import json
import random
import string
import datetime
from datetime import timedelta
from django.conf import settings
from django.http import JsonResponse
from django.utils.timezone import now
from django.core.mail import send_mail

from .models import OTPVerification
from django.shortcuts import render, redirect

from core.utils import send_sms_alert, send_email_alert
from .forms import EmailVerificationForm, PhoneVerificationForm


def generate_otp():
    return ''.join(random.choices(string.digits, k=6))


def send_otp(request):
    if request.method == "POST":
        data = json.loads(request.body.decode('utf-8'))
        contact_type = data.get("type")
        contact_value = data.get("input_value")
        if contact_type == "id_email":
            otp = generate_otp()
            OTPVerification.objects.create(email=contact_value, otp=otp, expires_at=now() + timedelta(minutes=10))
            subject="Your Verification Code"
            message=f"Your OTP is {otp}. It expires in 10 minutes."
            email = contact_value
            send_email_alert(email, subject, message)
            print(otp)
            return JsonResponse({"message": "OTP sent to your email", "status": "success"})
        
        elif contact_type == "id_phone":
            otp = generate_otp()
            OTPVerification.objects.create(phone=contact_value, otp=otp, expires_at=now() + timedelta(minutes=10))
            # Send OTP via SMS
            print(otp)
            body=f'Your OTP code is {otp}. It will expire in 10 minutes.',
            send_sms_alert(body=body, phone_number=contact_value)
            return JsonResponse({"message": "OTP sent to your phone", "status": "success"})
        
        return JsonResponse({"message": "Invalid contact type", "status": "error"})

    return JsonResponse({"message": "Invalid request", "status": "error"})


def verify_otp(request):
    if request.method == "POST":
        data = json.loads(request.body.decode('utf-8'))
        contact_type = data.get("type")  # "email" or "phone"
        contact_value = data.get("value")
        otp = data.get("otp")
        verification = OTPVerification.objects.filter(
            email=contact_value if contact_type == "id_email" else None,
            phone=contact_value if contact_type == "id_phone" else None,
            otp=otp,
            expires_at__gt=now(),
        ).first()

        if verification:
            verification.verified = True
            verification.save()
            return JsonResponse({"message": "Verification successful", "status": "success"})
        else:
            return JsonResponse({"message": "Invalid or expired OTP", "status": "error"})

    return JsonResponse({"message": "Invalid request", "status": "error"})