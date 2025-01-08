import time
import json
import requests
from datetime import datetime
from rest_framework import status
from django.conf import settings


class AirtelMoney:
    def baseUrl(self):
        if settings.DEBUG:
            return 'https://openapiuat.airtel.africa'
        else:
            return 'https://openapi.airtel.africa'
        
    def getAuthToken(self):
        url = f'{self.baseUrl()}/auth/oauth2/token'
        headers = {
            'Content-Type': 'application/json',
            'Accept': '*/*'
        }
        data = {
            "client_id": '02de430a-3aba-4812-ace1-e743d94cc698',
            "client_secret": '02de430a-3aba-4812-ace1-e743d94cc698',
            "grant_type": "client_credentials"
        }
        
        try:
            response = requests.post(url, headers=headers,data=json.dumps(data))  
            success = True if response.status_code == 200 else False
            if success == True:
                print('##################################')
                print('Airtel Money Authentication successful')
                print('##################################')
            return {"success": success, "data": response.json()}
        except Exception as ex:
            print('##################################')
            print('Airtel Money Authentication failed')
            print('##################################')
            return {"success": False, "message": str(ex)}


    def accessToken():
        airtel = AirtelMoney()
        auth_results = airtel.getAuthToken()
        if auth_results['success']:
            access_token = auth_results['data']['access_token']
            #get validity time of the access token. 7200
            expires_in = auth_results['data']['expires_in']
            return access_token
        else:
            return None


    def collectMoney(self, accessToken, reference, customerPhoneNumber, amount, transactionId):
        url = f'{self.baseUrl()}/merchant/v1/payments/'
        headers = {
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'X-Country': 'UG', # payer's country in ISO format
            'X-Currency': 'UGX', # payer's currency in ISO format
            'Authorization': f'Bearer  {accessToken}'
        }
        data = {
            "reference": reference, 
            "subscriber": {
                "country": "UG", # in ISO country code
                "currency": "UGX", # in ISO currency code
                "msisdn": int(customerPhoneNumber) # eg. 708658321
            },
            "transaction": {
                "amount": int(amount),
                "country": "UG",
                "currency": "UGX",
                "id": transactionId # random-unique-id
            }
        }
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))  
            success = True if response.status_code == 200 else False
            # print('##################################')
            # print('Airtel Money collection successful')
            # print('##################################')
            return {"success": success, "data": response.json()}
        except Exception as e:
            # print('##################################')
            # print('Airtel Money collection failed')
            # print('##################################')
            return {"success": False, "message": str(e)}


    def checkCollectionStatus(self,accessToken,id):
        url = f'{self.baseUrl()}/standard/v1/payments/{id}'
        headers = {
            'Content-Type': 'application/json',
            'Accept': '*/*',
            'X-Country': 'UG',
            'X-Currency': 'UGX',
            'Authorization': f'Bearer  {accessToken}'
        }
        try:
            response = requests.get(url, headers=headers)  
            statusCode = response.status_code
            success = True if statusCode == 200 else False
            return {
                "success": success, 
                "status": statusCode, 
                "data": response.json()
            }
        except Exception as e:
            return {
                "success":False,
                "status":status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message":str(e)
            }
