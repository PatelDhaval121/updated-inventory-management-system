from django.test import TestCase

from accounts.models import Customer


class CustomerModelTests(TestCase):
    def test_customer_str_handles_missing_last_name(self):
        customer = Customer.objects.create(
            first_name="Asha",
            last_name="",
            email="asha@example.com",
        )

        self.assertEqual(str(customer), "Asha")
