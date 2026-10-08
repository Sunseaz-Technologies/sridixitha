from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from core.models import Category, CategoryService
from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse, HttpResponse
from .models import User,Booking, BookingHistory, Payment, VendorProfile, CustomerRemark,TermsAcceptance
import random
from django.db.models import Count, Q
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import get_user_model
from accounts.mixins import RoleRequiredMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.hashers import make_password
from django.core.paginator import Paginator
from accounts.utils import verify_otp
from accounts.utils import send_otp, can_resend
from core.models import CategoryService,ServicesCards
from .utils import create_notification
from django.urls import reverse
from django.utils import timezone
from datetime import datetime
import json
from .utils import paginate_queryset
from decimal import Decimal
from django.views.generic import ListView
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from collections import OrderedDict
from django.utils.timezone import now
from datetime import timedelta
from .utils import (send_otp,verify_otp)
from django.contrib.auth.models import Permission
from accounts.utils import permission_required
from collections import defaultdict
from django.db.models.functions import TruncMonth




User = get_user_model()
mainly_allowed_roles=["admin","superadmin"]

# login classes
def normalize_phone(phone):
    return phone.replace(" ", "").replace("+91", "").strip()


    

class LoginView(View):
    """View for OTP based user login and role based dashboard redirection with vendor approval validation."""

    def get(self, request):
        next_url = request.GET.get("next", "")
        return render(request,"customer/customer_login.html",
            {
                "next": next_url
            }
        )

    def post(self, request):

        data = json.loads(request.body)
        phone = data.get("phone","").replace("+91", "").strip()
        otp = data.get("otp")
        next_url = data.get("next")

        if not phone.isdigit() or len(phone) != 10:
            return JsonResponse({"error": "Enter valid 10 digit phone number"})

        if otp:

            if not verify_otp(phone, otp):
                return JsonResponse({

                    "error": "Invalid OTP"

                })

            user = User.objects.filter(phone__endswith=phone).first()

            if not user:

                return JsonResponse({

                    "error": "User not found Please Register",

                    "redirect": f"/register/?phone={phone}"

                })

            if user.role == "vendor" and not user.is_active:

                return JsonResponse({
                    "error": "Your account is not approved yet. Please wait for admin approval."

                })

            login(request, user)

            # --- MERGE SESSION CART WITH USER CART ---
            from .models import Cart, CartItem
            session_key = request.session.session_key
            if session_key:
                try:
                    session_cart = Cart.objects.get(session_key=session_key)
                    user_cart, created = Cart.objects.get_or_create(user=user)
                    for item in session_cart.items.all():
                        if not CartItem.objects.filter(cart=user_cart, service=item.service).exists():
                            item.cart = user_cart
                            item.save()
                        else:
                            item.delete()
                    session_cart.delete()
                except Cart.DoesNotExist:
                    pass
            # -----------------------------------------

            # print(
            #     "LOGGED IN USER ROLE:",
            #     user.role
            # )

            if user.role == "superadmin":
                redirect_url = reverse("superadmin_dashboard")
            elif user.role == "admin":
                redirect_url = reverse("admin_dashboard")
            elif user.role == "vendor":
                redirect_url = reverse("vendor_dashboard")
            else:
                # Customer or unknown role
                if next_url:
                    redirect_url = next_url
                else:
                    redirect_url = reverse("indexpage")
            
            return JsonResponse({
                "success": True,
                "redirect": redirect_url

            })


        user = User.objects.filter(
            phone=phone
        ).first()

        if not user:

            return JsonResponse({

                "error": "User not found Please Register",

                "redirect": f"/register/?phone={phone}"

            })

        if user.role == "vendor" and not user.is_active:

            return JsonResponse({

                "error": "Your account is not approved yet. Please wait for admin approval."

            })

        send_otp(phone,"login")

        return JsonResponse({

            "success": True,
            "message": "OTP sent"

        })

# register classes

class RegisterView(View):
    """ registration for customer and vendor users with role based account creation """

    def get(self, request):

        category_id = request.GET.get("category")
        categories = Category.objects.all()
        services = CategoryService.objects.all()

        if category_id:

            services = services.filter(
                category_id=category_id
            )

        return render(
            request,
            "customer/register.html",
            {
                "categories": categories,
                "services": services,
                "selected_category": category_id
            }
        )

    def post(self, request):

        try:

            data = json.loads(request.body)

        except:

            return JsonResponse({
                "error": "Invalid data"
            }, status=400)

        action = data.get("action")

        phone = data.get("phone")
        otp = data.get("otp")
        name = data.get("name")
        email = data.get("email")
        role = data.get("role", "customer")
        category_id = data.get("category")
        service_id = data.get("service")

        # NEW

        city = data.get("city")
        postal_code = data.get("postal_code")

        # SEND OTP

        if action == "send_otp":

            if not phone or len(phone) != 10:

                return JsonResponse({

                    "error": "Enter valid phone number"

                })

            if User.objects.filter(
                phone=phone
            ).exists():

                return JsonResponse({

                    "error": "User already exists. Please login.",

                    "redirect": "/login/"

                })

            send_otp(phone,"register")

            return JsonResponse({

                "success": True

            })
        # RESEND OTP

        if action == "resend_otp":

            if not phone or len(phone) != 10:

                return JsonResponse({
                    "error": "Enter valid phone number"
                })

            send_otp(phone,"register")

            return JsonResponse({
                "success": True
            })
        # VERIFY OTP

        if action == "verify_otp":

            if not verify_otp(phone, otp):

                return JsonResponse({

                    "error": "Invalid or expired OTP"

                })

            # EMAIL CHECK

            if User.objects.filter(
                email=email
            ).exists():

                return JsonResponse({

                    "error": "Email already registered. Please login.",

                    "redirect": "/login/"

                })

            try:

                user = User.objects.create_user(

                    email=email,

                    password=None

                )

                user.phone = phone

                user.first_name = name

                user.role = role

                # NEW

                user.city = city
                user.postal_code = postal_code

                user.is_active = False if role == "vendor" else True

                user.save()

                # VENDOR

                if role == "vendor":

                    if not category_id:

                        user.delete()

                        return JsonResponse({

                            "error": "Please select category"

                        })

                    services_qs = CategoryService.objects.filter(
                        category_id=category_id
                    )

                    if not services_qs.exists():

                        user.delete()

                        return JsonResponse({

                            "error": "No services available for selected category"

                        })

                    if not service_id:

                        user.delete()

                        return JsonResponse({

                            "error": "Please select a service"

                        })

                    ser_obj = CategoryService.objects.filter(

                        id=service_id,

                        category_id=category_id

                    ).first()

                    if not ser_obj:

                        user.delete()

                        return JsonResponse({

                            "error": "Invalid service selected"

                        })

                    cat_obj = get_object_or_404(
                        Category,
                        id=category_id
                    )

                    profile = VendorProfile.objects.create(

                        user=user,

                        category=cat_obj,

                        experience=0,

                        locality="Default",

                        street="Default",

                        # NEW

                        city=city,

                        postal_code=postal_code

                    )

                    profile.services.add(
                        ser_obj
                    )

                if role == "customer":
                    login(request, user)
                    return JsonResponse({
                        "success": True,
                        "redirect": "/"
                    })
                else:
                    return JsonResponse({
                        "success": True,
                        "redirect": "/login/"
                    })

            except Exception as e:

                print("REGISTER ERROR:", e)

                try:

                    user.delete()

                except:

                    pass

                return JsonResponse({

                    "error": "Something went wrong. Please try again."

                }, status=500)

        return JsonResponse({

            "error": "Invalid request"

        }, status=400)

# get the category and services in regigter page 




# logout classes
@method_decorator(never_cache, name='dispatch')
class LogoutView(LoginRequiredMixin, View):
    """  logout user and clear session data  """
    def get(self, request):
        auth_logout(request)
        request.session.flush()
        return redirect("indexpage")
        
    def post(self, request):
        auth_logout(request) 
        request.session.flush()
        return redirect("indexpage")







# =========================================
# superadmin
# ======================================


# 1.super admin -- dashboard page
@method_decorator(never_cache, name='dispatch')
class SuperDashboardView(LoginRequiredMixin, RoleRequiredMixin, View):

    ''' superadmin dashboard view for managing users, bookings, service analytics, and monthly booking statistics '''

    allowed_roles = ['superadmin']
    def get(self, request):

        # count the users
        user_counts = User.objects.aggregate(

            total_customers=Count("id",filter=Q(role="customer")),
            total_vendors=Count("id",filter=Q(role="vendor")),
            total_admins=Count("id",filter=Q(role="admin"))
        )
        # bookings status wise filter
        bookings = Booking.objects.all()
        booking_counts = bookings.aggregate(
                total_bookings=Count("id"),
                total_pending=Count("id",filter=Q(status="pending")),
                total_assigned=Count("id",filter=Q(status="assigned")),
                total_accepted=Count("id",filter=Q(status="accepted")),
                total_in_progress=Count("id",filter=Q(status="in_progress")),
                total_completed=Count("id",filter=Q(status="completed")),
                total_cancelled=Count("id",filter=Q(status="cancelled")),
                )

        # monthly bookings count

        current_year = timezone.now().year

        monthly_counts = bookings.filter(

            booking_created_at__year=current_year

        ).annotate(
            month=TruncMonth(
                "booking_created_at")).values("month").annotate(
            total=Count("id")).order_by("month")

        month_map = {
            item["month"].month: item["total"]
            for item in monthly_counts
        }

        month_labels = [

            datetime(
                current_year,
                month,
                1
            ).strftime("%b")

            for month in range(1, 13)

        ]

        monthly_data = [

            month_map.get(
                month,
                0
            )

            for month in range(1, 13)

        ]
        # category filter

        categories = Category.objects.all()
        selected_category = request.GET.get("category")
        services = CategoryService.objects.all()
        if selected_category:
            services = services.filter(category_id=selected_category)

        # service analytics
        service_labels = []
        service_data = []
        for service in services:
            service_labels.append(service.s_title)
            service_data.append(bookings.filter(service=service).count())

        context = {
            'page_title': 'Dashboard',
            'total_customers': user_counts["total_customers"],
            'total_vendors': user_counts["total_vendors"],
            'total_admins': user_counts["total_admins"],
            'total_bookings': booking_counts["total_bookings"],
            'total_pending': booking_counts["total_pending"],
            'total_assigned': booking_counts["total_assigned"],
            'total_accepted': booking_counts["total_accepted"],
            'total_in_progress': booking_counts["total_in_progress"],
            'total_completed': booking_counts["total_completed"],
            'total_cancelled': booking_counts["total_cancelled"],
            'month_labels': month_labels,
            'monthly_data': monthly_data,
            'categories': categories,
            'selected_category': selected_category,
            'service_labels': json.dumps(service_labels),
            'service_data': json.dumps(service_data),
        }

        return render(request,"superadmin/dashboard.html",context)




# 2.superadmin can create the admins
@method_decorator(never_cache, name='dispatch')
class CreateAdminView(LoginRequiredMixin, View):

    def get(self, request):
        admins = User.objects.filter(role="admin").order_by("-id")
        page_obj = paginate_queryset(request, admins, 5)
        context = {
            "admins": page_obj,
            "page_obj": page_obj,
            "page_title": "Create_Admins"
        }
        return render(request, "superadmin/create_admin.html", context)

    def post(self, request):
        try:
            if request.user.role != "superadmin":
                return JsonResponse({"error": "Unauthorized"}, status=403)

            first_name = request.POST.get("first_name", "").strip()
            last_name  = request.POST.get("last_name", "").strip()
            email      = request.POST.get("email", "").strip()
            city       = request.POST.get("city", "").strip()
            pincode    = request.POST.get("pincode", "").strip()
            phone      = request.POST.get("phone", "").strip()
            phone      = normalize_phone(phone)

            if not all([first_name, last_name, email, city, pincode, phone]):
                return JsonResponse({"error": "All fields are required"}, status=400)

            import re
            if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
                return JsonResponse({"error": "Invalid email address"}, status=400)

            if not re.match(r'^[1-9][0-9]{5}$', pincode):
                return JsonResponse({"error": "Invalid 6-digit pincode"}, status=400)

            if User.objects.filter(email=email).exists():
                return JsonResponse({"error": "Email already exists"}, status=400)

            if User.objects.filter(phone=phone).exists():
                return JsonResponse({"error": "Phone number already exists"}, status=400)

            user = User.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                city=city,
                pincode=pincode,
                phone=phone,
                role="admin"
            )
            user.set_unusable_password()
            user.save()

            return JsonResponse({"status": "success"})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)



