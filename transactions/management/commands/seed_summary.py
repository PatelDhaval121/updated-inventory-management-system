from django.core.management.base import BaseCommand
from django.utils import timezone
import random
from decimal import Decimal

from store.models import Category, Item, Delivery
from accounts.models import Vendor, Customer, Profile
from django.contrib.auth import get_user_model
from transactions.models import Purchase, Sale, SaleDetail
from invoice.models import Invoice
from bills.models import Bill

User = get_user_model()

TARGETS = {
    'revenue': 1580000.0,
    'expenses': 1025000.0,
    'profit': 555000.0,
    'products': 494,
    'staff': 25,
    'customers': 185,
    'sales': 320,
    'pending_orders': 18,
}


def rand_price():
    return round(random.uniform(50.0, 2000.0), 2)


class Command(BaseCommand):
    help = 'Seed database to match provided summary targets.'

    def handle(self, *args, **options):
        created = {}

        # Ensure categories exist
        cat_names = ["Electronics", "Office", "Kitchen", "Garden", "Toys", "Clothing", "Sports"]
        for name in cat_names:
            Category.objects.get_or_create(name=name)

        # Products
        current_products = Item.objects.count()
        needed = TARGETS['products'] - current_products
        created['products'] = 0
        categories = list(Category.objects.all())
        vendors = list(Vendor.objects.all())
        if not vendors:
            # create a default vendor
            v, _ = Vendor.objects.get_or_create(name='Default Vendor', defaults={'phone_number': 9999999999, 'address': 'Default Address'})
            vendors = [v]

        for i in range(max(0, needed)):
            idx = current_products + i + 1
            cat = categories[(idx - 1) % len(categories)]
            vendor = vendors[(idx - 1) % len(vendors)]
            item, created_flag = Item.objects.get_or_create(
                name=f"AutoProduct {idx}",
                defaults={
                    'description': f'Auto generated product {idx}',
                    'category': cat,
                    'quantity': random.randint(5, 100),
                    'price': rand_price(),
                    'vendor': vendor,
                }
            )
            if created_flag:
                created['products'] += 1

        # Staff (Profiles)
        current_staff = Profile.objects.count()
        needed = TARGETS['staff'] - current_staff
        created['staff'] = 0
        for i in range(max(0, needed)):
            idx = current_staff + i + 1
            username = f'staff{idx}'
            email = f'staff{idx}@example.com'
            user, user_created = User.objects.get_or_create(username=username, defaults={'email': email})
            if user_created:
                user.set_password('Staff@123')
                user.save()
            profile, prof_created = Profile.objects.get_or_create(user=user, defaults={'first_name': f'Staff{idx}', 'last_name': 'Auto', 'role': 'OP'})
            if prof_created:
                created['staff'] += 1

        # Customers
        current_customers = Customer.objects.count()
        needed = TARGETS['customers'] - current_customers
        created['customers'] = 0
        for i in range(max(0, needed)):
            idx = current_customers + i + 1
            first = f'Cust{idx}'
            obj, flag = Customer.objects.get_or_create(first_name=first, defaults={'last_name': 'Auto', 'email': f'cust{idx}@example.com', 'phone': '0000000000'})
            if flag:
                created['customers'] += 1

        # Sales: create up to target number and adjust totals to reach revenue target
        current_sales = Sale.objects.count()
        needed_sales = TARGETS['sales'] - current_sales
        created['sales'] = 0

        # Compute current revenue
        from django.db.models import Sum
        current_revenue = float(Sale.objects.aggregate(total=Sum('grand_total'))['total'] or 0.0)
        remaining_revenue = TARGETS['revenue'] - current_revenue
        sales_to_create = max(0, needed_sales)

        items = list(Item.objects.all())
        customers = list(Customer.objects.all())
        if not items or not customers:
            self.stdout.write(self.style.ERROR('No items or customers available to create sales.'))
        else:
            # Distribute remaining revenue across new sales (if any) and, if still needed, update some existing sales by small amounts
            per_sale = remaining_revenue / max(1, sales_to_create)
            per_sale = max(per_sale, 10.0)
            for i in range(sales_to_create):
                cust = customers[i % len(customers)]
                sale = Sale.objects.create(customer=cust, sub_total=0, grand_total=0, tax_amount=0, tax_percentage=0, amount_paid=0, amount_change=0)
                # make a detail that sums to around per_sale
                item = items[i % len(items)]
                price = float(item.price) or rand_price()
                qty = max(1, int(round(per_sale / price)))
                total = round(price * qty, 2)
                if total == 0:
                    total = round(per_sale, 2)
                sd = SaleDetail.objects.create(sale=sale, item=item, price=price, quantity=qty, total_detail=total)
                sale.sub_total = total
                sale.grand_total = total
                sale.save()
                created['sales'] += 1

        # Purchases (Expenses): ensure total purchases >= expenses target
        current_expenses = float(Purchase.objects.aggregate(total=Sum('total_value'))['total'] or 0.0)
        remaining_expenses = TARGETS['expenses'] - current_expenses
        created['purchases'] = 0
        if remaining_expenses > 0 and items:
            # create several purchases distributing remaining_expenses
            # make up to 50 purchase records to reach target
            count = min(50, int(remaining_expenses // 100 + 1))
            for i in range(count):
                item = items[i % len(items)]
                vendor = item.vendor or vendors[0]
                # allocate portion
                portion = remaining_expenses / count
                price = float(item.price) or rand_price()
                qty = max(1, int(round(portion / price)))
                total_value = round(price * qty, 2)
                p = Purchase(item=item, vendor=vendor, quantity=qty, price=price, total_value=total_value)
                p.save()
                created['purchases'] += 1

        # Pending orders: ensure at least TARGETS['pending_orders'] purchases with delivery_status 'P'
        pending_count = Purchase.objects.filter(delivery_status='P').count()
        need_pending = TARGETS['pending_orders'] - pending_count
        created['pending_orders'] = 0
        if need_pending > 0 and items:
            for i in range(need_pending):
                item = items[i % len(items)]
                vendor = item.vendor or vendors[0]
                p = Purchase(item=item, vendor=vendor, quantity=1, price=float(item.price) or rand_price(), total_value=float(item.price) or rand_price())
                p.delivery_status = 'P'
                p.save()
                created['pending_orders'] += 1

        # Invoices: create a few invoices to reflect sales (not strictly necessary)
        created['invoices'] = 0
        for i in range(5):
            item = items[i % len(items)]
            Invoice.objects.create(customer_name=f'InvCust{i+1}', contact_number='0000000000', item=item, price_per_item=item.price, quantity=1, shipping=0.0)
            created['invoices'] += 1

        # Bills: create a few bills to reflect expenses
        created['bills'] = 0
        for i in range(5):
            Bill.objects.create(institution_name=f'Inst{i+1}', phone_number=1000000000+i, email=f'inst{i+1}@example.com', address='Addr', description='Auto bill', payment_details='Bank', amount=round(random.uniform(1000,50000),2), status=False)
            created['bills'] += 1

        # Deliveries (packages) create if needed
        created['deliveries'] = 0
        current_deliveries = Delivery.objects.count()
        if current_deliveries < TARGETS['pending_orders']:
            for i in range(TARGETS['pending_orders'] - current_deliveries):
                Delivery.objects.create(item=items[i % len(items)], customer_name=f'Del{ i+1 }', phone_number='0000000000', location='Warehouse', date=timezone.now(), is_delivered=False)
                created['deliveries'] += 1

        # Summary output
        self.stdout.write(self.style.SUCCESS('Seeding to summary completed. Created:'))
        for k, v in created.items():
            self.stdout.write(f'  {k}: {v}')

        # Final counts
        from django.db.models import Sum
        final_products = Item.objects.count()
        final_staff = Profile.objects.count()
        final_customers = Customer.objects.count()
        final_sales = Sale.objects.count()
        final_revenue = float(Sale.objects.aggregate(total=Sum('grand_total'))['total'] or 0.0)
        final_expenses = float(Purchase.objects.aggregate(total=Sum('total_value'))['total'] or 0.0)
        self.stdout.write(self.style.SUCCESS('Final counts:'))
        self.stdout.write(f'  Products: {final_products}')
        self.stdout.write(f'  Staff: {final_staff}')
        self.stdout.write(f'  Customers: {final_customers}')
        self.stdout.write(f'  Sales: {final_sales}')
        self.stdout.write(f'  Revenue (approx): ₹{final_revenue:,.2f}')
        self.stdout.write(f'  Expenses (approx): ₹{final_expenses:,.2f}')
