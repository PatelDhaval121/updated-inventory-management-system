from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from accounts.models import Customer, Profile, Vendor
from transactions.models import Sale


class CustomerModelTests(TestCase):
    def test_customer_str_handles_missing_last_name(self):
        customer = Customer.objects.create(
            first_name="Asha",
            last_name="",
            email="asha@example.com",
        )

        self.assertEqual(str(customer), "Asha")


class CustomerListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="customer-list-user",
            password="test-password",
        )
        self.user.profile.role = "EX"
        self.user.profile.save(update_fields=["role"])
        self.client.force_login(self.user)
        for index in range(1, 11):
            Customer.objects.create(
                first_name=f"Customer {index}",
                last_name="Test",
            )

    def test_customer_list_has_eight_customers_per_page_in_id_order(self):
        response = self.client.get(reverse("customer_list"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(response.context["paginator"].per_page, 8)
        self.assertEqual(
            list(response.context["page_obj"].object_list.values_list("id", flat=True)),
            list(range(1, 9)),
        )

    def test_customer_list_second_page_contains_remaining_customers(self):
        response = self.client.get(reverse("customer_list") + "?page=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["page_obj"].object_list.values_list("id", flat=True)),
            [9, 10],
        )


class ProfileListViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            password="password",
        )
        self.admin.profile.slug = "admin"
        self.admin.profile.role = "AD"
        self.admin.profile.status = "A"
        self.admin.profile.save()

        for index in range(1, 10):
            user = User.objects.create_user(username=f"staff-{index}")
            user.profile.slug = f"staff-{index}"
            user.profile.role = "OP"
            user.profile.status = "A"
            user.profile.save()

        self.client.login(username="admin", password="password")

    def test_staff_list_has_eight_profiles_per_page_in_id_order(self):
        response = self.client.get("/accounts/profiles/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(response.context["paginator"].per_page, 8)
        self.assertEqual(
            list(response.context["page_obj"].object_list.values_list("id", flat=True)),
            list(range(1, 9)),
        )

    def test_staff_list_second_page_continues_id_order(self):
        response = self.client.get("/accounts/profiles/?page=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["page_obj"].object_list.values_list("id", flat=True)),
            [9, 10],
        )

    def test_staff_delete_confirmation_and_deletion(self):
        staff_profile = Profile.objects.get(slug="staff-1")

        confirmation = self.client.get(
            reverse("profile-delete", kwargs={"pk": staff_profile.pk})
        )

        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, "staff-1")
        self.assertContains(confirmation, reverse("profile_list"))

        response = self.client.post(
            reverse("profile-delete", kwargs={"pk": staff_profile.pk})
        )

        self.assertRedirects(response, reverse("profile_list"))
        self.assertFalse(Profile.objects.filter(pk=staff_profile.pk).exists())


class CustomerDeleteViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="customer-admin",
            password="password",
        )
        self.client.force_login(self.admin)
        self.customer = Customer.objects.create(
            first_name="Asha",
            last_name="Patel",
        )

    def test_customer_delete_preserves_sale_and_clears_customer(self):
        sale = Sale.objects.create(customer=self.customer)

        response = self.client.post(
            reverse("customer_delete", kwargs={"pk": self.customer.pk})
        )

        self.assertRedirects(response, reverse("customer_list"))
        self.assertFalse(Customer.objects.filter(pk=self.customer.pk).exists())
        sale.refresh_from_db()
        self.assertIsNone(sale.customer_id)

    def test_executive_can_delete_customer(self):
        self.admin.is_superuser = False
        self.admin.is_staff = False
        self.admin.save(update_fields=["is_superuser", "is_staff"])
        self.admin.profile.role = "EX"
        self.admin.profile.save(update_fields=["role"])

        response = self.client.post(
            reverse("customer_delete", kwargs={"pk": self.customer.pk})
        )

        self.assertRedirects(response, reverse("customer_list"))
        self.assertFalse(Customer.objects.filter(pk=self.customer.pk).exists())

    def test_operative_cannot_delete_customer(self):
        self.admin.is_superuser = False
        self.admin.is_staff = False
        self.admin.save(update_fields=["is_superuser", "is_staff"])
        self.admin.profile.role = "OP"
        self.admin.profile.save(update_fields=["role"])

        response = self.client.post(
            reverse("customer_delete", kwargs={"pk": self.customer.pk})
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(Customer.objects.filter(pk=self.customer.pk).exists())


class VendorListViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="vendor-list-user",
            password="test-password",
        )
        self.user.profile.role = "EX"
        self.user.profile.save(update_fields=["role"])
        self.client.force_login(self.user)
        for name in ("Zulu Supplies", "Alpha Supplies", "Beta Supplies"):
            Vendor.objects.create(name=name)

    def test_vendor_list_orders_vendors_and_paginates(self):
        response = self.client.get(reverse("vendor-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["page_obj"].object_list.values_list("name", flat=True)),
            ["Alpha Supplies", "Beta Supplies", "Zulu Supplies"],
        )
        self.assertEqual(response.context["paginator"].per_page, 10)

    def test_vendor_list_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse("vendor-list"))

        self.assertRedirects(
            response,
            f"{reverse('user-login')}?next={reverse('vendor-list')}",
        )