# update/edit the admin profile
@method_decorator(never_cache, name='dispatch')
class EditAdminView(LoginRequiredMixin, View):

    """ edit admin """

    def get(self, request, id):

        admin = User.objects.get(

            id=id,
            role="admin"
        )

        context = {

            "admin": admin,
            "page_title": "Edit_Admin"

        }

        return render( request,"superadmin/edit_admin.html",context)

    def post(self, request, id):

        try:

            admin = User.objects.get(

                id=id,
                role="admin"
            )

            admin.city = request.POST.get(
                "city"
            )

            admin.pincode = request.POST.get(
                "pincode"
            )

            admin.save()

            messages.success(

                request,
                "Admin updated successfully"
            )

            return redirect(
                "create_admin"
            )

        except Exception as e:

            messages.error(

                request,
                str(e)
            )

            return redirect(
                "edit_admin",
                id=id
            )
# 3.superadmin can see the user profile views code
@method_decorator(never_cache, name='dispatch')
class UserProfileView(LoginRequiredMixin,View):
    """ view and manage complete user details, profile information, and account activity """

    def get(self, request, id):

        if request.user.role not in mainly_allowed_roles:
            return redirect("login")

        user_obj = get_object_or_404(User,id=id)

        if (
            request.user.role == "admin"
            and
            user_obj.role == "superadmin"
        ):
            return redirect("login")

        if request.user.role == "superadmin":
            back_url = "superadmin_dashboard"

        else:
            back_url = "admin_dashboard"

        context = {
            "user_obj": user_obj,
            "back_url": back_url,
        }

        return render(request,"admin/user_profile.html",context)


# superadmin can see the all users and update the behaviour
@method_decorator(never_cache, name='dispatch')
class AllUsersView(LoginRequiredMixin,View):
    """ View All Users """

    def get(self, request):
        current_user = request.user

        if current_user.role not in mainly_allowed_roles:
            return redirect("login")
        if current_user.role == "superadmin":

            users = User.objects.filter(

                role__in=[
                    "customer",
                    "vendor",
                    "admin"
                ]

            )

        else:

            users = User.objects.filter(

                role__in=[
                    "customer",
                    "vendor"
                ]

            )

            if current_user.city:

                users = users.filter(

                    city__iexact=
                    current_user.city.strip()

                )

        users = users.distinct()
        role = request.GET.get("role")

        city = request.GET.get("city")

        if role:

            users = users.filter(
                role=role
            )

        if city:

            users = users.filter(
                city__iexact=city
            )

        users = users.order_by("-id")
        raw_locations = (

            users

            .exclude(city__isnull=True)

            .exclude(city="")

            .values_list(
                "city",
                flat=True
            )
            .distinct()

        )
        seen_cities = set()
        locations = []
        for loc in raw_locations:
            cleaned_loc = loc.strip().title()
            if cleaned_loc and cleaned_loc not in seen_cities:
                seen_cities.add(cleaned_loc)
                locations.append(cleaned_loc)
        locations.sort()
        page_obj = paginate_queryset(request,users,10)

        if current_user.role == "superadmin":

            customer_count = User.objects.filter(
                role="customer"
            ).count()

            vendor_count = User.objects.filter(
                role="vendor"
            ).count()

            admin_count = User.objects.filter(
                role="admin"
            ).count()

        else:

            customer_count = User.objects.filter(

                role="customer",

                city__iexact=
                current_user.city.strip()

            ).count()

            vendor_count = User.objects.filter(

                role="vendor",

                city__iexact=
                current_user.city.strip()

            ).count()

            admin_count = 0


        total_users = (customer_count+ vendor_count + admin_count)
        context = {

            "page_obj": page_obj,
            "users": page_obj,
            "locations": locations,
            "selected_role": role,
            "selected_city": city,
            "customer_count": customer_count,
            "vendor_count": vendor_count,
            "admin_count": admin_count,
            "total_users":total_users,

        }

        return render(request,"superadmin/all_users.html",context)

    def post(self, request):

        if request.user.role not in [
            "superadmin",
            "admin"
        ]:

            return JsonResponse({

                "success": False,

                "error": "Access Denied"

            })

        try:

            data = json.loads(
                request.body
            )

            user_id = data.get(
                "user_id"
            )

            behaviour = data.get(
                "behaviour"
            )

            user = User.objects.filter(

                id=user_id,

                role__in=[
                    "customer",
                    "vendor",
                    "admin"
                ]

            ).first()

            if not user:

                return JsonResponse({

                    "success": False,

                    "error": "User not found"

                })



            user.behaviour = behaviour

            user.save()

            return JsonResponse({

                "success": True

            })

        except Exception as e:

            return JsonResponse({

                "success": False,

                "error": str(e)

            })

# superadmin all leads tracking
@method_decorator(never_cache, name='dispatch')
@method_decorator(never_cache,name='dispatch')
class SuperAdminOrdersView(LoginRequiredMixin,View):
    """ View all bookings and vendor assignment timings """

    def get(self, request):

        bookings = Booking.objects.select_related("user","service","vendor"
        ).prefetch_related(
            "history"
        ).order_by(
            "-booking_created_at"
        )

        services = CategoryService.objects.all()
        vendors = User.objects.filter(role="vendor")
        q = request.GET.get("q")

        if q:

            bookings = bookings.filter(

                Q(order_id__icontains=q) |
                Q(user__first_name__icontains=q) |
                Q(user__phone__icontains=q)

            )

        service_id = request.GET.get(
            "service"
        )

        if service_id:

            bookings = bookings.filter(
                service_id=service_id
            )

        vendor_id = request.GET.get(
            "vendor"
        )

        if vendor_id:

            bookings = bookings.filter(
                vendor_id=vendor_id
            )

        status = request.GET.get(
            "status"
        )

        if status:

            bookings = bookings.filter(
                status=status
            )

        start_date = request.GET.get(
            "start_date"
        )

        end_date = request.GET.get(
            "end_date"
        )

        if start_date and end_date:

            bookings = bookings.filter(

                booking_created_at__date__range=[
                    start_date,
                    end_date
                ]

            )

        for booking in bookings:
            assigned_history = (
                booking.history.filter(
                    status="assigned"
                ).order_by(
                    "created_at"
                ).first()
            )

            if assigned_history:
                booking.assigned_time = (
                    assigned_history.created_at
                )

                diff = (

                    assigned_history.created_at
                    - booking.booking_created_at

                )
                booking.assign_hours = round(diff.total_seconds() / 3600,2)
            else:
                booking.assigned_time = None
                booking.assign_hours = None
        total_count = bookings.count()
        pending_count = bookings.filter(status="pending").count()
        progress_count = bookings.filter(status="in_progress").count()
        completed_count = bookings.filter(status="completed").count()
        # PAGINATION
        page_obj = paginate_queryset(request,bookings,10)
        context = {

            "bookings": page_obj,
            "services": services,
            "vendors": vendors,
            "page_obj": page_obj,
            "total_count": total_count,
            "pending_count": pending_count,
            "progress_count": progress_count,
            "completed_count": completed_count,

        }
        return render(request,"superadmin/superadmin_orders.html",context)
    


# superadmin renewal the leads

# superadmin can track the payments
@method_decorator(never_cache, name="dispatch")
class SuperAdminPaymentsView(LoginRequiredMixin, View):
    """Track all payments."""

    def dispatch(self, request, *args, **kwargs):

        if request.user.role not in mainly_allowed_roles:
            return redirect("dashboard")

        return super().dispatch(request, *args, **kwargs)

    def get(self, request):

        payments = (
            Payment.objects.select_related(
                "booking",
                "booking__user",
                "vendor",
                "service"
            )
            .order_by("-payment_created_at")
        )

        payment_status = request.GET.get("payment_status")
        search = request.GET.get("search")

        if payment_status:
            payments = payments.filter(status=payment_status)

        if search:
            payments = payments.filter(
                Q(booking__order_id__icontains=search) |
                Q(booking__name__icontains=search) |
                Q(booking__phone__icontains=search)
            )

        page_obj = paginate_queryset(request, payments, 10)

        context = {
            "payments": page_obj,
            "page_obj": page_obj,
            "payment_status": payment_status,
            "search": search,
        }

        return render(
            request,
            "superadmin/superadmin_payments.html",
            context,
        )

# permisison per admin in index page 
class AdminPermissionsView(LoginRequiredMixin,View):

    """
    Superadmin Manage Admin Permissions
    """

    def get(self, request):

        # ONLY SUPERADMIN

        if request.user.role != "superadmin":

            return redirect(
                "login"
            )

        # SEARCH

        search = request.GET.get(
            "search"
        )

        # SELECTED ADMIN

        selected_admin_id = request.GET.get(
            "admin"
        )

        # ADMINS

        admins = User.objects.filter(
            role="admin"
        ).order_by(
            "-id"
        )

        # SEARCH FILTER

        if search:

            admins = admins.filter(

                Q(first_name__icontains=search) |

                Q(last_name__icontains=search) |

                Q(email__icontains=search)

            )

        # ALL CORE PERMISSIONS

        permissions = Permission.objects.filter(

            content_type__app_label="core"

        ).select_related(
            "content_type"
        ).order_by(
            "content_type_id",
            "id"
        )
        selected_admin = None
        if selected_admin_id:
            try:
                selected_admin = User.objects.get(
                    id=selected_admin_id,
                    role="admin"
                )

            except User.DoesNotExist:
                selected_admin = None
        grouped_permissions = defaultdict(list)
        for permission in permissions:
            model_name = permission.content_type.model
            grouped_permissions[
                model_name
            ].append(
                permission
            )

        context = {

            "admins": admins,
            "search": search,
            "selected_admin": selected_admin,
            "grouped_permissions": dict(
                grouped_permissions
            )

        }

        return render(request,"superadmin/admin_permissions.html",context)

    def post(self, request):
        if request.user.role != "superadmin":
            return redirect(
                "login"
            )

        admin_id = request.POST.get(
            "admin_id"
        )
        if not admin_id:

            messages.error(request,"Please Select Admin")

            return redirect(
                "admin_permissions"
            )

        permission_ids = request.POST.getlist(
            "permissions"
        )

        try:

            admin = User.objects.get(

                id=int(admin_id),

                role="admin"

            )

        except User.DoesNotExist:

            messages.error(

                request,

                "Admin Not Found"

            )

            return redirect(
                "admin_permissions"
            )

        admin.user_permissions.clear()
        permissions = Permission.objects.filter(
            id__in=permission_ids
        )
        admin.user_permissions.add(
            *permissions
        )

        messages.success(

            request,

            "Permissions Updated Successfully"

        )

        return redirect(f"/admin-permissions/?admin={admin.id}")

# ===============================================================================================
# admin dashboard
# ================================================================================================


@method_decorator(never_cache, name='dispatch')
class AdminDashboardView(LoginRequiredMixin,RoleRequiredMixin,View):

    """ Admin Dashboard """

    allowed_roles = ['admin']

    def get(self, request):
        current_admin = request.user

        customers = User.objects.filter(
    role="customer",
    city__icontains=current_admin.city.strip(),
    is_active=True
)

        vendors = User.objects.filter(
    role="vendor",
    city__icontains=current_admin.city.strip(),
    is_active=True
)

        bookings = Booking.objects.filter(
            city__iexact=current_admin.city
                )

        total_customers = customers.count()

        total_vendors = vendors.count()
        booking_counts = bookings.aggregate(

            total_bookings=Count("id"),

            total_pending=Count(
                "id",
                filter=Q(status="pending")
            ),

            total_assigned=Count(
                "id",
                filter=Q(status="assigned")
            ),

            total_accepted=Count(
                "id",
                filter=Q(status="accepted")
            ),

            total_in_progress=Count(
                "id",
                filter=Q(status="in_progress")
            ),

            total_completed=Count(
                "id",
                filter=Q(status="completed")
            ),

            total_cancelled=Count(
                "id",
                filter=Q(status="cancelled")
            ),

        )

        current_year = timezone.now().year

        monthly_counts = bookings.filter(

            booking_created_at__year=current_year

        ).annotate(

            month=TruncMonth(
                "booking_created_at"
            )

        ).values(

            "month"

        ).annotate(

            total=Count("id")

        ).order_by(

            "month"

        )

        month_map = {

            item["month"].month: item["total"]

            for item in monthly_counts

        }

        month_labels = [

            datetime(
                current_year,
                month,
                1
            ).strftime("%b")

            for month in range(1, 13)

        ]

        monthly_data = [

            month_map.get(
                month,
                0
            )

            for month in range(1, 13)

        ]

        categories = Category.objects.all()

        selected_category = request.GET.get(
            "category"
        )

        services = CategoryService.objects.all()

        if selected_category:

            services = services.filter(
                category_id=selected_category
            )

        service_labels = [
            service.s_title
            for service in services
        ]

        service_data = [

            bookings.filter(
                service=service
            ).count()

            for service in services

        ]

        recent_bookings = bookings.order_by(
            "-booking_created_at"
        )[:5]

        context = {

            'page_title': 'Dashboard',
            'total_customers': total_customers,
            'total_vendors': total_vendors,
            'total_bookings': booking_counts["total_bookings"],
            'total_pending': booking_counts["total_pending"],
            'total_assigned': booking_counts["total_assigned"],
            'total_accepted': booking_counts["total_accepted"],
            'total_in_progress': booking_counts["total_in_progress"],
            'total_completed': booking_counts["total_completed"],
            'total_cancelled': booking_counts["total_cancelled"],
            'month_labels': month_labels,
            'monthly_data': monthly_data,
            'categories': categories,
            'selected_category': selected_category,
            'service_labels': json.dumps(
                service_labels
            ),

            'service_data': json.dumps(
                service_data
            ),

            'recent_bookings': recent_bookings,
        }

        return render(request,"admin/dashboard.html",context)


