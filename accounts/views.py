import datetime
from time import sleep

from django.http import Http404
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.contrib.auth import login
from django.core.mail import send_mail
from django.contrib.auth.views import LoginView
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.shortcuts import render, redirect, get_object_or_404, HttpResponseRedirect
from django.views.generic import CreateView, TemplateView, UpdateView, DeleteView, DetailView

from .tokens import account_activation_token
from tracking_analyzer.models import Tracker
from .models import User, UserProfile, PayLink, Portfolio, PortfolioType,  Receipt
from .forms import AboutMeForm, CoverPhotoForm, UserSignUpForm, ProfileChangeForm, PortfolioForm, ImageForm, ReportUserForm, ReportEvidenceForm, PayLinkForm


class LogInView(LoginView):
	template_name = 'accounts/auth/login.html'

	def get_success_url(self):
		messages.success(self.request, 'Welcome Back!')
		url = self.get_redirect_url()
		return url or '/'
			
		
def user_signup(request, ref_code=None):
	user_type = 'buyer'
	if request.method == 'POST':
		form = UserSignUpForm(request.POST)
		if form.is_valid():
			user = form.save()
			domain_url = get_current_site(request)
			subject = 'Activate your PayLink Account'
			message = render_to_string('accounts/auth/registration/account_activation_email.html', {
				'user': user,
				'domain': domain_url.domain,
				'uid': urlsafe_base64_encode(force_bytes(user.pk)),
				'token': account_activation_token.make_token(user),
			})
			user.email_user(subject, message) #send email synchronously
			return redirect('account_activation_sent')
	else:
		form = UserSignUpForm()
	return render(request, 'accounts/auth/registration/signup.html', {'form': form, 'user_type': user_type})


def resend_activation_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            if user.is_active:
                messages.info(request, 'Your account is already active. Please log in.')
                return redirect('login')
            
            # Send the activation email
            domain_url = get_current_site(request)
            subject = 'Resend: Activate Your PayLink Account'
            message = render_to_string('accounts/auth/registration/account_activation_email.html', {
                'user': user,
                'domain': domain_url.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            user.email_user(subject, message)  # Send email synchronously
            messages.success(request, 'A new activation email has been sent. Please check your inbox.')
        except User.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
    
    return render(request, 'accounts/auth/registration/resend_activation_email.html')

def account_activation_sent(request):
	return render(request, 'accounts/auth/registration/account_activation_sent.html', {})


def activate(request, uidb64, token, backend='django.contrib.auth.backends.ModelBackend'):
	try:
		uid = force_str(urlsafe_base64_decode(uidb64))
		print(uid)
		user = User.objects.get(pk=uid)
		print(user)
	except (TypeError, ValueError, OverflowError, user.DoesNotExist):
		user = None

	if user is not None and account_activation_token.check_token(user, token):
		user.is_active = True
		user.user_profile.email_confirmed = True
		user.user_profile.is_active = True
		user.user_profile.save()
		user.save()
		# user_logged_in.send(user.__class__, instance=user, request=user)
		login(request, user, backend='django.contrib.auth.backends.ModelBackend')
		messages.success(request, 'Account Activation Successful, Please complete your profile')
		return redirect('update_profile', user.user_profile.id)
	return redirect('login')


def check_username(request):
	username = request.GET.get('username')
	data = {
	   'username_exists': UserProfile.objects.filter(username__iexact=username).exists()
	}
	return JsonResponse(data)


def check_user_email(request):
	email = request.GET.get('email')
	data = {
	   'email_exists': User.objects.filter(email__iexact=email).exists()
	}
	return JsonResponse(data)


@login_required
def gotomyaccount(request):
	return render(request, 'accounts/myaccount.html', {})


@login_required
def account_page(request):
	return render(request, 'accounts/profile_account_overview.html')


@login_required
def profile(request, id, username, template_name='accounts/user_profile.html'):
	portfolio = None
	try:
		profile = UserProfile.objects.get(user__id=id, username=username)
		pay_links = PayLink.objects.filter(user=request.user).order_by('-updated')
	except UserProfile.DoesNotExist:
		messages.error(request, 'User profile could not be found!')
		return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))
	current_user = request.user
	form = PayLinkForm()
	try:
		portfolio = Portfolio.objects.get(user=profile)
		portfolio_form = PortfolioForm(instance=portfolio)
	except Portfolio.DoesNotExist:
		messages.info(request, 'You need to set up a business portfolio to continue')
		return redirect('create_or_update_portfolio', profile.id)
	context = {'profile': profile, 'current_user':current_user, 'pay_links': pay_links, 'form':form, 'portfolio': portfolio, 'portfolio_form':portfolio_form}
	Tracker.objects.create_from_request(request, profile)
	return render(request, template_name, context)


