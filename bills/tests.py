from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from bills.models import Bill


class BillSearchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="bills-user",
            password="secret123",
        )
        self.user.profile.role = "OP"
        self.user.profile.save(update_fields=["role"])
        Bill.objects.create(
            institution_name="Acme Workshop",
            payment_details="Bank transfer",
            amount=120,
        )

    def test_search_filters_bills_by_institution(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("bill_list"),
            {"q": "Acme"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["bills"]), 1)
        self.assertEqual(
            response.context["bills"][0].institution_name,
            "Acme Workshop",
        )

        no_match_response = self.client.get(
            reverse("bill_list"),
            {"q": "Missing Workshop"},
        )
        self.assertEqual(len(no_match_response.context["bills"]), 0)

    def test_operative_can_view_but_not_create_or_export_bills(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("bill_list"))
        create_response = self.client.get(reverse("bill_create"))
        export_response = self.client.get(
            reverse("bill_list"),
            {"_export": "xlsx"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("bill_create"))
        self.assertRedirects(create_response, reverse("dashboard"))
        self.assertRedirects(export_response, reverse("dashboard"))
