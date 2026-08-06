from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Vendor
from store.models import Item
from transactions.models import Purchase


class Command(BaseCommand):
    help = "Seed sample purchase records for development and testing"

    def handle(self, *args, **options):
        sample_purchases = [
            {
                "item_name": "Laptop",
                "vendor_name": "Tech Supply Co",
                "description": "Quarterly bulk laptop order",
                "quantity": 3,
                "price": Decimal("85000.00"),
                "delivery_status": "S",
                "delivery_date": timezone.now() - timedelta(days=2),
            },
            {
                "item_name": "USB-C Adapter",
                "vendor_name": "Digital Parts Ltd",
                "description": "Accessory replenishment for the office",
                "quantity": 25,
                "price": Decimal("450.00"),
                "delivery_status": "S",
                "delivery_date": timezone.now() - timedelta(days=5),
            },
            {
                "item_name": "Wireless Mouse",
                "vendor_name": "Office Hub",
                "description": "Peripheral stock for new workstations",
                "quantity": 12,
                "price": Decimal("700.00"),
                "delivery_status": "P",
                "delivery_date": None,
            },
            {
                "item_name": "IPHONE 16",
                "vendor_name": "Tech Supply Co",
                "description": "Premium phone inventory top-up",
                "quantity": 2,
                "price": Decimal("125000.00"),
                "delivery_status": "S",
                "delivery_date": timezone.now() - timedelta(days=1),
            },
            {
                "item_name": "Water bottles",
                "vendor_name": "Priyansh tandel",
                "description": "Promotional bottle order for an event",
                "quantity": 50,
                "price": Decimal("25.00"),
                "delivery_status": "P",
                "delivery_date": None,
            },
        ]

        created = 0
        for entry in sample_purchases:
            if Purchase.objects.filter(description=entry["description"]).exists():
                continue

            item = Item.objects.filter(name=entry["item_name"]).first()
            vendor = Vendor.objects.filter(name=entry["vendor_name"]).first()
            if not item or not vendor:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping purchase for {entry['item_name']} because the item or vendor was not found."
                    )
                )
                continue

            purchase = Purchase.objects.create(
                item=item,
                description=entry["description"],
                vendor=vendor,
                quantity=entry["quantity"],
                price=entry["price"],
                delivery_status=entry["delivery_status"],
                delivery_date=entry["delivery_date"],
            )
            created += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created purchase for {purchase.item.name} from {purchase.vendor.name}"
                )
            )

        self.stdout.write(self.style.SUCCESS(f"Finished seeding purchases. Created {created} new records."))