@login_required
def update_profile(request, id, template_name='accounts/edit_profile.html'):
	profile = get_object_or_404(UserProfile, id=id)
	if request.method == 'POST':
		form = ProfileChangeForm(request.POST or None, request.FILES, instance=profile)
		if form.is_valid():
			profile = form.save(commit=False)
			profile.save()
			user = profile.user
			user.first_name = profile.first_name
			user.last_name = profile.last_name
			user.save()
			messages.success(request, 'Your profile updated successfully')
			if not profile.photo:
				return redirect('upload_photo', profile.id)
			
			try:
				portfolio = Portfolio.objects.get(user=profile)
			except Portfolio.DoesNotExist:
				messages.info(request, 'You need to set up a business portfolio to continue')
			if not portfolio:
				messages.info(request, 'You need to set up a business portfolio to continue')
				return redirect('create_or_update_portfolio', profile.id)
			else:
				return redirect('profile', profile.user.id, profile.username)
	else:
		form = ProfileChangeForm(instance=profile)
	return render(request, template_name, {'form': form, 'profile': profile})


def create_or_update_portfolio(request, id):
	try:
		profile = UserProfile.objects.get(id=id)
		portfolio_types = PortfolioType.objects.filter(is_active=True)
		try:
			portfolio = Portfolio.objects.get(user=profile)
			if request.method == "POST":
				form = PortfolioForm(request.POST or None, request.FILES, instance=portfolio)
				if form.is_valid():
					portfolio = form.save(commit=False)
					portfolio_type_id = request.POST.get('kind_of_business')
					portfolio_type = PortfolioType.objects.get(id=portfolio_type_id)
					portfolio.kind_of_business = portfolio_type
					portfolio.save()
					messages.success(request, 'Your portfolio has been updated successfully')
					return redirect('profile', profile.user.id, profile.username)
			form = PortfolioForm(instance=portfolio)
			return render(request, "accounts/describe_business.html", {'form':form, 'portfolio_types':portfolio_types, 'profile':profile, 'portfolio':portfolio})
		except Portfolio.DoesNotExist:
			if request.method == "POST":
				form = PortfolioForm(request.POST or None, request.FILES)
				if form.is_valid():
					new_portfolio = form.save(commit=False)
					portfolio_type_id = request.POST.get('kind_of_business')
					portfolio_type = PortfolioType.objects.get(id=portfolio_type_id)
					new_portfolio.user = profile
					new_portfolio.kind_of_business = portfolio_type
					new_portfolio.save()
					messages.success(request, 'Your portfolio has been created successfully')
					return redirect('profile', profile.user.id, profile.username)
				messages.error(request, f'There was an error submitting your portfolio! {form.errors}')
			form = PortfolioForm()
			return render(request, "accounts/describe_business.html", {'form':form, 'portfolio_types':portfolio_types, 'profile':profile})
	except UserProfile.DoesNotExist:
		messages.error(request, 'User Profile Could not be obtained')
	except Exception as e:
		print(e)
		messages.error(request, f"An Internal Error occurred with this process {e}")
	return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))


def upload_photo(request, id, template_name='accounts/upload_profile_photo.html'):
	profile = get_object_or_404(UserProfile, id=id)
	if request.method == 'POST':
		form = ImageForm(request.POST or None, request.FILES, instance=profile)
		if form.is_valid():
			form.save()
			messages.success(request, 'Photo uploaded successfully')
			if not profile.photo:
				return redirect('upload_photo', profile.id)
			else:
				return redirect('profile', profile.user.id, profile.username)
	else:
		form = ImageForm(instance=profile)
	return render(request, template_name, {'form': form, 'profile': profile})


def upload_cover_photo(request, id, template_name='accounts/edit_profile.html'):
	profile = get_object_or_404(UserProfile, id=id)
	if request.method == 'POST':
		form = CoverPhotoForm(request.POST or None, request.FILES, instance=profile)
		if form.is_valid():
			form.save()
			messages.success(request, 'Photo uploaded successfully')
			return redirect('profile', profile.user.id, profile.username)
	else:
		form = CoverPhotoForm(instance=profile)
	return render(request, template_name, {'form': form, 'profile': profile})


def user_bio(request, id, template_name='accounts/edit_profile.html'):
	profile = get_object_or_404(UserProfile, id=id)
	if request.method == 'POST':
		form = AboutMeForm(request.POST or None, request.FILES, instance=profile)
		if form.is_valid():
			form.save()
			messages.success(request, 'Profile updated successfully')
			return redirect('profile', profile.user.id, profile.username)
	else:
		form = AboutMeForm(instance=profile)
	return render(request, template_name, {'form': form, 'profile': profile})


