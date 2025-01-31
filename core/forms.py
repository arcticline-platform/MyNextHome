from django import forms
# from django.db import transaction
# from django.utils.text import slugify
from django.forms.utils import ErrorList
# from django.core.validators import MaxValueValidator, MinValueValidator

from .models import Contact, FAQ, NewsLetter, SystemUtility, SMS_Broadcast, User_Inquiry


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ('email', 'subject', 'message')


class UserInquiryForm(forms.ModelForm):
    message = forms.CharField(widget=forms.Textarea(attrs={'name':'Inquiry', 'rows':3, 'cols':5, 'placeholder': 'Describe to us the problem'}), label='Write your inquiry')
    class Meta:
        model = User_Inquiry
        fields = ('subject', 'message')
        widgets = {
            'subject': forms.TextInput(attrs={'placeholder': 'Tell us what the problem is'}),
        }


class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ('question',)
        widgets = {
            'question': forms.TextInput(attrs={'placeholder': 'Ask your Question'}),
        }


class SystemUtilityModelForm(forms.ModelForm):
    def clean(self):
        if SystemUtility.objects.count() >= 1:
            self._errors.setdefault('__all__', ErrorList()).append("You can only create one Utility object!")
        return self.cleaned_data
    

class NewsLetterForm(forms.ModelForm):
    class Meta:
        model = NewsLetter
        fields = ( 'receivers', 'subject', 'message')


class BroadcastForm(forms.ModelForm):
    class Meta:
        model = SMS_Broadcast
        fields = ( 'receivers', 'message')