# admin can approve the vendor
@method_decorator(never_cache, name='dispatch')
class AdminVendorApprovalView(LoginRequiredMixin, View):
    "vendor approve and see the vendor profile details"
    def get(self, request):

        if request.user.role != "admin":

            return JsonResponse({
                "error": "Unauthorized"
            }, status=403)

        # ONLY MATCHED CITY VENDORS

        vendors = User.objects.filter(role="vendor").filter(
                city__iexact=request.user.city.strip()
            
        ).select_related(

            "vendor_profile"

        ).prefetch_related(

            "vendor_profile__services"

        ).order_by("-id")

        q = request.GET.get("q")
        status = request.GET.get("status")

        # SEARCH

        if q:

            vendors = vendors.filter(
                first_name__icontains=q
            )

        # STATUS FILTER

        if status == "active":

            vendors = vendors.filter(
                is_active=True
            )
        elif status == "pending":

            vendors = vendors.filter(
                is_active=False
            )
    
        page_obj = paginate_queryset(request,vendors,10)
        categories = Category.objects.all()
        context={
                "vendors": page_obj,
                "page_obj": page_obj,
                "categories": categories,
                "q": q,
                "status": status
            }
        return render(request, "admin/admin_approve_vendor.html", context)


# admin  see all users and update the behaviour
@method_decorator(never_cache, name='dispatch')
class AdminUsersView(LoginRequiredMixin,View):

    """ Admin Users View """

    def get(self, request):

        if request.user.role != "admin":

            return redirect("login")

        role = request.GET.get(
            "role"
        )
        search = request.GET.get(
            "search"
        )
        admin_city = (
            request.user.city or ""
        ).strip()
        users = User.objects.filter(

            role__in=[
                "customer",
                "vendor"
            ],
        )
        if admin_city:

            users = users.filter(

                city__icontains=
                admin_city

            )
        users = users.distinct()

        if role:
            users = users.filter(
                role=role
            )

        if search:
            users = users.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(username__icontains=search) |
                Q(email__icontains=search)

            )
        users = users.order_by("-id")
        customer_count = users.filter(
            role="customer"
        ).count()

        vendor_count = users.filter(
            role="vendor"
        ).count()

        total_users = users.count()
        page_obj = paginate_queryset(request,users,10)

        context = {

            "page_obj": page_obj,
            "users": page_obj,
            "customer_count": customer_count,
            "vendor_count": vendor_count,
            "total_users": total_users,
            "active_page": "admin_all_users",

        }

        return render(request,"admin/all_users.html",context)



    def post(self, request):
        if request.user.role != "admin":
            return JsonResponse({

                "success": False,
                "error": "Access Denied"

            })

        try:

            data = json.loads(request.body)
            user_id = data.get("user_id")
            behaviour = data.get("behaviour")
            admin_city = (
                request.user.city or ""
            ).strip()
            user = User.objects.filter(
                id=user_id,
                role__in=[
                    "customer",
                    "vendor"
                ],

                city__icontains=
                admin_city

            ).first()

            if not user:

                return JsonResponse({

                    "success": False,
                    "error": "User not found"

                })

            user.behaviour = behaviour
            user.save()

            return JsonResponse({

                "success": True

            })

        except Exception as e:

            return JsonResponse({"success": False,"error": str(e)})


# admin all leads see and assign the vendors 
@method_decorator(never_cache,name='dispatch')
class AdminOrdersView(LoginRequiredMixin,View):

    ''' admin manage city based bookings,vendors,status,payments and service filters '''

    def get(self,request):

        if request.user.role!="admin":
            return redirect("login")

        category_id=request.GET.get("category")
        service_id=request.GET.get("service")
        city=request.GET.get("city")
        q=request.GET.get("q")
        postal_code=request.GET.get("postal_code")

        bookings=Booking.objects.filter(
            city__iexact=request.user.city
        ).select_related(
            "service","vendor"
        ).order_by("-id")

        if category_id:
            bookings=bookings.filter(
                service__category_id=category_id
            )

        if service_id:
            bookings=bookings.filter(
                service_id=service_id
            )

        if q:
            bookings=bookings.filter(
                Q(name__icontains=q)|
                Q(phone__icontains=q)|
                Q(city__icontains=q)|
                Q(order_id__icontains=q)
            )

        if postal_code:
            bookings=bookings.filter(
                vendor__vendor_profile__postal_code__icontains=postal_code
            )

        categories=Category.objects.all()

        services=CategoryService.objects.filter(
            category_id=category_id
        ) if category_id else CategoryService.objects.all()

        cities=Booking.objects.filter(
            city__iexact=request.user.city
        ).exclude(
            city__isnull=True
        ).exclude(
            city=""
        ).values_list(
            "city",flat=True
        ).distinct()

        vendors = User.objects.filter(
        role="vendor",
        city__icontains=
        request.user.city.strip(),
        is_active=True).select_related(
        "vendor_profile"
        ).prefetch_related(
        "vendor_profile__services"
        ).distinct()
        if service_id:
            vendors=vendors.filter(
                vendor_profile__services__id=service_id
            )

        elif category_id:
            vendors=vendors.filter(
                vendor_profile__category_id=category_id
            )

        if postal_code:
            vendors=vendors.filter(
                vendor_profile__postal_code__icontains=postal_code
            )

        page_obj=paginate_queryset(
            request,bookings,10
        )
        # LEAD NOTIFICATIONS

        lead_notifications = []

        pending_bookings = Booking.objects.filter(
            city__iexact=request.user.city,
            vendor__isnull=True
        ).order_by("-booking_created_at")[:6]

        for booking in pending_bookings:

            diff = timezone.now() - booking.booking_created_at

            hours = int(
                diff.total_seconds() / 3600
            )

            booking.pending_hours = hours

            # ALERT TYPES

            if hours < 12:

                booking.alert_type = "waiting"

                booking.alert_title = "Lead Waiting"

                booking.alert_message = (
                    "Move to vendor soon"
                )

            elif hours < 24:

                booking.alert_type = "urgent"

                booking.alert_title = "Urgent Lead"

                booking.alert_message = (
                    "Pending vendor assignment"
                )

            else:

                booking.alert_type = "delayed"

                booking.alert_title = "Lead Delayed"

                booking.alert_message = (
                    "Assign vendor immediately"
                )

            lead_notifications.append(
                booking
            )       

        context ={

            "bookings":page_obj,
            "page_obj":page_obj,
            "vendors":vendors.distinct(),
            "categories":categories,
            "services":services,
            "cities":cities,
            "selected_category":category_id,
            "selected_service":service_id,
            "selected_city":city,
            "q":q,
            "postal_code":postal_code,
            "lead_notifications":lead_notifications,

        }

        return render(request,"admin/admin_orders.html",context)

    def post(self,request):

        try:

            data=json.loads(request.body)

            booking_id=data.get("booking_id")
            status=data.get("status")
            total_amount=data.get("total_amount")

            allowed_status=[
                "pending",
                "assigned",
                "accepted",
                "in_progress",
                "completed",
                "cancelled"
            ]

            booking=get_object_or_404(
                Booking,
                id=booking_id,
                city__iexact=request.user.city
            )

            if total_amount:

                total_amount=Decimal(total_amount)

                payment=Payment.objects.filter(
                    booking=booking
                ).first()

                if payment:

                    payment.total_amount=total_amount

                    payment.remaining_amount=(
                        total_amount-payment.paid_amount
                    )

                    payment.save()

                else:

                    payment=Payment.objects.create(
                        booking=booking,
                        vendor=booking.vendor,
                        service=booking.service,
                        total_amount=total_amount,
                        paid_amount=Decimal("0"),
                        remaining_amount=total_amount
                    )

                return JsonResponse({
                    "success":True,
                    "total_amount":str(payment.total_amount)
                })

            if status:

                if status not in allowed_status:
                    return JsonResponse({
                        "error": "Invalid status"
                    }, status=400)

                booking.status = status
                booking.save()

                BookingHistory.objects.create(
                    booking=booking,
                    status=status,
                    updated_by=request.user
                )

                # Create payment automatically when booking is completed
                if status == "completed":

                    Payment.objects.get_or_create(
                        booking=booking,
                        defaults={
                            "vendor": booking.vendor,
                            "service": booking.service,
                            "total_amount": Decimal("0"),
                            "paid_amount": Decimal("0"),
                            "remaining_amount": Decimal("0"),
                            "status": "pending",
                        }
                    )

            return JsonResponse({
                "success": True
            })
        except Exception as e:

            return JsonResponse({
                "error":str(e)
            },status=400)

# admin payments page view

@method_decorator(never_cache,name='dispatch')
class AdminPaymentsView(LoginRequiredMixin,View):

    ''' manage payments, payment status, due amounts and payment methods for admin and superadmin '''

    def dispatch(self,request,*args,**kwargs):

        if request.user.role not in ["admin","superadmin"]:
            return redirect("dashboard")

        return super().dispatch(
            request,*args,**kwargs
        )

    def get(self,request):

        payments=Payment.objects.select_related(
            "booking",
            "booking__user",
            "vendor",
            "service",
            "service__category"
        ).order_by("-id")

        if request.user.role!="superadmin":

            payments=payments.filter(
                booking__city__iexact=request.user.city
            )

        payment_status=request.GET.get(
            "payment_status"
        )

        if payment_status:

            payments=payments.filter(
                status=payment_status
            )

        for p in payments:

            p.payment_method=(
                p.payment_method or "Cash"
            )

        page_obj=paginate_queryset(request,payments,10)
        context= {
                "payments":page_obj,
                "page_obj":page_obj,
            }
        return render(request,"admin/admin_payments.html",context)

    def post(self,request):

        payment_id=request.POST.get(
            "payment_id"
        )

        if not payment_id:
            return redirect(
                "admin_payments"
            )

        filters={"id":payment_id}

        if request.user.role!="superadmin":

            filters[
                "booking__city__iexact"
            ]=request.user.city

        payment=get_object_or_404(Payment,**filters)
        payment_method=request.POST.get("payment_method")
        due_date=request.POST.get("due_date")
        payment_request=request.POST.get("payment_request")
        paid_amount=request.POST.get("paid_amount")

        if payment_method:
            payment.payment_method=payment_method

        if due_date:
            payment.due_date=due_date

        if payment_request:
            payment.payment_request=payment_request

        if paid_amount:
            paid_amount_decimal=Decimal(paid_amount)
            total_amount=Decimal(payment.total_amount or 0)
            remaining=(total_amount-paid_amount_decimal)
            payment.paid_amount=paid_amount_decimal
            payment.remaining_amount=remaining

            if remaining<=0:
                payment.status="paid"

            elif paid_amount_decimal>0:
                payment.status="partial_paid"

            else:
                payment.status="pending"

        payment.payment_method=(
            payment.payment_method or "Cash"
        )
        payment.save()

        return redirect("admin_payments")
    
    
# remarks 
    
    

