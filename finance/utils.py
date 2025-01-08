import logging
import requests

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

from django.conf import settings


def send_payment_request(phone, amount):
    api_key = settings.DARAZA_API_KEY
    # print(api_key)
    def format_phone_number(phone):
        """Ensure the phone number is in +256XXXXXXXXX format."""
        if not phone.startswith("+256"):
            phone = "+256" + phone[-9:]  # Add country code and extract last 9 digits
        return phone

    formatted_phone = format_phone_number(phone)
    # print(phone)
    url = "https://daraza.net/api/request_to_pay/"
    headers = {"Authorization": f"Api-Key {api_key}", "Content-Type": "application/json"}
    data = {
        "method": 1,
        "amount": str(amount),
        "phone": formatted_phone, 
        "note": "Checkout"
        }


    try:
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()
        
        if response_data.get('code') == 'Error':
            error_message = response_data.get('message', 'Payment processing failed')
            details = response_data.get('details', '')
            
            if 'Internal Service Error' in details:
                return {
                    "status": "error",
                    "message": "Our payment system is experiencing technical difficulties. Please try again later."
                }
            elif 'Insufficient Balance' in details:
                return {
                    "status": "error",
                    "message": "Sorry, you have insufficient balance to complete this transaction."
                }
            else:
                logger.error(f"Payment failed: {details}")
                return {
                    "status": "error",
                    "message": f"Payment failed: {details}"
                }
        elif response_data.get('code') == 'Success':
            # Successful payment scenario
            return {
                "status": "success",
                "message": f"Payment of {amount} UGX successfully processed."
            }
        else:
            logger.error(f"Response Error: Unknown Response Received")
            return {"status": "error", "message": f"Response Error"}
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Unable to process payment: {e}")
        return {
            "status": "error",
            "message": "Unable to process payment. Please check your connection."
        }
    

def update_payment_status(payment_id, status, declined, error):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"payment_{payment_id}",
        {
            "type": "payment_status_update",
            "data": {
                "status": status,
                "declined": declined,
                "error": error
            },
        },
    )