from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from django.core.mail import EmailMessage
from django.contrib.sites.models import Site
from django.shortcuts import render, redirect
from django.views.generic.edit import CreateView
from django.urls import path, reverse, reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required

# from seo.admin import register_seo_admin
from core.models import SEOMetaData 
from core.tasks import send_sms_alert_task
from core.utils import send_sms_alert
from .forms import NewsLetterForm, BroadcastForm
from .models import Action, File, SystemUtility, FAQ, EmailSubscription, NewsLetter, PhoneNumber, SystemEmail, SMS_Subscription, SMS_Broadcast, ErrorLogs, Update, User_Inquiry, Notification

from import_export.admin import ExportActionMixin


admin.site.unregister(Site)
class SiteAdmin(admin.ModelAdmin):
    fields = ('id', 'name', 'domain')
    readonly_fields = ('id',)
    list_display = ('id', 'name', 'domain')
    list_display_links = ('name',)
    search_fields = ('name', 'domain')
admin.site.register(Site, SiteAdmin)


class FAQAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('question', 'answer', 'created', 'updated')
    list_per_page = 50
    list_filter = ['is_answered', 'is_archived']
    search_fields = ('questions',)


class User_InquiryAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('user', 'subject', 'created', 'updated')
    list_per_page = 50
    list_filter = ['is_answered',]
    search_fields = ('subject',)


class ActionAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('user', 'verb', 'target', 'timestamp')
    list_filter = ('timestamp',)
    list_per_page = 100
    search_fields = ('verb',)


class PhoneNumberInline(admin.TabularInline):
    model = PhoneNumber
    raw_id_fields = ['utility']


class SystemEmailInline(admin.TabularInline):
    model = SystemEmail
    raw_id_fields = ['utility']


class SystemUtilityAdmin(admin.ModelAdmin):
    def add_view(self, request):
        if request.method == "POST":
            # A single global SystemUtility object is required
            if SystemUtility.objects.count() >= 1:
                # redirect to a page saying 
                return HttpResponseRedirect("Can only create one SystemUtility!")
        return super(SystemUtilityAdmin, self).add_view(request)

    # form  #smilar feature like add_view
    inlines = [PhoneNumberInline, SystemEmailInline]


class SendNewsLetterView(PermissionRequiredMixin, CreateView):
    permission_required = "core.view_newsletter"
    template_name = "admin/core/newsletter/newsletter.html"
    model = NewsLetter
    fields = ['subject','message']
    success_url = reverse_lazy('tasks')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "The task was created successfully.")
        return super(SendNewsLetterView,self).form_valid(form)
    
    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            **admin.site.each_context(self.request),
            "opts": self.model._meta,
        }


@staff_member_required
def newsletter(request, **kwargs):
    if request.method == 'POST':
        form = NewsLetterForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data.get('subject')
            receivers = form.cleaned_data.get('receivers').split(',')
            email_message = form.cleaned_data.get('message')
            mail = EmailMessage(subject, email_message, f"Shukrani Food <{request.user.email}>", bcc=receivers)
            mail.content_subtype = 'html'
            if mail.send():
                messages.success(request, "Email sent succesfully")
            else:
                messages.error(request, "There was an error sending email")
            return redirect('/main_access/core/emailsubscription/')
        else:
            for error in list(form.errors.values()):
                messages.error(request, error)
            return redirect('/main_access/core/emailsubscription/')
    form = NewsLetterForm()
    form.fields["receivers"].initial = ','.join([active.email for active in EmailSubscription.objects.filter(is_active=True)])
    return render(request=request, template_name='admin/core/newsletter/newsletter.html', context={"form": form, **admin.site.each_context(request),"opts": EmailSubscription._meta})

class EmailSubscriptionAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('user', 'email', 'is_active', 'created', 'updated', 'news_letter')

    def get_urls(self):
        return [
            path(
                "send_news_letter/",
                self.admin_site.admin_view(newsletter),
                name=f"send_news_letter",
            ),
            *super().get_urls(),
        ]

    def news_letter(self, obj: EmailSubscription) -> str:
        url = reverse("admin:send_news_letter")
        return format_html(f'<a href="{url}">Send 📝</a>')


class SMS_SubscriptionAdmin(ExportActionMixin, admin.ModelAdmin):
    list_display = ('user', 'phone', 'is_active', 'created', 'updated')
    search_fields = ('phone',)
    actions = ['deactivate_subscriptions', 'activate_subscriptions']

    def deactivate_subscriptions(self, request, queryset):
        queryset.update(is_active=False)
    
    def activate_subscriptions(self, request, queryset):
        queryset.update(is_active=True)

@staff_member_required
def sms_broadcast(request, id, **kwargs):
    broadcast = SMS_Broadcast.objects.get(id=id)
    if request.method == 'POST':
        form = BroadcastForm(request.POST)
        if form.is_valid():
            receivers = form.cleaned_data.get('receivers').split(',')
            message = form.cleaned_data.get('message')
            sms_receivers = SMS_Subscription.objects.filter(is_active=True)
            for receiver in sms_receivers:
                receiver_phone = str(receiver.phone)
                send_sms_alert_task.apply_async(args=[message, receiver_phone])
            # send_sms_alert(message, receivers)
            messages.success(request, f'Broadcast "{message}" sent')
            return redirect('/main_access/core/sms_broadcast/')
        else:
            for error in list(form.errors.values()):
                messages.error(request, error)
            return redirect('/main_access/core/sms_broadcast/')
    form = BroadcastForm(instance=broadcast)
    return render(request=request, template_name='admin/core/sms_broadcast/broadcast.html', context={"form": form, **admin.site.each_context(request),"opts": SMS_Broadcast._meta})


class SMSBroadcastAdmin(admin.ModelAdmin):
    list_display = ('subject', 'is_active', 'created', 'updated', 'broadcast')
    # actions = ['broadcast',]
    def get_urls(self):
        return [
            path(
                "sms_broadcast/<id>",
                self.admin_site.admin_view(sms_broadcast),
                name=f"sms_broadcast",
            ),
            *super().get_urls(),
        ]

    def broadcast(self, obj: SMS_Broadcast, *args) -> str:
        url = reverse("admin:sms_broadcast", args=[obj.id])
        return format_html(f'<a href="{url}">broacast 📢</a>')


class NewsLetterAdmin(admin.ModelAdmin):
    list_display = ('subject', 'created', 'updated')

class UpdateAdmin(admin.ModelAdmin):
    list_display = ('subject','is_active', 'is_archived', 'created', 'updated')
    list_filter = ('is_active', 'is_archived', 'created', 'updated')


class FilesAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created')


class ErrorLogsAdmin(admin.ModelAdmin):
    list_display = ('error_narration', 'timestamp')


admin.site.register(FAQ, FAQAdmin)
admin.site.register(Notification)
admin.site.register(Update, UpdateAdmin)
admin.site.register(Action, ActionAdmin)
# register_seo_admin(admin.site, SEOMetaData)
admin.site.register(File, FilesAdmin)
admin.site.register(ErrorLogs, ErrorLogsAdmin)
admin.site.register(NewsLetter, NewsLetterAdmin)
admin.site.register(SystemUtility, SystemUtilityAdmin)
admin.site.register(User_Inquiry, User_InquiryAdmin)
admin.site.register(SMS_Broadcast, SMSBroadcastAdmin)
admin.site.register(SMS_Subscription, SMS_SubscriptionAdmin)
admin.site.register(EmailSubscription, EmailSubscriptionAdmin)


