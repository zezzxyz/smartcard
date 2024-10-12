# id_card_generator/api/serializers.py
from rest_framework import serializers
from .models import User, Vendor, IDCard, Transaction

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'date_joined']

class VendorSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Vendor
        fields = ['user', 'company_name', 'address', 'phone_number', 'wallet_balance']

class IDCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = IDCard
        fields = ['id_number', 'name', 'photo', 'vendor', 'id_format', 'dob', 'issue_date', 'expiry_date', 'card_number']
        extra_kwargs = {
            'dob': {'format': '%d/%m/%Y'}
        }

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['vendor', 'amount', 'transaction_type', 'date']