@method_decorator(never_cache,name='dispatch')
class AdminLeadsView(LoginRequiredMixin,View):

    ''' manage admin leads,bookings,renewals,slots and status updates '''

    login_url="/login/"

    def get(self,request):

        if request.user.role!="admin":
            return HttpResponse("Not allowed")

        bookings=Booking.objects.select_related(
            "user","vendor","service","category"
        ).prefetch_related(
            "payments"
        ).order_by("-id")

        status=request.GET.get("status")
        search=request.GET.get("search")

        if status:
            bookings=bookings.filter(status=status)

        if search:
            bookings=bookings.filter(
                Q(order_id__icontains=search)|
                Q(service__s_title__icontains=search)|
                Q(user__first_name__icontains=search)|
                Q(vendor__first_name__icontains=search)
            )
        context={
            "bookings":bookings
        }
        return render(request,"admin/admin_leads.html",context)

    def post(self,request):

        try:

            data=json.loads(request.body)

            booking=get_object_or_404(
                Booking,
                id=data.get("booking_id")
            )

            action=data.get("action")

            if action=="accept_renewal":

                booking.renewal_requested=False
                booking.is_renewed=True
                booking.status="accepted"
                booking.save()

                BookingHistory.objects.create(
                    booking=booking,
                    status="Renewal Accepted",
                    updated_by=request.user
                )

                return JsonResponse({"success":True})

            if action=="edit_slot":

                booking.scheduled_date=data.get("scheduled_date")
                booking.scheduled_time=data.get("scheduled_time")
                booking.start_date=data.get("start_date")
                booking.end_date=data.get("end_date")

                booking.save()

                BookingHistory.objects.create(
                    booking=booking,
                    status="Booking Updated",
                    updated_by=request.user
                )

                return JsonResponse({"success":True})

            booking.status=data.get("status")
            booking.save()

            BookingHistory.objects.create(
                booking=booking,
                status=booking.status,
                updated_by=request.user
            )

            return JsonResponse({"success":True})

        except Exception as e:

            return JsonResponse({
                "error":str(e)
            })







# ============================
# vendor dashboard
# ==========================

@method_decorator(never_cache,name='dispatch')
class VendorDashboardView(LoginRequiredMixin,View):

    ''' vendor dashboard view for managing leads,customers and monthly booking analytics '''

    def get(self,request):

        if request.user.role!="vendor":
            return redirect("login")

        vendor=request.user

        bookings=Booking.objects.filter(
            vendor=vendor
        )

        counts=bookings.aggregate(

            total_leads=Count("id"),
            assigned_leads=Count("id",filter=Q(status="assigned")),
            progress_leads=Count("id",filter=Q(status="progress")),
            completed_leads=Count("id",filter=Q(status="completed")),
            cancelled_leads=Count("id",filter=Q(status="cancelled")),
            pending_leads=Count("id",filter=Q(status="pending"))
        )

        total_customers=bookings.values(
            "user"
        ).distinct().count()
        current_year = timezone.now().year

        monthly_counts = bookings.filter(

            booking_created_at__year=current_year

        ).annotate(

            month=TruncMonth(
                "booking_created_at"
            )

        ).values(

            "month"

        ).annotate(

            total=Count("id")

        ).order_by(

            "month"

        )

        month_map = {

            item["month"].month: item["total"]

            for item in monthly_counts

        }

        jan_leads = month_map.get(1, 0)

        feb_leads = month_map.get(2, 0)

        mar_leads = month_map.get(3, 0)

        apr_leads = month_map.get(4, 0)

        may_leads = month_map.get(5, 0)

        jun_leads = month_map.get(6, 0)

        jul_leads = month_map.get(7, 0)

        aug_leads = month_map.get(8, 0)

        sep_leads = month_map.get(9, 0)

        oct_leads = month_map.get(10, 0)

        nov_leads = month_map.get(11, 0)

        dec_leads = month_map.get(12, 0)

        recent_leads=bookings.order_by(
            "-booking_created_at"
        )[:8]
        context={

            "total_leads":counts["total_leads"],
            "assigned_leads":counts["assigned_leads"],
            "progress_leads":counts["progress_leads"],
            "completed_leads":counts["completed_leads"],
            "cancelled_leads":counts["cancelled_leads"],
            "pending_leads":counts["pending_leads"],
            "total_customers":total_customers,
            "jan_leads":jan_leads,
            "feb_leads":feb_leads,
            "mar_leads":mar_leads,
            "apr_leads":apr_leads,
            "may_leads":may_leads,
            "jun_leads":jun_leads,
            "jul_leads":jul_leads,
            "aug_leads":aug_leads,
            "sep_leads":sep_leads,
            "oct_leads":oct_leads,
            "nov_leads":nov_leads,
            "dec_leads":dec_leads,

            "recent_leads":recent_leads,

        }
        return render(request,"vendor/dashboard.html",context)
        
        

@method_decorator(never_cache,name='dispatch')
class VendorProfileView(LoginRequiredMixin,View):

    ''' vendor profile update view for managing profile,category and service details '''

    def get(self,request,id):

        if request.user.role!="vendor":
            return redirect("login")

        vendor=get_object_or_404(User,id=id,role="vendor")
        profile,_=VendorProfile.objects.get_or_create(user=vendor)
        categories=Category.objects.all()
        services=CategoryService.objects.filter(
            category=profile.category
        ) if profile.category else CategoryService.objects.none()
        context={
            "vendor":vendor,
            "profile":profile,
            "categories":categories,
            "services":services
        }
        return render(request,"vendor/vendor_profile.html",context)

    def post(self,request,id):

        if request.user.role!="vendor":
            return redirect("login")

        vendor=get_object_or_404(User,id=id,role="vendor")
        profile,_=VendorProfile.objects.get_or_create(user=vendor)
        category_id=request.POST.get("category")
        vendor.first_name=request.POST.get("first_name")
        vendor.last_name=request.POST.get("last_name")
        vendor.email=request.POST.get("email")
        vendor.save()
        profile.experience=request.POST.get("experience")
        profile.locality=request.POST.get("locality")
        profile.street=request.POST.get("street")
        profile.city=request.POST.get("city")
        profile.postal_code=request.POST.get("postal_code")
        profile.company_name=request.POST.get("company_name")
        profile.company_address=request.POST.get("company_address")
        profile.pan_number=request.POST.get("pan_number")
        profile.license_number=request.POST.get("license_number")

        if request.FILES.get("pan_card"):
            profile.pan_card=request.FILES.get("pan_card")

        if request.FILES.get("license_file"):
            profile.license_file=request.FILES.get("license_file")

        if category_id:
            profile.category_id=category_id

        profile.save()

        service_ids=request.POST.getlist("services")

        if service_ids:
            profile.services.set(service_ids)

        return redirect(
            "vendor_profile",
            id=vendor.id
        )

# vendor leads views 

@method_decorator(never_cache,name='dispatch')
class VendorOrdersView(LoginRequiredMixin,View):

    ''' vendor manage orders,payments,renewals and booking status updates '''

    def get(self,request):

        if request.user.role!="vendor":
            return HttpResponse("Not allowed")

        bookings=Booking.objects.filter(
            vendor=request.user
        ).select_related(
            "service",
            "user",
            "category"
        ).prefetch_related(
            "payments"
        ).order_by("-id")

        status=request.GET.get("status")
        date=request.GET.get("date")

        if status:
            bookings=bookings.filter(
                status=status
            )

        if date:
            bookings=bookings.filter(
                booking_created_at__date=date
            )

        page_obj=paginate_queryset(
            request,bookings,10
        )
        context={
            "bookings":page_obj,
            "page_obj":page_obj,
        }
        return render(request,"vendor/vendor_orders.html",context)

    def post(self,request):

        if "screenshot" in request.FILES:

            booking_id=request.POST.get("booking_id")
            txn=request.POST.get("transaction_id")
            file=request.FILES["screenshot"]

            booking=get_object_or_404(
                Booking,
                id=booking_id
            )

            if booking.vendor!=request.user:
                return JsonResponse({
                    "error":"Not allowed"
                },status=403)

            if booking.status!="completed":
                return JsonResponse({
                    "error":"Complete order first"
                },status=400)

            payment,created=Payment.objects.get_or_create(

                booking=booking,

                defaults={
                    "vendor":request.user,
                    "service":booking.service,
                }
            )

            if not created and payment.status=="paid":

                return JsonResponse({
                    "error":"Payment already submitted"
                },status=400)

            payment.transaction_id=txn
            payment.screenshot=file
            payment.status="paid"
            payment.vendor=request.user

            payment.save()

            return JsonResponse({
                "success":True
            })

        try:

            data=json.loads(request.body)

            booking_id=data.get("booking_id")
            renew_accept=data.get("renew_accept")
            status=data.get("status")

            booking=get_object_or_404(
                Booking,
                id=booking_id
            )

            if booking.vendor!=request.user:
                return JsonResponse({
                    "error":"Not allowed"
                },status=403)

            if renew_accept:

                booking.renewal_requested=False
                booking.is_renewed=True
                booking.status="accepted"

                booking.save()

                BookingHistory.objects.create(
                    booking=booking,
                    status="accepted",
                    updated_by=request.user
                )

                return JsonResponse({
                    "success":True
                })

            allowed_status=[
                "pending",
                "accepted",
                "in_progress",
                "completed",
                "cancelled"
            ]

            if status not in allowed_status:

                return JsonResponse({
                    "error":"Invalid status"
                },status=400)

            booking.status=status

            booking.save()

            BookingHistory.objects.create(
                booking=booking,
                status=status,
                updated_by=request.user
            )

            return JsonResponse({
                "success":True
            })

        except Exception as e:

            return JsonResponse({
                "error":str(e)
            },status=400)



# vendor payment view
@method_decorator(never_cache, name='dispatch')
class VendorPaymentsView(LoginRequiredMixin, View):

    def get(self, request):

        if request.user.role != "vendor":

            return redirect("login")

        bookings = Booking.objects.filter(

            vendor=request.user,

            status__in=[

                "accepted",
                "in_progress",
                "completed"

            ]

        ).select_related(

            "user",
            "service"

        ).prefetch_related(

            "payments"

        ).order_by("-id")

        # PAYMENT STATUS FILTER

        payment_status = request.GET.get(
            "payment_status"
        )

        # FIXED ISSUE

        if payment_status:
            bookings = [
                b for b in bookings

                if (

                    b.payments.first()
                    and
                    b.payments.first().status == payment_status

                )

            ]
        # DUE DATE VALUES

        for b in bookings:
            payment = b.payments.first()
            if payment:
                b.due_date_value = (

                    str(payment.due_date)

                    if payment.due_date

                    else ""

                )

            else:

                b.due_date_value = ""

        # PAGINATION

        page_obj = paginate_queryset(request,bookings,10)
        context = {

            "bookings": page_obj,
            "page_obj": page_obj,

        }
        return render(request,"vendor/vendor_payments.html",context)
   
   
        
#  not used   
@method_decorator(never_cache, name='dispatch')      
class VendorPaymentPageView(LoginRequiredMixin, View):

    def get(self, request, booking_id):

        booking = get_object_or_404(
            Booking,
            id=booking_id,
            vendor=request.user
        )

        payment = Payment.objects.filter(
            booking=booking
        ).first()

        context = {
            "booking": booking,
            "payment": payment
        }

        return render(
            request,
            "vendor/payment_page.html",
            context
        )

    def post(self, request, booking_id):

        booking = get_object_or_404(
            Booking,
            id=booking_id,
            vendor=request.user
        )

        transaction_id = request.POST.get("transaction_id")
        status = request.POST.get("status")
        screenshot = request.FILES.get("screenshot")
        payment, created = Payment.objects.get_or_create(

            booking=booking,

            defaults={

                "vendor": request.user,
                "service": booking.service,
                "total_amount": 0,
                "status": "pending"
            }
        )

        if status:
            payment.status = status
        if transaction_id:
            payment.transaction_id = transaction_id
        if screenshot:
            payment.screenshot = screenshot

        payment.vendor = request.user
        payment.save()
        messages.success(
            request,
            "Payment Updated Successfully"
        )

        return redirect("vendor_payments")       
   




# vendor payment show view

