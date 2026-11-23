from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Vendor
from invoice.models import Invoice
from store.models import Category, Item


class InvoicePaginationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="invoice-user",
            password="secret123",
        )
        self.user.profile.role = "OP"
        self.user.profile.save(update_fields=["role"])
        category = Category.objects.create(name="Invoice Category")
        vendor = Vendor.objects.create(name="Invoice Vendor")
        item = Item.objects.create(
            name="Invoice Item",
            description="An item for invoice pagination",
            category=category,
            vendor=vendor,
        )
        for index in range(11):
            Invoice.objects.create(
                customer_name=f"Customer {index}",
                contact_number="1234567890",
                item=item,
                price_per_item=10,
                quantity=1,
                shipping=0,
            )

    def test_invoices_are_paginated_ten_per_page(self):
        self.client.force_login(self.user)

        first_page = self.client.get(reverse("invoicelist"))
        second_page = self.client.get(reverse("invoicelist"), {"page": 2})

        self.assertEqual(first_page.status_code, 200)
        self.assertTrue(first_page.context["is_paginated"])
        self.assertEqual(len(first_page.context["invoices"]), 10)
        self.assertContains(first_page, "Showing 1")
        self.assertContains(first_page, "of 11 invoices")
        self.assertEqual(len(second_page.context["invoices"]), 1)
        self.assertContains(second_page, "Showing 11")

    def test_pagination_controls_remain_visible_on_a_single_page(self):
        Invoice.objects.order_by("-pk").first().delete()
        self.client.force_login(self.user)

        response = self.client.get(reverse("invoicelist"))

        self.assertEqual(len(response.context["invoices"]), 10)
        self.assertContains(response, "Showing 1")
        self.assertContains(response, "of 10 invoices")
        self.assertContains(response, 'aria-label="Page navigation"')

    def test_search_filters_invoices_by_customer(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("invoicelist"),
            {"q": "Customer 4"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["invoices"]), 1)
        self.assertEqual(
            response.context["invoices"][0].customer_name,
            "Customer 4",
        )

    def test_operative_can_view_but_not_create_or_export_invoices(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("invoicelist"))
        create_response = self.client.get(reverse("invoice-create"))
        export_response = self.client.get(
            reverse("invoicelist"),
            {"_export": "xlsx"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("invoice-create"))
        self.assertRedirects(create_response, reverse("dashboard"))
        self.assertRedirects(export_response, reverse("dashboard"))
