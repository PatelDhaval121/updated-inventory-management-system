# Django core imports
from datetime import datetime
from django.urls import reverse
from django.db.models import Q

# Class-based views
from django.views.generic import (
    CreateView,
    UpdateView,
    DeleteView
)

# Authentication and permissions
from django.contrib.auth.mixins import LoginRequiredMixin
from InventoryMS.permissions import (
    StaffDeletionPermissionMixin,
    StaffManagementPermissionMixin,
    StaffExportPermissionMixin,
)

# Third-party packages
from django_tables2 import SingleTableView
from django_tables2.export.views import ExportMixin

# Local app imports
from .models import Bill
from .tables import BillTable


class BillListView(
    LoginRequiredMixin,
    StaffExportPermissionMixin,
    ExportMixin,
    SingleTableView,
):
    """View for listing bills."""
    model = Bill
    table_class = BillTable
    template_name = 'bills/bill_list.html'
    context_object_name = 'bills'
    paginate_by = 10
    ordering = ['pk']
    SingleTableView.table_pagination = False

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get("q", "").strip()
        if query:
            filters = (
                Q(institution_name__icontains=query)
                | Q(description__icontains=query)
                | Q(email__icontains=query)
                | Q(address__icontains=query)
                | Q(payment_details__icontains=query)
            )
            if query.isdecimal():
                filters |= Q(pk=int(query)) | Q(phone_number=int(query))
            if query.casefold() == "paid":
                filters |= Q(status=True)
            elif query.casefold() == "pending":
                filters |= Q(status=False)
            queryset = queryset.filter(filters)
        return queryset

    def get_export_filename(self, export_format):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"Bills_{timestamp}.{export_format}"


class BillCreateView(
    LoginRequiredMixin, StaffManagementPermissionMixin, CreateView
):
    """View for creating a new bill."""
    model = Bill
    template_name = 'bills/billcreate.html'
    fields = [
        'institution_name',
        'phone_number',
        'email',
        'address',
        'description',
        'payment_details',
        'amount',
        'status'
    ]

    def get_success_url(self):
        """Redirect to the list of bills after a successful update."""
        return reverse('bill_list')


class BillUpdateView(
    LoginRequiredMixin, StaffManagementPermissionMixin, UpdateView
):
    """View for updating an existing bill."""
    model = Bill
    template_name = 'bills/billupdate.html'
    fields = [
        'institution_name',
        'phone_number',
        'email',
        'address',
        'description',
        'payment_details',
        'amount',
        'status'
    ]

    def get_success_url(self):
        """Redirect to the list of bills after a successful update."""
        return reverse('bill_list')


class BillDeleteView(LoginRequiredMixin, StaffDeletionPermissionMixin, DeleteView):
    """View for deleting a bill."""
    model = Bill
    template_name = 'bills/billdelete.html'

    def test_func(self):
        """Check if the user is a superuser."""
        return self.request.user.is_superuser

    def get_success_url(self):
        """Redirect to the list of bills after successful deletion."""
        return reverse('bill_list')
