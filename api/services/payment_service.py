import requests
from django.conf import settings

class PhonePePaymentService:
    BASE_URL = 'https://api.phonepe.com/v1/'

    def __init__(self):
        self.merchant_id = settings.PHONEPE_MERCHANT_ID
        self.secret_key = settings.PHONEPE_SECRET_KEY

    def initiate_payment(self, amount, user):
        url = f'{self.BASE_URL}/initiate_payment'
        data = {
            'merchant_id': self.merchant_id,
            'amount': amount,
            'user_id': user.id
        }
        response = requests.post(url, json=data, headers={'Authorization': f'Bearer {self.secret_key}'})
        return response.json()

    def check_payment_status(self, transaction_id):
        url = f'{self.BASE_URL}/payment_status/{transaction_id}'
        response = requests.get(url, headers={'Authorization': f'Bearer {self.secret_key}'})
        return response.json()
