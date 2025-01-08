from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, HttpRequest, JsonResponse, HttpResponseBadRequest

from core.utils import info_message, create_action, send_email_alert
from .models import Ledger, PaymentMethods, Payments, Remittance, BillingAddress, MainWallet, UserWallet, Subscription, SubscriptionPlan, Tip

from import_export.admin import ExportActionMixin


class LedgerAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('transaction_id', 'amount', 'is_credit', 'is_debit', 'is_valid', 'is_active', 'is_merged', 'timestamp')
    search_fields = ('transaction_id',)
    list_filter = ('is_active', 'is_credit', 'is_debit', 'is_valid', 'is_merged', 'timestamp')
    list_per_page = 50


class PayementMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created', 'updated')


@staff_member_required
def approvePayment(request, id):
    response_data = {}
    payment = Payments.objects.get(id=id)
    if request.method == 'POST':
        transactionId = request.POST.get('transactionId')
        payment_id = request.POST.get('paymentId')
        initiated_payment = Payments.objects.get(id=payment_id) #Just to make sure what ID was sent is got back
        initiated_payment.transaction_id = transactionId
        initiated_payment.cleared_by = request.user
        initiated_payment.is_successful = True
        response_data['response'] = 'Payment Complete'
        initiated_payment.save()
        return JsonResponse(response_data, safe=False)
        # return HttpResponseRedirect(request.get_full_path())
    else:    
        return render(request=request, template_name='admin/finance/payments/payments.html', context={**admin.site.each_context(request), 'payment': payment})


@staff_member_required
def declinePayment(request, id):
    response_data = {}
    # payment = Payments.objects.get(id=id)
    if request.method == 'POST':
        # payment_id = request.POST.get('paymentId')
        initiated_payment = Payments.objects.get(id=id)
        initiated_payment.cleared_by = request.user
        initiated_payment.is_successful = False
        initiated_payment.declined = True
        response_data['response'] = 'Payment Declined or Invalid'
        initiated_payment.save()
        return JsonResponse(response_data, safe=False)
        # return HttpResponseRedirect(request.get_full_path())


class PaymentAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('payment_id', 'phone', 'is_successful', 'declined', 'is_processed', 'created', 'approve_Payment')
    list_per_page = 25
    search_fields = ('payment_id', 'phone')
    list_filter = ('is_successful', 'declined', 'is_processed', 'created',)
    change_list_template = "admin/finance/payments/payments_changelist.html"

    class Meta:
        model = Payments
    

    class Media:
        js = ("assets/js/autorefresh.js",)
    
    def get_urls(self):
        return [path("approve_payment/<id>/", self.admin_site.admin_view(approvePayment), name=f"approve_payment"), *super().get_urls(),]
    
    def approve_Payment(self, obj: Payments) -> str:
        url = reverse(f"admin:approve_payment", args=[obj.id])
        return format_html(f'<a href="{url}">Approve 📝</a>')


class RemittanceAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('user', 'amount', 'is_valid', 'is_successful', 'is_cancelled', 'created', 'updated')
    list_per_page = 25
    list_filter = ('is_valid', 'is_successful', 'is_cancelled', 'created', 'updated')
    # actions = ['approve_refund']

    # def approve_refund(self, request, queryset):
    #     queryset.update(is_valid=True)


class MainWalletAdmin(admin.ModelAdmin):
    list_display = ('amount', 'updated')


class UserWalletAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('owner', 'is_active', 'points', 'created', 'updated')


class SubscriptionAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('user', 'plan', 'start_date', 'end_date', 'is_active')


class TipAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'is_active', 'timestamp', 'updated')


admin.site.register(BillingAddress)
admin.site.register(PaymentMethods)
admin.site.register(Ledger, LedgerAdmin)
admin.site.register(Remittance, RemittanceAdmin)
admin.site.register(Payments, PaymentAdmin)
admin.site.register(MainWallet, MainWalletAdmin)
admin.site.register(UserWallet, UserWalletAdmin)
admin.site.register(SubscriptionPlan)
admin.site.register(Tip, TipAdmin)
admin.site.register(Subscription, SubscriptionAdmin)


