import random
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

from .models import OTP


OTP_EXPIRE = 120
RESEND_TIME = 30


def generate_otp():
    return str(random.randint(1000, 9999))


def send_otp(phone, purpose):

    otp = generate_otp()
    
    print(f"\n[{purpose.upper()}] OTP for {phone}: {otp}\n")

    # Delete old OTPs
    OTP.objects.filter(phone=phone).delete()

    # Save new OTP
    OTP.objects.create(
        phone=phone,
        otp=otp
    )

    templates = {
        "login": {
            "template_id": settings.SMS_LOGIN_TEMPLATE_ID,
            "message": (
                f"Dear User, your secure login OTP for Sridixitha Enterprises is { otp }. This code is required to complete your sign-in process. If you did not request this login, please ignore this message immediately."
            )
        },
        "register": {
            "template_id": settings.SMS_REGISTER_TEMPLATE_ID,
            "message": (
                f"Thank you for registering your account with Sridixitha Enterprises. Your verification code is { otp }. Please enter the OTP to complete your registration."
            )
        }
    }

    config = templates[purpose]

    payload = {
        "username": settings.SMS_USERNAME,
        "apikey": settings.SMS_APIKEY,
        "senderid": settings.SMS_SENDER_ID,
        "mobile": phone,
        "message": config["message"],
        "templateid": config["template_id"],
    }

    response = requests.get(
        "https://smslogin.co/v3/api.php",
        params=payload,
        timeout=10
    )

    print("Generated OTP:", otp)
    # print("Status Code:", response.status_code)
    # print("Response:", response.text)

    return True




def verify_otp(phone, otp):

    otp_obj = OTP.objects.filter(
        phone=phone,
        otp=str(otp)
    ).first()

    if not otp_obj:
        return False

    if timezone.now() - otp_obj.created_at > timedelta(seconds=OTP_EXPIRE):
        otp_obj.delete()
        return False

    otp_obj.delete()

    return True



def can_resend(phone):

    otp_obj = OTP.objects.filter(
        phone=phone
    ).order_by("-created_at").first()

    if not otp_obj:
        return True

    elapsed_time = timezone.now() - otp_obj.created_at

    return elapsed_time > timedelta(seconds=RESEND_TIME)





from django.core.paginator import Paginator

def paginate_queryset(request, queryset, per_page=10):

    paginator = Paginator(
        queryset,
        per_page
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(
        page_number
    )

    return page_obj





# notifications code 
from .models import Notification

def create_notification(

    user,
    title,
    message,
    booking=None,
    payment=None

):

    Notification.objects.create(

        user=user,

        booking=booking,

        payment=payment,

        title=title,

        message=message

    )
    
    


# permisions
from django.shortcuts import redirect
from django.contrib import messages

def permission_required(permission):

    def decorator(view_func):

        def wrapper(
            request,
            *args,
            **kwargs
        ):

            if not request.user.has_perm(
                permission
            ):

                messages.error(
                    request,
                    "Permission Denied"
                )

                return redirect(
                    "admin_dashboard"
                )

            return view_func(
                request,
                *args,
                **kwargs
            )

        return wrapper

    return decorator