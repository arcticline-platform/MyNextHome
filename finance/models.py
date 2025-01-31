# import uuid
import logging
# import requests

from datetime import timedelta

# from django.conf import settings
from django.utils import timezone
from django.utils.timezone import now
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from phonenumber_field.modelfields import PhoneNumberField

# from core.utils import send_email_alert
from accounts.models import User, UserProfile
# from core.tasks import send_email_task, send_sms_alert_task


logger = logging.getLogger(__name__)

class BillingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name=_('billing_address_user'))
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    street = models.CharField(max_length=20)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Billing Address'
        verbose_name_plural = "Billing Addresses"


class PaymentMethods(models.Model):
    name = models.CharField(max_length=75)
    image = models.ImageField(upload_to='Core/PaymentMethod_Images/', null=True, blank=True)
    phone_number = PhoneNumberField(null=True, blank=True)
    unique_id = models.CharField(max_length=13, null=True, blank=True)
    key = models.CharField(max_length=17, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment Method'
        verbose_name_plural = "Payment Methods"

    def __str__(self):
        return self.name


class Payments(models.Model):
    method = models.ForeignKey(PaymentMethods, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    phone = models.CharField(max_length=13)
    note = models.CharField(max_length=150)
    payment_id = models.BigIntegerField(default=100000000)
    transaction_id = models.BigIntegerField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    is_successful = models.BooleanField(default=False)
    declined = models.BooleanField(default=False)
    error = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    receivers_phone = models.CharField(max_length=13)
    initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='initiation_user')
    cleared_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='clearance_user')

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = "Payments"

    def __str__(self):
        return str(f'Payment Initiation of {self.amount}')

    def save(self, *args, **kwargs):
        with transaction.atomic():
            # Handle payment ID increment for new records
            if self._state.adding:
                last_payment = Payments.objects.order_by('-payment_id').first()
                self.payment_id = last_payment.payment_id + 1 if last_payment else 100000000

            # Prevent task re-enqueueing if already being processed
            if not self.is_processed:
                self.is_processed = True  # Mark as processing before saving
                super().save(*args, **kwargs)  # Save the initial record
                from .tasks import process_and_update_payment
                # process_and_update_payment.delay(self.id)  # Enqueue Celery task
                process_and_update_payment.apply_async(
                    args=[self.id],  # Task arguments
                    #queue='payments',  # Optional: specify the queue
                    countdown=1  # Optional: delay execution by 5 seconds
                )
            else:
                super().save(*args, **kwargs)  # Save without triggering the task


class Remittance(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name=_('remittance_user'))
    unique_number = models.PositiveIntegerField(null=True, blank=True)
    phone = PhoneNumberField(null=True, blank=True)
    amount = models.DecimalField(decimal_places=2, max_digits=9)
    reason = models.CharField(max_length=255)
    is_valid = models.BooleanField(default=False)
    is_successful = models.BooleanField(default=False)
    is_cancelled = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Remittance'
        verbose_name_plural = "Remittances"

    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Check if this is a new instance
        super(Remittance, self).save(*args, **kwargs)  # Save instance first
        # Schedule the task for 24 hours later
        from .tasks import process_remittance
        if is_new and not self.is_processed:
            process_remittance.apply_async((self.id,), eta=now() + timedelta(hours=24))


class UserWallet(models.Model):
    owner = models.OneToOneField(UserProfile, on_delete=models.CASCADE, related_name='user_wallet')
    amount = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    is_active = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.owner.username}'s Wallet"



class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration_days = models.IntegerField(default=30)

    def get_success_url(self):
        return f'/subscribe/success/{self.id}'

    def get_cancel_url(self):
        return f'/subscribe/cancel/{self.id}'
    
    def __str__(self) -> str:
        return str(self.name)
    

class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    def is_expired(self):
        return not self.is_active or self.end_date < timezone.now()

    def activate_subscription(self):
        self.end_date = timezone.now() + timedelta(days=self.plan.duration_days)
        self.is_active = True
        self.save()

    def deactivate_subscription(self):
        self.is_active = False
        self.save()

    
    def __str__(self) -> str:
        return str(self.user)