@method_decorator(never_cache,name='dispatch')
class VendorPaymentsShowView(LoginRequiredMixin,View):

    ''' vendor payment management view for tracking paid,partial and pending payments '''

    def get(self,request):

        if request.user.role!="vendor":
            return redirect("login")

        bookings=Booking.objects.filter(
            vendor=request.user,
            status__in=[
                "accepted",
                "in_progress",
                "completed"
            ]
        ).select_related(
            "user",
            "service"
        ).prefetch_related(
            "payments"
        ).order_by("-id")

        payment_status=request.GET.get(
            "payment_status"
        )

        if payment_status:

            filtered=[]

            for b in bookings:

                payment=b.payments.first()

                if payment_status=="paid" and payment and payment.status=="paid":
                    filtered.append(b)

                elif payment_status=="partial_paid" and payment and payment.status=="partial_paid":
                    filtered.append(b)

                elif payment_status=="pending" and (
                    not payment or payment.status=="pending"
                ):
                    filtered.append(b)

            bookings=filtered

        for b in bookings:

            payment=b.payments.first()

            if payment:

                b.total_amount_value=payment.total_amount or 0
                b.paid_amount_value=payment.paid_amount or 0
                b.remaining_amount_value=payment.remaining_amount or 0
                b.transaction_id_value=payment.transaction_id
                b.due_date_value=payment.due_date

            else:

                b.total_amount_value=0
                b.paid_amount_value=0
                b.remaining_amount_value=0
                b.transaction_id_value=""
                b.due_date_value=None

        page_obj=paginate_queryset(request,bookings,10)
        context={

            "bookings":page_obj,
            "page_obj":page_obj,

        }
        return render(request,"vendor/vendor_payment_show.html",context)

    def post(self,request):

        if request.user.role!="vendor":
            return redirect("login")

        booking=get_object_or_404(
            Booking,
            id=request.POST.get("booking_id"),
            vendor=request.user
        )

        payment=booking.payments.first()

        if payment:

            paid_amount_decimal=Decimal(
                request.POST.get("paid_amount")
            )

            remaining=(
                payment.total_amount-paid_amount_decimal
            )

            if remaining<0:
                remaining=Decimal("0")

            payment.paid_amount=paid_amount_decimal
            payment.remaining_amount=remaining

            if paid_amount_decimal>=payment.total_amount:
                payment.status="paid"

            elif paid_amount_decimal>0:
                payment.status="partial_paid"

            else:
                payment.status="pending"

            payment.save()

        return redirect(
            "vendor_payment_show"
        )

@method_decorator(never_cache, name='dispatch')
class VendorHelpView(LoginRequiredMixin, View):
    """ vendor  help page views"""

    def get(self, request):

        if request.user.role != "vendor":

            return redirect("login")

        # MATCHED CITY ADMIN
        admin_user = User.objects.filter(
            role="admin",
            city__iexact=request.user.city,
            is_active=True
        ).first()

        context = {
            "admin_user": admin_user
        }

        return render(request,"vendor/vendor_help.html",context)


# ===============================
# customer
# ==============================

# customer dashboard


@method_decorator(never_cache, name='dispatch')
class CustomerDashboardView(LoginRequiredMixin,RoleRequiredMixin,View):
    """ Customer Dashboard """

    login_url = "/login/"
    allowed_roles = ["customer"]

    def get(self, request, *args, **kwargs):

        user = request.user

        # Customer Bookings
        bookings = Booking.objects.filter(
            user=user
        )
        total_bookings = bookings.count()
        pending_bookings = bookings.filter(status="pending").count()
        completed_bookings = bookings.filter(status="completed").count()
        cancelled_bookings = bookings.filter(status="cancelled").count()
        completion_rate = 0
        if total_bookings > 0:
            completion_rate = round(
                (completed_bookings / total_bookings) * 100
            )
        recent_bookings = bookings.order_by(
            "-booking_created_at"
        )[:5]

        service_stats = (
            bookings.values(
                "service__s_title"
            )
            .annotate(
                total=Count("id")
            )
            .order_by("-total")
        )

        service_labels = [
            item["service__s_title"]
            for item in service_stats
        ]

        service_counts = [
            item["total"]
            for item in service_stats
        ]

        today = now().date()

        weekly_labels = []
        weekly_counts = []

        for i in range(6, -1, -1):

            day = today - timedelta(days=i)

            count = bookings.filter(
                booking_created_at__date=day
            ).count()

            weekly_labels.append(
                day.strftime("%a")
            )

            weekly_counts.append(count)


        from .models import Cart
        cart_count = 0
        try:
            cart = Cart.objects.get(user=user)
            cart_count = cart.total_items
        except Cart.DoesNotExist:
            pass

        context = {

            "total_bookings": total_bookings,
            "pending_bookings": pending_bookings,
            "completed_bookings": completed_bookings,
            "cancelled_bookings": cancelled_bookings,
            "completion_rate": completion_rate,
            "recent_bookings": recent_bookings,
            "service_labels": service_labels,
            "service_counts": service_counts,
            "weekly_labels": weekly_labels,
            "weekly_counts": weekly_counts,
            "cart_count": cart_count,
        }

        return render(request,"customer/dashboard.html",context)
        




# get the all service in customer dashboard

class ServicesListingView(ListView):
    """ customer can see the all servcies and book that service without goes to landing page"""
    model = ServicesCards
    template_name = "customer/get_all_service.html"
    context_object_name = "services_cards"

    def get_queryset(self):

        queryset = ServicesCards.objects.all().order_by(
            "servicename"
        )
        letter = self.request.GET.get(
            "letter"
        )

        if letter:

            queryset = queryset.filter(
                servicename__istartswith=letter
            )

        return queryset

    def get_context_data(self, **kwargs):

        context = super().get_context_data(
            **kwargs
        )

        context["categories"] = Category.objects.all()

        context["selected_letter"] = self.request.GET.get("letter","")

        context["alphabet_list"] = list(
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        )

        return context
    
    
#customer all orders 
@method_decorator(never_cache, name='dispatch')
class CustomerOrdersView(LoginRequiredMixin, View):
    """ customer orders """

    def get(self, request):

        bookings = Booking.objects.filter(
            user=request.user
        ).select_related(
            "service",
            "vendor",
            "category"
        ).prefetch_related(
            "payments"
        ).order_by("-id")

        status = request.GET.get("status")
        search = request.GET.get("search")

        if status:
            bookings = bookings.filter(status=status)

        if search:

            bookings = bookings.filter(

                Q(order_id__icontains=search) |
                Q(service__s_title__icontains=search)

            )

        page_obj = paginate_queryset(request,bookings,10)
        context= {
                "bookings": page_obj,
                "page_obj": page_obj,
            }
        return render(request,"customer/customer_orders.html",context)
        
# customer payemnts
@method_decorator(never_cache, name='dispatch')
class CustomerPaymentsView(LoginRequiredMixin, View):
    """  customer can trqack the order payements clearly"""

    def get(self, request):

        bookings = (
            Booking.objects.filter(
                user=request.user
            )
            .select_related(
                "service",
                "vendor",
                "category"
            )
            .prefetch_related(
                "payments"
            )
            .order_by("-id")
        )

        payment_status = request.GET.get("payment_status")
        search = request.GET.get("search")

        booking_data = []

        for booking in bookings:

            payment = booking.payments.first()
            if payment_status == "paid":

                if not payment or payment.status != "paid":
                    continue

            elif payment_status == "pending":

                if payment and payment.status == "paid":
                    continue

            if search:

                search_value = search.lower()

                order_match = (
                    search_value in str(booking.order_id).lower()
                )

                service_match = (
                    booking.service and
                    search_value in booking.service.s_title.lower()
                )

                transaction_match = (
                    payment and
                    payment.transaction_id and
                    search_value in payment.transaction_id.lower()
                )

                if not (
                    order_match or
                    service_match or
                    transaction_match
                ):
                    continue

            booking_data.append({
                "booking": booking,
                "payment": payment
            })
        page_obj = paginate_queryset(request,bookings,10)
        context = {
            "booking_data": booking_data,
            "bookings": page_obj,
            "page_obj": page_obj,
            
        }

        return render(request,"customer/customer_payments.html",context)
        
    def post(self, request):

        payment_id = request.POST.get("payment_id")

        payment_request = request.POST.get(
        "payment_request"
    )
        payment = get_object_or_404(
        Payment,
        id=payment_id
    )
        payment.payment_request = payment_request
        payment.save()

        return redirect("customer_payments")

# track the order in customer 
@method_decorator(never_cache, name='dispatch')
class CustomerTrackingView(LoginRequiredMixin, View):
    """ nav page in customer track the orders page """

    def get(self, request):

        bookings = Booking.objects.filter(
            user=request.user
        ).select_related(
            "service",
            "vendor"
        ).order_by("-id")

        status = request.GET.get("status")
        search = request.GET.get("search")

        if status:
            bookings = bookings.filter(status=status)

        if search:

            bookings = bookings.filter(

                Q(order_id__icontains=search) |
                Q(service__s_title__icontains=search)

            )
        page_obj = paginate_queryset(request,bookings,10)
        context= {
                "bookings": bookings,
                "bookings": page_obj,
                "page_obj": page_obj,
            }
        return render(request,"customer/customer_tracking.html",context)
        


# custoern trackig orders in time line page
@method_decorator(never_cache, name='dispatch')
class CustomerTrackingDetailView(LoginRequiredMixin, View):
    """ customer tracking order timeline """

    def get(self, request, id):

        booking = get_object_or_404(
            Booking.objects.select_related(
                "service",
                "vendor"
            ),
            id=id,
            user=request.user
        )

        history_qs = BookingHistory.objects.filter(
            booking=booking
        ).select_related(
            "updated_by"
        ).order_by("-created_at")

        grouped_history = OrderedDict()

        for item in history_qs:

            status_key = item.status.lower().strip()

            if status_key not in grouped_history:
                grouped_history[status_key] = item

        history = list(grouped_history.values())
        history.reverse()

        context = {
            "booking": booking,
            "history": history
        }

        return render(request,"customer/tracking_detail.html",context)
            
# customer can see the orders in myservcie(detail)

@method_decorator(never_cache, name='dispatch')
class CustomerOrderDetailView(LoginRequiredMixin, View):
    """ custoemr orders details iews here see the details of the services"""

    def get(self, request, id):
        booking = Booking.objects.get(
            id=id,
            user=request.user
        )
        history_qs = booking.history.select_related(
            "updated_by"
        ).order_by("-created_at")
        grouped_history = OrderedDict()
        for item in history_qs:

            status_key = item.status.lower().strip()

            if status_key not in grouped_history:

                grouped_history[status_key] = item



        history = grouped_history.values()
        context= {
                "booking": booking,
                "history": history
            }
        return render(request,"customer/order_detail.html",context)




# set the satatus in user is active/inactive in the admin can set the user is inactive or active that code here 
@method_decorator(never_cache, name='dispatch')
class SetUserStatusView(LoginRequiredMixin,View):
    """ Set User Status """

    def get(self,request,user_id,status):
        if request.user.role not in mainly_allowed_roles:
            return redirect("login")
        user = get_object_or_404(User,id=user_id)

        if status == "active":
            user.is_active = True
        elif status == "inactive":

            user.is_active = False

        user.save()
        return redirect(request.META.get("HTTP_REFERER","/"))


# admin can verify the vendor view
@method_decorator(never_cache, name='dispatch')
class AdminVendorVerifyView(LoginRequiredMixin, View):
    """ here admin can be verify the vendor view logic"""
    login_url = "/login/"

    def get(self, request, id):

        if request.user.role != "admin":
            return HttpResponse("Not allowed")

        vendor = get_object_or_404(
            User,
            id=id,
            role="vendor"
        )

        profile = vendor.vendor_profile

        context = {

            "vendor": vendor,
            "profile": profile

        }

        return render(request,"admin/vendor_verify.html",context)

    def post(self, request, id):

        if request.user.role != "admin":
            return HttpResponse("Not allowed")

        vendor = get_object_or_404(
            User,
            id=id,
            role="vendor"
        )

        profile = vendor.vendor_profile

        # TOGGLE VERIFICATION

        if "verify_status" in request.POST:

            profile.is_verified = True

        else:

            profile.is_verified = False

        profile.save()

        return redirect(
            "admin_vendor_verify",
            id=vendor.id
        )
        
# user delete view code
@method_decorator(never_cache, name='dispatch')
class DeleteUserView(View):

    def post(self, request, id):

        user = get_object_or_404(User, id=id)

        if user.role == "superadmin":
            messages.error(request, "Superadmin cannot be deleted!")
            return redirect("all_users")

        if request.user == user:
            messages.error(request, "You cannot delete yourself!")
            return redirect("all_users")

        try:
            if hasattr(user, 'cart') and user.cart:
                user.cart.session_key = f"deleted_{user.id}"
                user.cart.save()
                user.cart.delete()
        except:
            pass

        user.delete()
        messages.success(request, "User deleted successfully!")

        return redirect("all_users")



