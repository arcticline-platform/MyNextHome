from django.contrib import admin
# from django.urls import reverse_lazy
# from django.urls import path, reverse
# from django.utils.html import format_html
# from django.shortcuts import render, HttpResponseRedirect
# from django.contrib.admin.views.decorators import staff_member_required
# from django.http import HttpResponse, HttpRequest, JsonResponse, HttpResponseBadRequest

# from core.utils import info_message, create_action, send_email_alert
from .models import PaymentMethods, Payments, Remittance, BillingAddress, UserWallet, Subscription, SubscriptionPlan

from import_export.admin import ExportActionMixin


class PaymentAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('payment_id', 'phone', 'is_successful', 'declined', 'is_processed', 'created')
    list_per_page = 25
    search_fields = ('payment_id', 'phone')
    list_filter = ('is_successful', 'declined', 'is_processed', 'created',)
    change_list_template = "admin/finance/payments/payments_changelist.html"

    class Meta:
        model = Payments
    

    class Media:
        js = ("assets/js/autorefresh.js",) 


class RemittanceAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('user', 'amount', 'is_valid', 'is_successful', 'is_cancelled', 'created', 'updated')
    list_per_page = 25
    list_filter = ('is_valid', 'is_successful', 'is_cancelled', 'created', 'updated')
    # actions = ['approve_refund']

    # def approve_refund(self, request, queryset):
    #     queryset.update(is_valid=True)


class UserWalletAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('owner', 'is_active', 'created', 'updated')


class SubscriptionAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active')


admin.site.register(BillingAddress)
admin.site.register(PaymentMethods)
admin.site.register(Remittance, RemittanceAdmin)
admin.site.register(Payments, PaymentAdmin)
admin.site.register(UserWallet, UserWalletAdmin)
admin.site.register(SubscriptionPlan)
admin.site.register(Subscription, SubscriptionAdmin)


