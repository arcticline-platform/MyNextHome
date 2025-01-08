from django import forms
from core.utils import send_email_alert
# from . import errors

from django.utils import timezone
from .models import Payments, Tip

class DepositForm(forms.Form):
    amount = forms.IntegerField(
        min_value=5000,
        max_value=500000,
        required=True,
    )

class TipForm(forms.ModelForm):

    class Meta:
        model = Tip
        fields = ('amount', 'narrative', 'is_held')
        widgets = {
            'amount': forms.NumberInput(attrs={'placeholder': 'Enter amount in USD'}),
			'narrative': forms.Textarea(attrs={'placeholder': 'Add a message with the tip'}),
            'is_held': forms.CheckboxInput(attrs={'help_text': 'Hold amount and release to receipient later'}) 
		}


	