# i think this is unnecassary code 
@method_decorator(never_cache, name='dispatch')
class AllUsersAPI(View):

    def get(self, request):

        query = request.GET.get("q", "").strip()
        role = request.GET.get("role", "")

        users = User.objects.exclude(role="superadmin")

        if role:
            users = users.filter(role=role)

        if query:
            users = users.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query)
            )

        users = users.order_by("-id")

        data = [{
            "name": f"{u.first_name} {u.last_name}",
            "email": u.email,
            "phone": u.phone,
            "role": u.role
        } for u in users]

        return JsonResponse({"users": data})


# get the servcie details
@method_decorator(never_cache, name='dispatch')
class ServiceDetailView(View):

    def get(self, request, id):
        service = CategoryService.objects.get(id=id)
        return render(request, "service/detail.html", {"service": service})

    def post(self, request, id):
        request.session["service_id"] = id
        return redirect("book_service")




# boooking page code 
@method_decorator(never_cache, name='dispatch')

class BookServiceView(LoginRequiredMixin,View):

    ''' customer service booking view for single and multiple service bookings '''

    login_url="/login/"

    def get(self,request):

        categories=Category.objects.filter(
            is_active=True
        )

        return render(request,"service/book.html",{
            "categories":categories
        })

    def post(self,request):

        try:

            data=json.loads(request.body)

            name=data.get("name")
            phone=data.get("phone")
            category_id=data.get("category_id")
            service_id=data.get("service_id")
            estimated_amount = data.get("estimated_amount")
            booking_type=data.get("booking_type")
            city=data.get("city")

            if not name or not phone:
                return JsonResponse({
                    "error":"Enter name and phone"
                })

            if not category_id or not service_id:
                return JsonResponse({
                    "error":"Select category and service"
                })

            if not city:
                return JsonResponse({
                    "error":"Enter city"
                })

            category=get_object_or_404(
                Category,
                id=category_id
            )

            service=get_object_or_404(
                CategoryService,
                id=service_id
            )

            matched_admin=User.objects.filter(
                role="admin",
                city__iexact=city,
                is_active=True
            ).first()

            if not matched_admin:
                return JsonResponse({
                    "error":"No admins available in this city"
                })

            vendor=User.objects.filter(
                role="vendor",
                services=service
            ).first()

            booking_data={

                "user":request.user,
                "admin":matched_admin,
                "category":category,
                "service":service,
                "estimated_amount":estimated_amount,
                "vendor":vendor,
                "name":name,
                "phone":phone,
                "city":city,
                "address":data.get("address"),
                "problem":data.get("problem"),
                "status":"pending"

            }

            if booking_type=="single":

                booking_date=data.get("date")
                time_value=data.get("time")

                if not booking_date:
                    return JsonResponse({
                        "error":"Select booking date"
                    })

                formatted_time={

                    "09-11":"09 AM - 11 AM",
                    "011-01":"11 AM - 01 PM",
                    "01-03":"01 PM - 03 PM",
                    "03-05":"03 PM - 05 PM"

                }.get(time_value,"")

                booking_data.update({

                    "scheduled_date":booking_date,
                    "scheduled_time":formatted_time,
                    "start_date":None,
                    "end_date":None

                })

            else:

                start_date=data.get("start_date")
                end_date=data.get("end_date")

                if not start_date or not end_date:
                    return JsonResponse({
                        "error":"Select start date and end date"
                    })

                booking_data.update({

                    "scheduled_date":None,
                    "scheduled_time":None,
                    "start_date":start_date,
                    "end_date":end_date

                })

            Booking.objects.create(**booking_data)

            return JsonResponse({

                "success":True,
                "message":"Service booked successfully",
                "redirect":"/customer-dashboard/"

            })

        except Exception as e:

            return JsonResponse({
                "error":str(e)
            })
            
            
# raise a complaint in customer 
@method_decorator(never_cache, name='dispatch')
class MyBookingsView(View):

    def get(self, request):

        bookings = Booking.objects.filter(user=request.user) \
            .select_related("vendor", "service") \
            .prefetch_related("remarks") \
            .order_by("-id")
        page_obj = paginate_queryset(request,bookings,10)
        return render(request, "customer/my_bookings.html", {
            "bookings": bookings,
            "bookings": page_obj,
            "page_obj": page_obj,
        })


# get the servcie and servcie here view 
@method_decorator(never_cache, name='dispatch')
class GetServicesView(View):
    def get(self, request):
        category_id = request.GET.get("category_id")

        if not category_id:
            return JsonResponse({"services": []})

        services = CategoryService.objects.filter(category_id=category_id)

        data = {
            "services": [
                {
                    "id": s.id,
                    "name": s.s_title,
                    "desc": s.s_desc,
                    "tag": s.s_tag,
                    "image": s.image.url if s.image else ""
                }
                for s in services
            ]
        }

        return JsonResponse(data)

















@method_decorator(never_cache,name='dispatch')
class RenewBookingPageView(LoginRequiredMixin,View):

    ''' customer service renewal view for updating booking renewal request and end date '''

    login_url="/login/"

    def get(self,request,booking_id):

        booking=get_object_or_404(
            Booking,
            id=booking_id,
            user=request.user
        )
        context={
            "booking":booking
        }
        return render(request,"service/renew_booking.html",context)

    def post(self,request,booking_id):
        booking=get_object_or_404(Booking,id=booking_id,user=request.user)
        booking.end_date=request.POST.get(
            "end_date"
        )

        booking.renewal_requested=True
        booking.status="pending"
        booking.save()

        return redirect("customer_orders")




# admin see and renewal the leads 
@method_decorator(never_cache, name='dispatch')

class AdminRenewalDashboardView(
    LoginRequiredMixin,
    View
):

    ''' manage renewal bookings,service renewals and booking schedule updates '''

    login_url = "/login/"

    def get(self, request):

        if request.user.role not in mainly_allowed_roles:

            return HttpResponse("Not allowed")

        bookings = Booking.objects.select_related(

            "user",
            "vendor",
            "service",
            "category"

        ).order_by("-id")

        if request.user.role != "superadmin":

            bookings = bookings.filter(
                city__iexact=request.user.city
            )

        # SEARCH FILTERS

        customer = request.GET.get("customer")
        vendor = request.GET.get("vendor")
        renewal_status = request.GET.get("renewal_status")

        if customer:
            bookings = bookings.filter(user__first_name__icontains=customer)

        if vendor:
            bookings = bookings.filter(vendor__first_name__icontains=vendor)

        if renewal_status == "renewed":
            bookings = bookings.filter(is_renewed=True)

        if renewal_status == "pending":
            bookings = bookings.filter(renewal_requested=True)

        # ANALYTICS

        expiring_bookings = bookings.filter(end_date__isnull=False)
        total_renewals = bookings.filter(is_renewed=True).count()
        active_services = bookings.filter(status="accepted").count()
        completed_services = bookings.filter(status="completed").count()
        total_service_days = sum([

            booking.total_days or 0

            for booking in bookings

        ])

        # PAGINATION
        page_obj = paginate_queryset(request,bookings,10)
        context = {

            "bookings": page_obj,
            "page_obj": page_obj,
            "total_renewals": total_renewals,
            "active_services": active_services,
            "completed_services": completed_services,
            "total_service_days": total_service_days,
            "expiring_bookings": expiring_bookings,

        }

        return render(request,"admin/admin_renewal_dashboard.html",context)

    def post(self, request):

        if request.user.role not in mainly_allowed_roles:

            return HttpResponse("Not allowed")

        # SUPERADMIN CAN ACCESS ALL BOOKINGS
        # ADMIN ONLY OWN CITY

        if request.user.role == "superadmin":

            booking = get_object_or_404(

                Booking,

                id=request.POST.get("booking_id")

            )

        else:

            booking = get_object_or_404(

                Booking,

                id=request.POST.get("booking_id"),

                city__iexact=request.user.city

            )

        # FORM VALUES

        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        scheduled_date = request.POST.get("scheduled_date")
        scheduled_time = request.POST.get("scheduled_time")

        # UPDATE VALUES

        if start_date:

            booking.start_date = start_date

        if end_date:

            booking.end_date = end_date

        if scheduled_date:

            booking.scheduled_date = scheduled_date

        if scheduled_time:

            booking.scheduled_time = scheduled_time

        booking.save()

        messages.success(request,"Renewal updated successfully")

        # ROLE BASED REDIRECT

        if request.user.role == "superadmin":

            return redirect(
                "superadmin_orders"
            )

        elif request.user.role == "admin":

            return redirect(
                "admin_renewal_dashboard"
            )

        return redirect("login")
    
    

# admin can assign the lead to vendor
@method_decorator(never_cache, name='dispatch')
class AssignVendorView(LoginRequiredMixin, View):

    def post(self, request):
        try:
            if request.user.role != "admin":
                return JsonResponse({"error": "Not allowed"}, status=403)

            data = json.loads(request.body)

            booking = get_object_or_404(Booking, id=data.get("booking_id"))
            vendor = get_object_or_404(
                User, id=data.get("vendor_id"), role="vendor")

            booking.vendor = vendor
            booking.status = "assigned"
            booking.save()

            BookingHistory.objects.create(
                booking=booking,
                status="assigned",
                updated_by=request.user
            )

            return JsonResponse({
                "success": True,
                "vendor_name": vendor.first_name
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)





# status can be updates 
@method_decorator(never_cache, name='dispatch')
class UpdateStatusView(LoginRequiredMixin, View):

    def post(self, request):
        try:
            data = json.loads(request.body)

            booking = get_object_or_404(Booking, id=data.get("booking_id"))
            status = data.get("status")
            vendor_id = data.get("vendor_id")

            allowed = ["progress", "completed"]

            if status not in allowed:
                return JsonResponse({"error": "Invalid status"}, status=400)

            if vendor_id:
                vendor = User.objects.get(id=vendor_id, role="vendor")
                booking.vendor = vendor

            if not booking.vendor:
                return JsonResponse({"error": "Assign vendor first"}, status=400)

            booking.status = status
            booking.save()

            BookingHistory.objects.create(
                booking=booking,
                status=status,
                updated_by=request.user
            )

            return JsonResponse({"success": True})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)




# track the order histrotyorder history
@method_decorator(never_cache,name='dispatch')
class OrderHistoryView(LoginRequiredMixin,View):

    def get(self,request,id):

        booking = get_object_or_404(
            Booking.objects.select_related(
                "user",
                "service",
                "vendor"),id=id
        )

        all_history = booking.history.select_related(
            "updated_by"
        ).order_by(
            "created_at"
        )
        history = []
        latest_status = {}

        for h in all_history:

            latest_status[h.status] = h

        history = list(
            latest_status.values()
        )

        history.sort(
            key=lambda x: x.created_at,
            reverse=True
        )
        assigned_time = None
        accepted_time = None
        for h in history:

            h.time_taken = None
            if h.status == "assigned":
                assigned_time = h.created_at

                h.custom_message = (

                    f"Assigned by "

                    f"{h.updated_by.first_name}"

                )
                if booking.vendor:

                    h.custom_message += (
                        f" to "
                        f"{booking.vendor.first_name}"

                    )
            elif h.status == "accepted":

                accepted_time = h.created_at
                h.custom_message = (

                    f"Updated by "

                    f"{h.updated_by.first_name}"

                )

                if assigned_time:
                    diff = (

                        accepted_time
                        - assigned_time

                    )

                    mins = int(
                        diff.total_seconds() / 60

                    )

                    h.time_taken = (

                        f"Vendor accepted "
                        f"in {mins} mins"

                    )

            else:

                h.custom_message = (

                    f"Updated by "
                    f"{h.updated_by.first_name}"

                )

        payment = Payment.objects.filter(
            booking=booking
        ).first()

        total_services = 1
        total_amount = (
            payment.total_amount
            if payment else 0
        )

        paid_amount = (
            payment.paid_amount
            if payment else 0
        )

        due_amount = (
            payment.remaining_amount
            if payment else 0
        )

        context = {

            "booking": booking,
            "history": history,
            "total_services": total_services,
            "total_amount": total_amount,
            "paid_amount": paid_amount,
            "due_amount": due_amount,

        }

        return render(request,"superadmin/order_history.html",context)


