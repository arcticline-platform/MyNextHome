import re
from celery import shared_task

from core.utils import send_email_alert
from .models import Payments, Ledger, Remittance
from .utils import send_payment_request, update_payment_status

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
def process_and_update_payment(payment_id):
    try:
        payment = Payments.objects.get(id=payment_id)
        # Execute the send_payment_request
        response = send_payment_request(payment.phone, payment.amount)
        # Update the payment record based on the response
        if response['status'] == 'success':
            payment.is_successful = True
            payment.note = response['message']
            Ledger.objects.create(
                user_from=payment.initiated_by,
                user_to=payment.cleared_by,
                is_credit=True,
                amount=payment.amount,
                is_valid=True,
                is_active=True,
                notes='Inbound User Payment'
            )
            Remittance.objects.create(
                user=payment.initiated_by,
                unique_number=payment_id,
                phone=payment.receivers_phone,
                amount=payment.amount,
                reason=f"Payment cleared for {payment.note}",
                is_valid=True,
            )
        elif response['status'] == 'error':
            message = response['message']
            if re.search("insufficient balance", message):
                payment.is_successful = False
                payment.declined = True
                payment.error = False
            else:
                payment.error = True
                payment.declined = False
                payment.is_successful = False
            payment.note = response['message'] 
        payment.save()  # Save the updates safely
        # Notify the WebSocket group
        update_payment_status(payment.id, payment.is_successful, payment.declined, payment.error)
    except Payments.DoesNotExist:
        # Log the error or handle it gracefully
        pass
    except Exception as e:
         print("Error: ", e)


@shared_task
def process_remittance(remittance_id):
    try:
        remittance = Remittance.objects.get(id=remittance_id)
        if remittance.phone is None:
            subject = f'Unsuccessful Remittance for Order {remittance.unique_number}'
            message = (f"Dear User, a Remittance of UGX {remittance.amount} in amount for your order '{remittance.unique_number}' could not be processed.\n"
                       f"Reason:\n Incomplete user profile or missing details.\n"
                       "Please provide the necessary details to rectify this problem. "
                       "Call or email user support at paylink@daraza.net for further help\n\n PayLink")
            send_email_alert(remittance.user.email, subject, message)
        elif remittance.is_successful:
            create_ledger = Ledger.objects.create(
                user_to=remittance.user, amount=remittance.amount,
                is_valid=True, is_active=True, is_debit=True,
                notes=f'Remittance'
            )
            remittance.ledger = create_ledger
            # Mark as processed
            remittance.is_processed = True
            remittance.save(update_fields=["is_processed"])

            subject = f'Remittance for Order {remittance.unique_number} has been made!'
            message = (f"Dear User, a Remittance of UGX {remittance.amount} in amount for your order '{remittance.unique_number}' "
                       f"has been made to your phone {remittance.phone}.\nRemittance Reason:\n'{remittance.reason}'\n\n"
                       "If there was an error in this process, please write to our customer support immediately through "
                       "paylink@daraza.net within the next 5 days.\nThank You \n\n PayLink")
            send_email_alert(remittance.user.email, subject, message)
    except Remittance.DoesNotExist:
        pass