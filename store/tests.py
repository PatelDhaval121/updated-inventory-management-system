from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Vendor
from store.models import Category, Delivery, Item


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="tester",
            password="secret123",
        )

    def test_dashboard_renders_for_local_host(self):
        self.client.force_login(self.user)
        response = self.client.get("/", HTTP_HOST="127.0.0.1")

        self.assertEqual(response.status_code, 200)


class DeletePermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="regular",
            password="secret123",
        )
        self.category = Category.objects.create(name="Test Category")

    def test_regular_user_cannot_access_delete_view(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("category-delete", kwargs={"pk": self.category.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))


class ProductManagementPermissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="regular",
            password="secret123",
        )
        self.category = Category.objects.create(name="Test Category")
        self.vendor = Vendor.objects.create(name="Test Vendor")
        self.item = Item.objects.create(
            name="Test Item",
            description="A test item",
            category=self.category,
            quantity=5,
            price=10.0,
            vendor=self.vendor,
        )

    def test_regular_user_cannot_access_product_create_view(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("product-create"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))

    def test_regular_user_cannot_access_product_update_view(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("product-update", kwargs={"slug": self.item.slug})
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))


class DeliveryPaginationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="delivery-user",
            password="secret123",
        )
        self.user.profile.role = "OP"
        self.user.profile.save(update_fields=["role"])
        category = Category.objects.create(name="Delivery Category")
        vendor = Vendor.objects.create(name="Delivery Vendor")
        item = Item.objects.create(
            name="Delivery Item",
            description="An item for delivery pagination",
            category=category,
            vendor=vendor,
        )
        for index in range(11):
            Delivery.objects.create(
                item=item,
                customer_name=f"Customer {index}",
                date=timezone.now(),
            )

    def test_deliveries_are_paginated_ten_per_page(self):
        self.client.force_login(self.user)

        first_page = self.client.get(reverse("deliveries"))
        second_page = self.client.get(reverse("deliveries"), {"page": 2})

        self.assertEqual(first_page.status_code, 200)
        self.assertTrue(first_page.context["is_paginated"])
        self.assertEqual(len(first_page.context["deliveries"]), 10)
        self.assertEqual(len(second_page.context["deliveries"]), 1)

    def test_search_filters_packages_by_customer(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("deliveries"),
            {"q": "Customer 4"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["deliveries"]), 1)
        self.assertEqual(
            response.context["deliveries"][0].customer_name,
            "Customer 4",
        )

    def test_operative_can_view_but_not_create_or_update_packages(self):
        self.client.force_login(self.user)
        delivery = Delivery.objects.first()

        response = self.client.get(reverse("deliveries"))
        create_response = self.client.get(reverse("delivery-create"))
        update_response = self.client.get(
            reverse("delivery-update", kwargs={"pk": delivery.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "View only")
        self.assertNotContains(response, reverse("delivery-create"))
        self.assertRedirects(create_response, reverse("dashboard"))
        self.assertRedirects(update_response, reverse("dashboard"))