# profile page page  in dropdown
@method_decorator(never_cache, name='dispatch')
class ProfileView(LoginRequiredMixin, View):

    login_url = "/login/"

    def get(self, request):

        return render(
            request,
            "profile/profile.html"
        )

    def post(self, request):

        user = request.user

        email = request.POST.get("email")
        address = request.POST.get("address")
        city = request.POST.get("city")

        # EMAIL VALIDATION

        if not email:

            messages.error(
                request,
                "Email is required"
            )

            return redirect("profile")

        # UPDATE USER

        user.email = email
        user.address = address
        user.city = city

        # PROFILE IMAGE

        if request.FILES.get("profile_image"):

            user.profile_image = request.FILES.get(
                "profile_image"
            )

        user.save()

        messages.success(
            request,
            "Profile updated successfully"
        )

        return redirect("profile")




 
# admin invoice number
@method_decorator(never_cache, name='dispatch')
class PaymentInvoiceView(View):
    def get(self, request, pk):
        payment = get_object_or_404(Payment, id=pk)
        return render(request, "service/invoice.html", {"p": payment})



# customer invoice 
@method_decorator(never_cache, name='dispatch')
class CustomerInvoiceView(LoginRequiredMixin, View):

    login_url = "/login/"

    def get(self, request, booking_id):

        booking = get_object_or_404(Booking,id=booking_id,user=request.user)
        payment = booking.payments.first()

        # payments values if not given 

        total_amount = 0
        paid_amount = 0
        remaining_amount = 0
        payment_method = "Cash"

        if payment:

            total_amount = payment.total_amount or 0

            paid_amount = payment.paid_amount or 0

            remaining_amount = (
                payment.remaining_amount or 0
            )

            payment_method = (
                payment.payment_method or "Cash"
            )
        context= {

                "booking": booking,
                "payment": payment,
                "total_amount": total_amount,
                "paid_amount": paid_amount,
                "remaining_amount": remaining_amount,
                "payment_method": payment_method,

            }
        return render(request,"customer/customer_invoice.html",context)


# vendor page show the all booking leads 
@method_decorator(never_cache, name='dispatch')
class VendorBookingDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        booking = get_object_or_404(Booking, id=pk)

        return render(request, "vendor/vendor_booking_detail.html", {
            "booking": booking
        })






@method_decorator(never_cache, name='dispatch')
class ComplaintCreateView(View):

    def get(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id)

        return render(request, "complaints/create.html", {
            "booking": booking
        })

    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id)

        #  Prevent other users accessing
        if booking.user != request.user:
            messages.error(request, "Unauthorized access!")
            return redirect("my_bookings")

        #  Prevent duplicate complaint
        if booking.remarks.exists():
            messages.error(
                request, "Complaint already raised for this booking!")
            return redirect("my_bookings")

        #  Get vendor safely
        vendor = booking.vendor

        if not vendor:
            messages.error(request, "Vendor not assigned to this booking!")
            return redirect("my_bookings")

        message = request.POST.get("message")
        priority = request.POST.get("priority", "medium")

        #  Basic validation
        if not message:
            messages.error(request, "Message is required!")
            return redirect("complaint_add", booking_id=booking.id)

        #  Create complaint
        CustomerRemark.objects.create(
            booking=booking,
            user=request.user,
            vendor=vendor,
            message=message,
            priority=priority
        )

        messages.success(request, "Complaint raised successfully!")

        return redirect("complaint_list")



@method_decorator(never_cache, name='dispatch')
class ComplaintListView(View):

    def get(self, request):

        if request.user.role in ["admin", "superadmin"]:

            complaints = CustomerRemark.objects.all().order_by("-created_at")

        else:

            complaints = CustomerRemark.objects.filter(
                user=request.user
            ).order_by("-created_at")

        return render(
            request,
            "complaints/list.html",
            {
                "complaints": complaints
            }
        )

@method_decorator(never_cache, name='dispatch')
class ComplaintDetailView(View):

    def get(self, request, pk):
        complaint = get_object_or_404(CustomerRemark, pk=pk)

        return render(request, "complaints/detail.html", {
            "complaint": complaint
        })

@method_decorator(never_cache, name='dispatch')
class ComplaintDeleteView(View):

    def post(self, request, pk):

        complaint = get_object_or_404(CustomerRemark, pk=pk)

        if request.user.is_superuser or complaint.user == request.user:
            complaint.delete()

        return redirect("complaint_list")

@method_decorator(never_cache, name='dispatch')
class ComplaintStatusAjaxUpdateView(View):

    def post(self, request, pk):

        complaint = get_object_or_404(CustomerRemark, pk=pk)

        status = request.POST.get("status")

        if status in ["open", "in_progress", "resolved"]:
            complaint.status = status

            if status == "resolved":
                complaint.resolved_by = request.user

            complaint.save()

            return JsonResponse({
                "success": True,
                "status": complaint.status,
                "updated_at": complaint.updated_at.strftime("%d-%m-%Y %H:%M")
            })

        return JsonResponse({"success": False})








# vedor can update the status view 
@method_decorator(never_cache, name='dispatch')
class VendorActionView(LoginRequiredMixin, View):

    def post(self, request):
        try:
      
            if request.user.role != "admin":
                return JsonResponse({
                    "error": "Unauthorized access"
                }, status=403)

            user_id = request.POST.get("user_id")
            action = request.POST.get("action")

            if not user_id or not action:
                return JsonResponse({
                    "error": "Missing required data"
                }, status=400)

            user = get_object_or_404(User, id=user_id, role="vendor")

            if action == "approve":
                user.is_active = True
                user.save()

                return JsonResponse({
                    "success": True,
                    "msg": "Vendor approved successfully"
                })

            elif action == "deactivate":
                user.is_active = False
                user.save()

                return JsonResponse({
                    "success": True,
                    "msg": "Vendor deactivated successfully"
                })

            elif action == "delete":
                user.delete()

                return JsonResponse({
                    "success": True,
                    "msg": "Vendor deleted successfully"
                })

            else:
                return JsonResponse({
                    "error": "Invalid action type"
                }, status=400)

        except Exception as e:
            return JsonResponse({
                "error": f"Server error: {str(e)}"
            }, status=500)


# admin can edit or change the payemnt method
@method_decorator(never_cache, name='dispatch')
class AdminBookingEditView(View):

    def get(self, request, booking_id):

        if request.user.role != "admin":
            return redirect("/")

        booking = get_object_or_404(Booking, id=booking_id)
        payment = booking.payments.first()

        return render(request, "admin/change_payment.html", {
            "booking": booking,
            "payment": payment
        })

    def post(self, request, booking_id):

        if request.user.role != "admin":
            return redirect("/")

        booking = get_object_or_404(Booking, id=booking_id)
        payment = booking.payments.first()

       
        booking.service_days = request.POST.get("service_days")
        booking.expiry_date = request.POST.get("expiry_date")
        booking.save()

      
        if payment:
            payment.total_amount = request.POST.get("total_amount")
            payment.paid_amount = request.POST.get("paid_amount")
            payment.status = request.POST.get("status")
            payment.save()

        messages.success(request, "Updated successfully")

        return redirect("admin_booking_edit", booking_id=booking.id)
    

# ok
# if the servcie time end show the nerew button 
@method_decorator(never_cache, name='dispatch')
def renew_service(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)

    booking.expiry_date = booking.expiry_date + timedelta(days=30)
    booking.save()

    messages.success(request, "Service renewed successfully")

    return redirect("my_orders")   



# admin create vendor


