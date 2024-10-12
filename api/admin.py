#api/admin.py

from django.contrib import admin
from .models import User, Vendor, IDCard, Payment, Transaction, IDCardFormat, Wallet

admin.site.register(User)
admin.site.register(Vendor)
admin.site.register(IDCard)
admin.site.register(Payment)
admin.site.register(Transaction)
@admin.register(IDCardFormat)
class IDCardFormatAdmin(admin.ModelAdmin):
    list_display = ('format_name', 'display_name')

class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'deduction_amount')
    search_fields = ('user__username',)

admin.site.register(Wallet, WalletAdmin)
