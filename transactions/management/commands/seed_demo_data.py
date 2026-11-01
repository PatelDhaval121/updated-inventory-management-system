from django.core.management.base import BaseCommand
from django.utils import timezone
import random

from store.models import Category, Item, Delivery
from accounts.models import Vendor, Customer
from transactions.models import Purchase, Sale, SaleDetail
from invoice.models import Invoice
from bills.models import Bill


class Command(BaseCommand):
    help = "Seed demo data: up to 5 items for products, sales, purchases, deliveries (package), invoices, bills"

    def handle(self, *args, **options):
        created = {'categories':0,'vendors':0,'customers':0,'items':0,'purchases':0,'sales':0,'deliveries':0,'invoices':0,'bills':0}

        # Categories
        cat_names = ["Electronics","Office","Kitchen","Garden","Toys"]
        for name in cat_names[:5]:
            obj, created_flag = Category.objects.get_or_create(name=name)
            if created_flag:
                created['categories'] += 1

        # Vendors
        for i in range(5):
            name = f"Vendor {i+1}"
            obj, flag = Vendor.objects.get_or_create(name=name, defaults={'phone_number': 1000000000 + i, 'address': f'Address {i+1}'})
            if flag:
                created['vendors'] += 1

        # Customers
        for i in range(5):
            first = f"Customer{i+1}"
            obj, flag = Customer.objects.get_or_create(first_name=first, defaults={'last_name':'Demo','email':f'cust{i+1}@example.com','phone':'0000000000'})
            if flag:
                created['customers'] += 1

        # Items (Products)
        categories = list(Category.objects.all())
        vendors = list(Vendor.objects.all())
        for i in range(5):
            name = f"Item {i+1}"
            defaults = {
                'description': f'Sample item {i+1}',
                'category': categories[i % len(categories)],
                'quantity': 10 + i,
                'price': round(random.uniform(5.0, 200.0),2),
                'vendor': vendors[i % len(vendors)]
            }
            item, flag = Item.objects.get_or_create(name=name, defaults=defaults)
            if flag:
                created['items'] += 1

        items = list(Item.objects.all())

        # Purchases
        for i in range(5):
            item = items[i % len(items)]
            vendor = item.vendor or (vendors[0] if vendors else None)
            if vendor is None:
                continue
            qty = 5 + i
            price = item.price
            purchase = Purchase(item=item, vendor=vendor, quantity=qty, price=price, total_value=price*qty)
            purchase.save()
            created['purchases'] += 1

        # Sales
        customers = list(Customer.objects.all())
        for i in range(5):
            customer = customers[i % len(customers)]
            sale = Sale.objects.create(customer=customer, sub_total=0, grand_total=0, tax_amount=0, tax_percentage=0, amount_paid=0, amount_change=0)
            item = items[i % len(items)]
            qty = 1 + (i % 3)
            total_detail = round(float(item.price) * qty, 2)
            sd = SaleDetail.objects.create(sale=sale, item=item, price=item.price, quantity=qty, total_detail=total_detail)
            sale.sub_total = total_detail
            sale.grand_total = total_detail
            sale.save()
            created['sales'] += 1

        # Deliveries (Package)
        for i in range(5):
            item = items[i % len(items)]
            d, flag = Delivery.objects.get_or_create(item=item, customer_name=f'Delivery {i+1}', defaults={'phone_number':'0000000000','location':'Warehouse','date':timezone.now()})
            if flag:
                created['deliveries'] += 1

        # Invoices
        for i in range(5):
            item = items[i % len(items)]
            invoice = Invoice.objects.create(customer_name=f'InvoiceCust{i+1}', contact_number='0000000000', item=item, price_per_item=item.price, quantity=1, shipping=0.0)
            created['invoices'] += 1

        # Bills
        for i in range(5):
            bill = Bill.objects.create(institution_name=f'Institution {i+1}', phone_number=1000000000 + i, email=f'inst{i+1}@example.com', address=f'Addr {i+1}', description='Demo bill', payment_details='Bank Transfer', amount=round(random.uniform(10,500),2), status=False)
            created['bills'] += 1

        # Summary
        self.stdout.write(self.style.SUCCESS('Seeding completed. Summary:'))
        for k,v in created.items():
            self.stdout.write(f"  {k}: {v}")