class CreateVendorView(LoginRequiredMixin, View):

    def get(self, request):

        category_id = request.GET.get("category")

        vendors = User.objects.filter(role="vendor")\
            .select_related("vendor_profile")\
            .order_by("-id")

        categories = Category.objects.all()

        services = CategoryService.objects.all()

        if category_id:
            services = services.filter(category_id=category_id)

        return render(request, "admin/create_vendor.html", {
            "vendors": vendors,
            "categories": categories,
            "services": services,
            "selected_category": category_id
        })

    def post(self, request):
        try:
            if request.user.role != "admin":
                return JsonResponse({"error": "Unauthorized"}, status=403)

            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            email = request.POST.get("email")
            phone = request.POST.get("phone")
            experience = request.POST.get("experience")
            locality = request.POST.get("locality")
            street = request.POST.get("street")
            city = request.POST.get("city")
            pincode = request.POST.get("pincode")
            category_id = request.POST.get("category")
            service_id = request.POST.get("service")
            company_name = request.POST.get("company_name")
            company_address = request.POST.get("company_address")

            if not first_name or not email or not phone:
                return JsonResponse({"error": "Basic fields required"}, status=400)

            if not email.endswith("@gmail.com"):
                return JsonResponse({"error": "Enter valid Gmail"}, status=400)

            if not phone.isdigit() or len(phone) != 10:
                return JsonResponse({"error": "Invalid phone number"}, status=400)

            if User.objects.filter(email=email).exists():
                return JsonResponse({"error": "Email already exists"}, status=400)

            if User.objects.filter(phone=phone).exists():
                return JsonResponse({"error": "Phone already exists"}, status=400)

            if not request.session.get("otp_verified"):
                return JsonResponse({"error": "Verify OTP first"}, status=400)

            if not city or not locality or not pincode:
                return JsonResponse({"error": "Location required"}, status=400)

            if not category_id:
                return JsonResponse({"error": "Select category"}, status=400)

            if not service_id:
                return JsonResponse({"error": "Select service"}, status=400)

            service_exists = CategoryService.objects.filter(
                id=service_id,
                category_id=category_id
            ).exists()

            if not service_exists:
                return JsonResponse({
                    "error": "Selected service does not belong to this category"
                }, status=400)

            user = User.objects.create(
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone=phone,
                role="vendor",
                created_by=request.user
            )

            user.set_unusable_password()
            user.save()

            VendorProfile.objects.create(
                user=user,
                experience=experience or 0,
                locality=locality,
                street=street,
                city=city,
                postal_code=pincode,
                category_id=category_id,
                service_id=service_id,
                company_name=company_name,
                company_address=company_address
            )

            request.session.pop("otp_verified", None)
            request.session.pop("phone", None)

            return JsonResponse({
                "status": "success",
                "message": "Vendor created successfully"
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


def get_services(request):

    category_id = request.GET.get("category_id")

    if not category_id:
        return JsonResponse({
            "services": []
        })

    services = CategoryService.objects.filter(
        category_id=category_id
    )

    data = []

    for s in services:

        data.append({
            "id": s.id,
            "name": s.s_title
        })

    return JsonResponse({
        "services": data
    })






from .utils import (
    send_otp,
    verify_otp,
    can_resend
)


def send_otp_view(request):
    if request.method == "POST":
        phone = request.POST.get("phone")
        phone = normalize_phone(phone)
        if not phone:
            return JsonResponse({"error": "Phone required"})
        
        if not can_resend(phone):
            return JsonResponse({"error": "Please wait before resend"})
            
        send_otp(phone, purpose="register")
        
        return JsonResponse({"status": "sent"})
        
    return JsonResponse({"error": "Invalid request"})

def verify_otp_view(request):
    if request.method == "POST":
        # In vendor registration, the frontend doesn't send phone number to verify-otp 
        # so we fetch it from the latest OTP or session, but let's see. 
        # Wait, create_vendor.html only sends OTP. We need to pass phone from frontend or session.
        # But if admin is creating vendor, they enter phone in form. So the frontend SHOULD send phone.
        # I'll update frontend to send phone.
        phone = request.POST.get("phone")
        if not phone:
            return JsonResponse({"error": "Phone required for verification"})
            
        phone = normalize_phone(phone)
        otp = request.POST.get("otp")
        
        if verify_otp(phone, otp):
            request.session["verified_phone"] = phone
            return JsonResponse({"status": "verified"})
            
        return JsonResponse({"error": "Invalid OTP"})
        
    return JsonResponse({"error": "Invalid request"})
    
    
    
    
@method_decorator(never_cache, name='dispatch')

class CustomerTermsView(LoginRequiredMixin, View):

    template_name = "customer/terms_form.html"

    def get(self, request):

        if request.user.role != "customer":

            return redirect("dashboard")

        booking = Booking.objects.filter(
            user=request.user
        ).last()

        already_accepted = TermsAcceptance.objects.filter(
            customer=request.user
        ).first()

        return render(
            request,
            self.template_name,
            {
                "booking": booking,
                "already_accepted": already_accepted
            }
        )

    def post(self, request):

        if request.user.role != "customer":

            return redirect("dashboard")

        booking = Booking.objects.filter(
            user=request.user
        ).last()

        accepted = request.POST.get("accepted")

        signature = request.FILES.get("signature")

        if not accepted:

            return render(
                request,
                self.template_name,
                {
                    "error": "Please accept terms and conditions.",
                    "booking": booking
                }
            )

        if not signature:

            return render(
                request,
                self.template_name,
                {
                    "error": "Please upload signature.",
                    "booking": booking
                }
            )

        already_exists = TermsAcceptance.objects.filter(
            customer=request.user
        ).exists()

        if already_exists:

            return render(
                request,
                self.template_name,
                {
                    "error": "You already accepted terms and conditions.",
                    "booking": booking,
                    "already_accepted": already_exists
                }
            )

        TermsAcceptance.objects.create(

            customer=request.user,

            booking=booking,

            signature=signature,

            accepted=True

        )

        return redirect("customer_terms")

# terms and conditions accept data.
@method_decorator(never_cache, name='dispatch')
class TermsListView(LoginRequiredMixin, View):

    template_name = "superadmin/terms_list.html"

    def get(self, request):

        if request.user.role != "superadmin":

            return redirect("dashboard")

        forms = TermsAcceptance.objects.select_related(
            "booking",
            "booking__user",
            "booking__service"
        ).order_by("-id")

        return render(
            request,
            self.template_name,
            {
                "forms": forms
            }
        )


@method_decorator(never_cache, name='dispatch')
class TermsDetailView(LoginRequiredMixin, View):

    template_name = "superadmin/terms_details.html"

    def get(self, request, pk):

        if request.user.role != "superadmin":

            return redirect("dashboard")

        form_data = get_object_or_404(
            TermsAcceptance.objects.select_related(
                "customer",
                "booking"
            ),
            id=pk
        )

        return render(
            request,
            self.template_name,
            {
                "form_data": form_data
            }
        )
        
        
        


# CUSTOMER TERMS

class CustomerRegisterTermsView(View):

    template_name = "terms/customer_terms.html"

    def get(self, request):
        return render(request,self.template_name)


# CUSTOMER PRIVACY

class CustomerPrivacyView(View):

    template_name = "terms/customer_privacy.html"

    def get(self, request):
        return render(request,self.template_name)


# VENDOR TERMS

class VendorTermsView(View):

    template_name = "terms/vendor_terms.html"

    def get(self, request):
        return render(request,self.template_name)


# VENDOR PRIVACY

class VendorPrivacyView(View):
    template_name = "terms/vendor_privacy.html"

    def get(self, request):
        return render(request,self.template_name)

# login page terms
class LoginTermView(View):
    template_name = "terms/login_term.html"
    
    def get(self, request):
        return render(request,self.template_name)
    
    



from .models import Visitor

 
@method_decorator(never_cache, name="dispatch")
class VisitorListView(LoginRequiredMixin, View):
    """
    Superadmin only — list all non-logged-in visitors.
    Supports search + bulk delete.
    """
 
    login_url = "/login/"
 
    def dispatch(self, request, *args, **kwargs):
        if request.user.role != "superadmin":
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)
 
    def get(self, request):
 
        visitors = Visitor.objects.all().order_by("-visited_at")
 
        # ── Search ────────────────────────────────────────────────
        search = request.GET.get("search", "").strip()
        if search:
            visitors = visitors.filter(
                Q(ip_address__icontains=search) |
                Q(country__icontains=search)    |
                Q(state__icontains=search)      |
                Q(city__icontains=search)        |
                Q(browser__icontains=search)    |
                Q(device__icontains=search)     |
                Q(operating_system__icontains=search) |
                Q(page_url__icontains=search)
            )
 
        total_count   = Visitor.objects.count()
        mobile_count  = Visitor.objects.filter(device="Mobile").count()
        desktop_count = Visitor.objects.filter(device="Desktop").count()
        tablet_count  = Visitor.objects.filter(device="Tablet").count()
 
        page_obj = paginate_queryset(request, visitors, 15)
 
        context = {
            "visitors":     page_obj,
            "page_obj":     page_obj,
            "search":       search,
            "total_count":  total_count,
            "mobile_count": mobile_count,
            "desktop_count":desktop_count,
            "tablet_count": tablet_count,
        }
 
        return render(request, "superadmin/visitors.html", context)
 
    def post(self, request):
        """Bulk delete selected visitors OR delete all."""
 
        if request.user.role != "superadmin":
            return JsonResponse({"success": False, "message": "Permission Denied"}, status=403)
 
        import json
        try:
            data       = json.loads(request.body)
            action     = data.get("action")        # "delete_selected" | "delete_all"
            visitor_ids = data.get("ids", [])
 
            if action == "delete_all":
                count = Visitor.objects.all().delete()[0]
                return JsonResponse({
                    "success": True,
                    "message": f"All {count} visitor records deleted.",
                })
 
            elif action == "delete_selected":
                if not visitor_ids:
                    return JsonResponse({"success": False, "message": "No visitors selected."})
 
                count = Visitor.objects.filter(id__in=visitor_ids).delete()[0]
                return JsonResponse({
                    "success": True,
                    "message": f"{count} visitor(s) deleted.",
                })
 
            return JsonResponse({"success": False, "message": "Invalid action."}, status=400)
 
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)
        

# ─────────────────────────────────────────────────────────────────
# ASSIGN LEADS VIEW
# ─────────────────────────────────────────────────────────────────


@method_decorator(never_cache, name="dispatch")
class SuperAdminAssignLeadView(LoginRequiredMixin, View):

    login_url = "/login/"

    def get(self, request):

        if request.user.role != "superadmin":
            return HttpResponse("Permission Denied")

        bookings = (
            Booking.objects.select_related(
                "user", "vendor", "category", "service",
            )
            .prefetch_related("payments")
            .order_by("-booking_created_at")
        )

  
        status   = request.GET.get("status")
        city     = request.GET.get("city")
        category = request.GET.get("category")
        service  = request.GET.get("service")
        search   = request.GET.get("search")

      
        if status:
            bookings = bookings.filter(status=status)

        if city:
            bookings = bookings.filter(city=city)

        if category:
            bookings = bookings.filter(category_id=category)

        if service:
            bookings = bookings.filter(service_id=service)

        if search:
            bookings = bookings.filter(
                Q(order_id__icontains=search)         |
                Q(user__first_name__icontains=search) |
                Q(phone__icontains=search)
            )

       
        total_count     = bookings.count()
        pending_count   = bookings.filter(status="pending").count()
        assigned_count  = bookings.filter(status="assigned").count()
        completed_count = bookings.filter(status="completed").count()
        cancelled_count = bookings.filter(status="cancelled").count()

       
        page_obj = paginate_queryset(request, bookings, 10)

   
        if category:
            services = CategoryService.objects.filter(category_id=category)
        else:
            services = CategoryService.objects.all()

    
        vendors = User.objects.filter(
            role="vendor",
            vendor_profile__isnull=False,
        ).select_related("vendor_profile")

        if city:
            vendors = vendors.filter(vendor_profile__city=city)

        if category:
            vendors = vendors.filter(vendor_profile__category_id=category)

        if service:
            vendors = vendors.filter(vendor_profile__services__id=service)

        vendors = vendors.distinct().order_by("first_name")

     
        context = {
            "bookings":  page_obj,
            "page_obj":  page_obj,

      
            "total_count":     total_count,
            "pending_count":   pending_count,
            "assigned_count":  assigned_count,
            "completed_count": completed_count,
            "cancelled_count": cancelled_count,

     
            "cities": VendorProfile.objects.exclude(
                city__isnull=True
            ).exclude(
                city=""
            ).values_list("city", flat=True).distinct(),

            "categories": Category.objects.all(),
            "services":   services,   
            "vendors":    vendors,    

        
            "selected_status":   status   or "",
            "selected_city":     city     or "",
            "selected_category": category or "",
            "selected_service":  service  or "",
            "selected_search":   search   or "",
        }

        return render(request, "superadmin/assign_lead.html", context)

    def post(self, request):
        """Assign vendor via JSON POST."""

        if request.user.role != "superadmin":
            return JsonResponse({"success": False, "message": "Permission Denied"})

        try:
            data    = json.loads(request.body)
            booking = get_object_or_404(Booking, id=data.get("booking_id"))
            vendor  = get_object_or_404(User, id=data.get("vendor_id"), role="vendor")

            booking.vendor = vendor
            booking.status = "assigned"
            booking.save()

            BookingHistory.objects.create(
                booking=booking,
                status="Vendor Assigned",
                updated_by=request.user,
            )

            return JsonResponse({"success": True, "message": "Vendor Assigned Successfully"})

        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})




@method_decorator(never_cache, name="dispatch")
class VendorFilterView(LoginRequiredMixin, View):

    login_url = "/login/"

    def get(self, request):

        city     = request.GET.get("city")
        category = request.GET.get("category")
        service  = request.GET.get("service")

        vendors = User.objects.filter(
            role="vendor",
            vendor_profile__isnull=False,  
        ).select_related("vendor_profile")

     
        if city:
            vendors = vendors.filter(vendor_profile__city=city)

     
        if category:
            vendors = vendors.filter(vendor_profile__category_id=category)

   
        if service:
            vendors = vendors.filter(vendor_profile__services__id=service)

        vendors = vendors.distinct().order_by("first_name")

        data = [
            {
                "id":    v.id,
                "name":  v.first_name,
            
                "city":  v.vendor_profile.city if hasattr(v, "vendor_profile") else "",
                "phone": v.phone or "",
            }
            for v in vendors
        ]

        return JsonResponse(data, safe=False)




@method_decorator(never_cache, name="dispatch")
class ServiceFilterView(LoginRequiredMixin, View):


    login_url = "/login/"

    def get(self, request):

        category = request.GET.get("category")

        if category:
            services = CategoryService.objects.filter(category_id=category)
        else:
            services = CategoryService.objects.all()

        data = [
            {"id": s.id, "name": s.s_title}
            for s in services
        ]

        return JsonResponse(data, safe=False)


# ─────────────────────────────────────────────────────────────────
# ASSIGN VENDOR VIEW  (form POST — assign button in table)
# ─────────────────────────────────────────────────────────────────

class AssignVendorView(LoginRequiredMixin, View):

    login_url = "/login/"

    def post(self, request):

        booking = get_object_or_404(
            Booking,
            id=request.POST.get("booking_id"),
        )

        vendor = get_object_or_404(
            User,
            id=request.POST.get("vendor_id"),
            role="vendor",
        )

        booking.vendor = vendor
        booking.status = "assigned"
        booking.save()

        BookingHistory.objects.create(
            booking=booking,
            status="Vendor Assigned",
            updated_by=request.user,
        )

        return redirect("assign_leads")


# ─────────────────────────────────────────────────────────────────
# DELETE LEAD VIEW  (AJAX POST)
# ─────────────────────────────────────────────────────────────────

@method_decorator(never_cache, name="dispatch")
class DeleteLeadView(LoginRequiredMixin, View):

    login_url = "/login/"

    def post(self, request, booking_id):

        if request.user.role != "superadmin":
            return JsonResponse({
                "success": False,
                "message": "Permission Denied",
            }, status=403)

        try:
            booking = get_object_or_404(Booking, id=booking_id)
            booking.delete()

            return JsonResponse({
                "success": True,
                "message": "Lead deleted successfully",
            })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": str(e),
            }, status=500)


# ─────────────────────────────────────────────────────────────────
# EDIT LEAD VENDOR VIEW  (AJAX POST — change vendor)
# ─────────────────────────────────────────────────────────────────

@method_decorator(never_cache, name="dispatch")
class EditLeadVendorView(LoginRequiredMixin, View):

    login_url = "/login/"

    def post(self, request):

        if request.user.role != "superadmin":
            return JsonResponse({
                "success": False,
                "message": "Permission Denied",
            })

        try:
            data = json.loads(request.body)

            booking = get_object_or_404(
                Booking,
                id=data.get("booking_id"),
            )

            vendor = get_object_or_404(
                User,
                id=data.get("vendor_id"),
                role="vendor",
            )

            booking.vendor = vendor
            booking.status = "assigned"
            booking.save()

            BookingHistory.objects.create(
                booking=booking,
                status="Vendor Reassigned",
                updated_by=request.user,
            )

            return JsonResponse({
                "success": True,
                "message": "Vendor updated successfully",
            })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": str(e),
            })