@login_required
def notifications(request):
	from core.models import Action
	notifications = Action.objects.filter(user=request.user)
	return render(request, 'accounts/notifications.html', {'notifications':notifications})


@login_required
def account_settings(request, id, template_name='accounts/settings.html'):
	user_profile = get_object_or_404(UserProfile, id=id)
	context = {'user_profile': user_profile}
	return render(request, template_name, context)


@login_required
def delete_user_account(request, id, template_name='core/forms/delete.html'):
	user_account = get_object_or_404(User, id=id)
	if request.method == 'POST':
		user_account.delete()
		messages.success(request, 'Account delete successful. Please write to as at <a href="mailto:support@daraza.net">support@daraza.net</a> if you faced any challenges with PayLink.')
		return redirect('account_login')
	return render(request, template_name, {'object': user_account, 'entity': 'your user account', 'narrative':'We hate to see you go! Are sure you can not change you mind? PayLink will continue to work to improve your user experience'})


@login_required
def account_settings(request):
	profile = request.user.user_profile
	return render(request, 'accounts/settings.html', {'profile':profile})


def report_user(request, id, link_id):
    try:
        # Fetch the PayLink and the user to report
        link = get_object_or_404(PayLink, id=link_id)
        user_to_report = User.objects.get(id=id)

        if request.method == 'POST':
            form = ReportUserForm(request.POST)
            file_form = ReportEvidenceForm(request.POST, request.FILES)

            if form.is_valid() and file_form.is_valid():
                # Save the report
                report = form.save(commit=False)
                report.reported_user = user_to_report
                report.link = link
                report.save()

                # Save the evidence file if provided
                if request.FILES.get('file'):
                    file = file_form.save(commit=False)
                    file.report = report
                    file.save()

                messages.success(request, 'User reported successfully.')
            else:
                messages.error(request, 'Something went wrong. Please check the form and try again.')

        else:
            form = ReportUserForm()
            file_form = ReportEvidenceForm()

    except Http404:
        messages.error(request, 'Your profile was not found. Please complete your profile first.')
    except User.DoesNotExist:
        messages.error(request, 'The user you are trying to report does not exist.')
    except Exception as e:
        messages.error(request, f'An unexpected error occurred: {str(e)}')

    # Render the form regardless of the scenario
    form = form if 'form' in locals() else ReportUserForm()
    file_form = file_form if 'file_form' in locals() else ReportEvidenceForm()

    return render(request, 'accounts/report_user.html', {
        'form': form,
        'file_form': file_form,
        'link': locals().get('link', None),
    })


	

def create_pay_link(request):
    if request.method == 'POST':
        form = PayLinkForm(request.POST, request.FILES)
        if form.is_valid():
            pay_link = form.save(commit=False)
            pay_link.user = request.user
            pay_link.save()
            messages.success(request, 'PayLink generated successfully!')
            return redirect('profile', request.user.id, request.user.username)
        else:
            messages.error(request, 'There was an error creating your PayLink.')
    else:
        form = PayLinkForm()
    return render(request, 'accounts/user_profile.html', {'form': form})


def pay_view(request, link_id):
	try:
		pay_link = PayLink.objects.get(link_id=link_id, is_active=True)
	except PayLink.DoesNotExist:
		pass
	return render(request, 'accounts/pay.html', {'pay_link': pay_link})


def edit_pay_link(request):
    if request.method == 'POST':
        pay_link_id = request.POST.get('pay_link_id')
        pay_link = get_object_or_404(PayLink, id=pay_link_id, user=request.user)
        pay_link.name = request.POST.get('name')
        pay_link.description = request.POST.get('description')
        pay_link.save()
        messages.success(request, "PayLink edited successfully!")
        return redirect('profile', request.user.id, request.user.username)


def view_receipt(request, transaction_id):
    """
    View to retrieve and display a specific transaction receipt
    """
    try:
        transaction = get_object_or_404(
            Receipt, 
            id=transaction_id, 
            user=request.user
        )

        context = {
            'transaction': transaction,
            'pay_link': transaction.pay_link
        }

        return render(request, 'payment/receipt.html', context)

    except Receipt.DoesNotExist:
        messages.error(request, "Receipt not found.")
        return redirect('dashboard')


def delete_pay_link(request):
    if request.method == 'POST':
        pay_link_id = request.POST.get('pay_link_id')
        pay_link = get_object_or_404(PayLink, id=pay_link_id, user=request.user)
        pay_link.delete()
        messages.success(request, "PayLink deleted successfully!")
        return redirect('profile', request.user.id, request.user.username)
	
