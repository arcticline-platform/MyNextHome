from django import forms
# from core.utils import send_email_alert
# from . import errors

# from django.utils import timezone
# from .models import Payments

class DepositForm(forms.Form):
    amount = forms.IntegerField(
        min_value=5000,
        max_value=500000,
        required=True,
    )



	