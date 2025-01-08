from time import sleep
from django.utils import timezone
from django.core.mail import send_mail
from celery import shared_task



def import_django_instance():
	"""
	Makes django environment available 
	to tasks!!
	"""
	import django
	import os
	os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Flirt.settings')
	django.setup()
	

@shared_task()
def create_profile(user):
	from accounts.models import User, UserProfile
	UserProfile.objects.create(user=user, username=user.username, first_name=user.username, last_name="New User", email=user.email)

@shared_task()
def send_sms_alert_task(body, sms_phone):
	from .utils import send_sms_alert
	send_sms_alert(body, sms_phone)
	# print('SMS send receipt', body, sms_phone)
	

@shared_task()
def send_email_task(email, subject, message):
	from .utils import send_email_alert
	send_email_alert(email, subject, message)


# Finance App
@shared_task()
def resend_payment_alert_sms(id):
	from finance.models import Payments
	from .utils import send_sms_alert
	from .models import InfoUtility, ErrorLogs
	try:
		payment = Payments.objects.get(id=id)
	except:
		payment = None
	if payment is not None:
		# print(payment)
		sleep(210)
		if payment.is_complete == False:
			try:
				systemUtility = InfoUtility.objects.get(id=1)
				body = f"About to Timeout!\nPlease initiate transaction of UGX {payment.amount} on the number {payment.phone}\nPayment ID: {payment.payment_id}"
				sms_phone = str(systemUtility.transaction_phone)
				send_sms_alert(body, sms_phone)
			except:
				if ErrorLogs.objects.exists():
					ErrorLogs.objects.create(error_narration=f"An error occurred during 'Resend Payment Alert'")
