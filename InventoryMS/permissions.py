from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.mixins import UserPassesTestMixin


class StaffManagementPermissionMixin(UserPassesTestMixin):
    """Allow only staff/superusers to access management actions."""

    permission_message = "You do not have permission to perform this action."

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True

        profile = getattr(user, "profile", None)
        return profile is not None and profile.role in {"AD", "EX"}

    def handle_no_permission(self):
        messages.error(self.request, self.permission_message)
        return redirect("dashboard")


class StaffDeletionPermissionMixin(StaffManagementPermissionMixin):
    """Allow only staff/superusers to access destructive actions."""

    permission_message = "You do not have permission to delete records."
