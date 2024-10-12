#id_card_generator/api//models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, User
from django.utils import timezone
from decimal import Decimal, ROUND_DOWN
import logging
logger = logging.getLogger(__name__)
from django.utils.translation import gettext_lazy as _

# Custom user model
class User(AbstractUser):
    email = models.EmailField(unique=True)
    ROLE_CHOICES = (
        ('super_admin', 'Super Admin'),
        ('sub_admin', 'Sub Admin'),
        ('vendor', 'Vendor'),
    )
    role = models.CharField(max_length=11, choices=ROLE_CHOICES, default='vendor')
    first_name = models.CharField(_('first name'), max_length=30, blank=True)
    last_name = models.CharField(_('last name'), max_length=30, blank=True)
    date_joined = models.DateTimeField(_('date joined'), auto_now_add=True)
    is_active = models.BooleanField(_('active'), default=True)

    def __str__(self):
        return self.username

# Vendor model
class Vendor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile')
    company_name = models.CharField(max_length=100)
    address = models.TextField()
    phone_number = models.CharField(max_length=15)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return self.user.username

# ID Card Format model
class IDCardFormat(models.Model):
    format_name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    fields = models.JSONField(default=dict)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    design_template = models.CharField(max_length=100, default='')

    def __str__(self):
        return self.display_name

class IDCard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='id_cards')
    id_number = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='id_photos/')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='id_cards')
    id_format = models.ForeignKey(IDCardFormat, on_delete=models.CASCADE, related_name='id_cards')
    dob = models.DateField()
    issue_date = models.DateField(auto_now_add=True, editable=False)
    expiry_date = models.DateField(null=True, blank=True)
    card_number = models.CharField(max_length=100)  # Removed unique=True
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.card_number}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'ID Card'
        verbose_name_plural = 'ID Cards'


# PDFUpload model
class PDFUpload(models.Model):
    id_card = models.ForeignKey(IDCard, on_delete=models.CASCADE, related_name='pdf_uploads')
    pdf_file = models.FileField(upload_to='pdf_uploads/')
    password_protected = models.BooleanField(default=False)
    password = models.CharField(max_length=100, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id_card.id_format} - {self.id_card.card_number}"

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'PDF Upload'
        verbose_name_plural = 'PDF Uploads'

# Payment model
class Payment(models.Model):
    id_card = models.ForeignKey(IDCard, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.id_card.card_number} - {self.amount}"

    class Meta:
        ordering = ['-payment_date']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

# Transaction model
class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    date = models.DateTimeField(auto_now_add=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id} - {self.amount}"

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'

# EnhancedIDCard model for additional features like header/footer
class EnhancedIDCard(models.Model):
    id_card = models.OneToOneField(IDCard, on_delete=models.CASCADE, related_name='enhanced_id_card')
    header = models.ImageField(upload_to='id_headers/', blank=True, null=True)
    footer = models.ImageField(upload_to='id_footers/', blank=True, null=True)

    def __str__(self):
        return f"{self.id_card.card_number} - Enhanced"

    class Meta:
        verbose_name = 'Enhanced ID Card'
        verbose_name_plural = 'Enhanced ID Cards'

# Wallet class for managing balance
class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    deduction_amount = models.DecimalField(max_digits=10, decimal_places=2, default=2.00)

    def deduct_amount(self, amount):
        # Ensure both balance and amount have the same precision level
        amount = amount.quantize(Decimal('0.00'), rounding=ROUND_DOWN)
        self.balance = self.balance.quantize(Decimal('0.00'), rounding=ROUND_DOWN)

        logger.info(f"Attempting to deduct {amount}. Current balance: {self.balance}")

        if self.balance >= amount:
            self.balance -= amount
            self.save()
            logger.info(f"Deduction successful. New balance: {self.balance}")
            return True
        else:
            logger.error(f"Deduction failed. Insufficient balance: {self.balance}")
            return False

    def __str__(self):
        return f"{self.user.username} - Balance: {self.balance}"

    class Meta:
        db_table = 'wallet'

class ApiWallet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    deduction_amount = models.DecimalField(max_digits=10, decimal_places=2)
    card_number = models.CharField(max_length=255, default="", null=False)
    deduction_date_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_wallet_log'  # Ensure a unique table name here

    def __str__(self):
        return f"{self.user.username} - {self.card_number} - {self.deduction_amount}"






# IDCardData model
class IDCardData(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # ForeignKey to User
    id_card = models.ForeignKey(IDCard, on_delete=models.CASCADE, related_name='extracted_data')
    data = models.JSONField()  # Store extracted data as JSON
    #field1 = models.CharField(max_length=100, blank=True, null=True)  # Add this field
    #field2 = models.CharField(max_length=100, blank=True, null=True)  # Add this field
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.id_card.card_number}"

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'ID Card Data'
        verbose_name_plural = 'ID Card Data'
