from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Vendor
from store.models import Category, Item


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
