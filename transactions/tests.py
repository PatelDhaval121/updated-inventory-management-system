from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Customer, Vendor
from store.models import Category, Item
from transactions.models import Purchase, Sale


class SaleDetailViewTests(TestCase):
    def test_sale_detail_links_back_to_sales_orders(self):
        user = get_user_model().objects.create_user(
            username="sales-user",
            password="secret123",
        )
        customer = Customer.objects.create(first_name="Test Customer")
        sale = Sale.objects.create(customer=customer)
        self.client.force_login(user)

        response = self.client.get(
            reverse("sale-detail", kwargs={"pk": sale.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("saleslist"))
        self.assertContains(response, "Back to Sales Orders")


class SalesAndPurchasesSearchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="orders-user",
            password="secret123",
        )
        self.user.profile.role = "OP"
        self.user.profile.save(update_fields=["role"])
        self.client.force_login(self.user)
        self.category = Category.objects.create(name="Orders Category")
        self.vendor = Vendor.objects.create(name="Northwind Supplies")
        self.item = Item.objects.create(
            name="Copper Cable",
            description="Electrical cable",
            category=self.category,
            vendor=self.vendor,
        )

    def test_sales_search_matches_customer_name(self):
        matching_customer = Customer.objects.create(first_name="Avery")
        other_customer = Customer.objects.create(first_name="Jordan")
        matching_sale = Sale.objects.create(customer=matching_customer)
        Sale.objects.create(customer=other_customer)

        response = self.client.get(reverse("saleslist"), {"q": "Avery"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["sales"]),
            [matching_sale],
        )

    def test_purchases_search_matches_item_and_vendor(self):
        matching_purchase = Purchase.objects.create(
            item=self.item,
            vendor=self.vendor,
            quantity=1,
            price=5,
            total_value=5,
        )
        other_vendor = Vendor.objects.create(name="Other Supplies")
        other_purchase = Purchase.objects.create(
            item=self.item,
            vendor=other_vendor,
            quantity=1,
            price=5,
            total_value=5,
        )

        response = self.client.get(
            reverse("purchaseslist"),
            {"q": "Northwind"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["purchases"]),
            [matching_purchase],
        )
        self.assertNotIn(other_purchase, response.context["purchases"])

    def test_purchase_view_action_opens_order_details(self):
        purchase = Purchase.objects.create(
            item=self.item,
            vendor=self.vendor,
            description="Urgent stock order",
            quantity=2,
            price=5,
            total_value=10,
        )

        list_response = self.client.get(reverse("purchaseslist"))
        detail_url = reverse(
            "purchase-detail",
            kwargs={"slug": purchase.slug},
        )
        detail_response = self.client.get(detail_url)

        self.assertContains(list_response, f'href="{detail_url}"')
        self.assertContains(list_response, "View")
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, f"Purchase Order #{purchase.id}")
        self.assertContains(detail_response, "Urgent stock order")
        self.assertContains(detail_response, self.vendor.name)
        self.assertContains(detail_response, self.item.name)

    def test_operative_can_add_purchase_but_not_edit_or_export(self):
        purchase = Purchase.objects.create(
            item=self.item,
            vendor=self.vendor,
            quantity=1,
            price=5,
            total_value=5,
        )

        purchase_form = self.client.get(reverse("purchase-create"))
        update_response = self.client.get(
            reverse("purchase-update", kwargs={"pk": purchase.pk})
        )
        delete_response = self.client.get(
            reverse("purchase-delete", kwargs={"pk": purchase.pk})
        )
        export_response = self.client.get(reverse("purchases-export"))

        self.assertEqual(purchase_form.status_code, 200)
        self.assertRedirects(update_response, reverse("dashboard"))
        self.assertRedirects(delete_response, reverse("dashboard"))
        self.assertRedirects(export_response, reverse("dashboard"))

    def test_purchase_creator_can_edit_and_delete_their_order(self):
        response = self.client.post(
            reverse("purchase-create"),
            {
                "item": self.item.pk,
                "price": "5.00",
                "description": "Created by operative",
                "vendor": self.vendor.pk,
                "quantity": "2",
                "delivery_date": "",
                "delivery_status": "P",
            },
        )

        self.assertRedirects(response, reverse("purchaseslist"))
        purchase = Purchase.objects.get(description="Created by operative")
        self.assertEqual(purchase.created_by, self.user)
        self.assertEqual(
            self.client.get(
                reverse("purchase-update", kwargs={"pk": purchase.pk})
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(
                reverse("purchase-delete", kwargs={"pk": purchase.pk})
            ).status_code,
            200,
        )

    def test_operative_cannot_edit_or_delete_another_users_order(self):
        other_user = get_user_model().objects.create_user(
            username="other-operative",
            password="secret123",
        )
        other_user.profile.role = "OP"
        other_user.profile.save(update_fields=["role"])
        purchase = Purchase.objects.create(
            item=self.item,
            vendor=self.vendor,
            quantity=1,
            price=5,
            total_value=5,
            created_by=other_user,
        )

        update_response = self.client.get(
            reverse("purchase-update", kwargs={"pk": purchase.pk})
        )
        delete_response = self.client.get(
            reverse("purchase-delete", kwargs={"pk": purchase.pk})
        )

        self.assertRedirects(update_response, reverse("dashboard"))
        self.assertRedirects(delete_response, reverse("dashboard"))

    def test_operative_cannot_create_sales_orders(self):
        response = self.client.get(reverse("sale-create"))

        self.assertRedirects(response, reverse("dashboard"))
