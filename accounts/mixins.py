from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

class RoleRequiredMixin:
    allowed_roles = []

    def dispatch(self, request, *args, **kwargs):

        # not logged in
        if not request.user.is_authenticated:
            return redirect("login")

        user_role = getattr(request.user, "role", None)

      
        if user_role not in self.allowed_roles:
            return redirect("/")   

        return super().dispatch(request, *args, **kwargs)