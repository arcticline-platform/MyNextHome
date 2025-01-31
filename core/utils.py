# import requests

from django.core.mail import send_mail

import africastalking
from twilio.rest import Client

from django.conf import settings
from .models import Action, ErrorLogs #,SystemUtility

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
channel_layer = get_channel_layer()


def send_sms_alert(body, phone_number):
	username = settings.AFRICAS_TALKING_USERNAME
	api_key = settings.AFRICAS_TALKING_APIKEY
	africastalking.initialize(username, api_key)
	# Initialize a service e.g. SMS
	sms = africastalking.SMS
	message = body
	recipients = [f'{phone_number}'] #pass number as string
	sender = settings.AFRICAS_TALKING_SENDER_ID
	try:
		response = sms.send(message, recipients)
		print(response)
		return response
	except Exception as e:
		if ErrorLogs.objects.exists():
			ErrorLogs.objects.create(error_narration=f"Error encountered during sms send with Africa's Talking: {e}")


def send_email_alert(email, subject, message):
	send_mail(subject, message, settings.ROOT_EMAIL, [email])


def create_action(user, verb, target=None):
	action = Action.objects.create(user=user, verb=verb, target=target)
	async_to_sync(channel_layer.group_send)(
		f'notification_inbox_{user.username}',
		{
			"type": "send_notification",
			"message": "You have a new connection and successful match"
		}
	)
	action.save()


def info_message(user, verb, target=None):
	message = Action.objects.create(user=user, verb=verb, target=target)
	message.save()
	