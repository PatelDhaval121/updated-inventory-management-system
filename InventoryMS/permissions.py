from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.mixins import UserPassesTestMixin


def has_management_permission(user):
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True

    profile = getattr(user, "profile", None)
    return profile is not None and profile.role in {"AD", "EX"}


def has_admin_permission(user):
    if not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True

    profile = getattr(user, "profile", None)
    return profile is not None and profile.role == "AD"


class StaffManagementPermissionMixin(UserPassesTestMixin):
    """Allow staff, superusers, executives, and admins to manage records."""

    permission_message = "You do not have permission to perform this action."

    def test_func(self):
        return has_management_permission(self.request.user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, self.permission_message)
        return redirect("dashboard")


class StaffDeletionPermissionMixin(StaffManagementPermissionMixin):
    """Allow management-authorized users to access destructive actions."""

    permission_message = "You do not have permission to delete records."


class StaffExportPermissionMixin:
    """Prevent operative users from exporting list data."""

    def dispatch(self, request, *args, **kwargs):
        if "_export" in request.GET and not has_management_permission(
            request.user
        ):
            messages.error(
                request,
                "You do not have permission to export records.",
            )
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)


class PurchaseOrderOwnerOrManagementPermissionMixin(
    StaffManagementPermissionMixin
):
    """Allow managers or a purchase-order owner to edit an order."""

    def test_func(self):
        order = self.get_object()
        if order.created_by_id is None:
            return has_admin_permission(self.request.user)
        return (
            has_management_permission(self.request.user)
            or order.created_by_id == self.request.user.pk
        )


class PurchaseOrderOwnerOrAdminPermissionMixin(
    StaffManagementPermissionMixin
):
    """Allow admins or a purchase-order owner to delete an order."""

    permission_message = "You can only delete your own purchase orders."

    def test_func(self):
        order = self.get_object()
        return (
            has_admin_permission(self.request.user)
            or (
                self.request.user.is_authenticated
                and order.created_by_id == self.request.user.pk
            )
        )
