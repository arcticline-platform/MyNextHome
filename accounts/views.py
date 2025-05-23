import re
import logging
import datetime
import traceback
from time import sleep

from django.http import Http404
from django.conf import settings
from django.db import transaction
# from django.utils import timezone
from django.contrib import messages
# from django.http import HttpResponse
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.contrib.auth import login
# from django.core.mail import send_mail
from django.http import HttpResponseNotAllowed
# from django.contrib.auth.views import LoginView
# from django.template.loader import render_to_string
# from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import update_session_auth_hash
# from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
# from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import render, redirect, get_object_or_404 #, HttpResponseRedirect
# from django.views.generic import CreateView, TemplateView, UpdateView, DeleteView, DetailView

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import ErrorLogs
from core.tasks import send_email_task
from core.utils import send_email_alert
from .tokens import account_activation_token
from tracking_analyzer.models import Tracker
from .serializers import UserSignupSerializer, LoginSerializer
from .models import User, UserProfile, Portfolio, PortfolioType,  Receipt, VerificationToken
from .forms import AboutMeForm, CoverPhotoForm, UserSignUpForm, ProfileChangeForm, PortfolioForm, ImageForm, ReportUserForm, ReportEvidenceForm

logger = logging.getLogger(__name__)

User = get_user_model()

# Helper function for sending verification token (implement using your email/SMS provider)
def send_verification(user, token):
    """Send verification token to user via email and SMS"""
    try:
        # Send email verification
        send_email_alert(
            email=user.email,
            subject="Verify Your MyNextHome Account",
            message=(
                f"Dear {user.first_name},\n\n"
                f"Thank you for registering with MyNextHome. Your verification code is:\n\n"
                f"{token}\n\n"
                "Please enter this code in the verification page to activate your account.\n\n"
                "If you did not request this verification, please ignore this message.\n\n"
                "For support, contact us at support@daraza.net or call +256789079301.\n\n"
                "Best regards,\n"
                "The MyNextHome Team"
            )
        )

        # Send SMS verification
        # if user.phone: 
        #     send_sms_alert(
        #         body=f"Your MyMextHome OTP verification code is: {token}",
        #         phone_number=user.phone
        #     )
    except Exception as e:
        ErrorLogs.objects.create(
            error_narration=f"Error sending verification: {str(e)}",
            stack_trace=traceback.format_exc()
        )


def signup(request):
    return render(request, 'accounts/signup.html')

def login_user(request):
    return render(request, 'accounts/login.html')

@csrf_protect 
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect('login')
    return HttpResponseNotAllowed(["POST"])


@extend_schema(exclude=True)
class SignupView(APIView):
    authentication_classes = []  # Disable default authentication
    permission_classes = []      # Disable default permissions

    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)

        fullname = request.data['full_name']
       
        first_name = fullname.split(' ')[0]
        second_name = fullname.split(' ')[1]

        if serializer.is_valid():
            user = serializer.save()

            user.first_name = first_name
            user.second_name = second_name
            user.save()
            profile = user.user_profile
            profile.first_name = first_name
            profile.second_name = second_name
            profile.save()

            # Create a verification token
            token_obj = VerificationToken.objects.create(user=user.user_profile)
            # Send verification (email/SMS) with token_obj.token
            send_verification(user, token_obj.token)
            return Response(
                {"message": "Signup successful. Please verify your email or phone."},
                status=status.HTTP_201_CREATED
            )
        # Format the validation errors into a clearer structure
        formatted_errors = {}
        for field, errors in serializer.errors.items():
            formatted_errors[field] = [str(error) for error in errors]
        return Response(
            {
            "status": "error",
            "errors": formatted_errors
            }, 
            status=status.HTTP_400_BAD_REQUEST
        )

@extend_schema(exclude=True)
class VerifyUserView(APIView):
    authentication_classes = []  # Disable default authentication
    permission_classes = []
    def post(self, request):
        token = request.data.get('verification_code')
        print('Token: ', token)
        if not token:
            return Response({"error": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            verification = VerificationToken.objects.get(token=token)
        except VerificationToken.DoesNotExist:
            print('Token is invalid')
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        # Activate user and delete token
        profile = verification.user
        profile.is_active = True
        profile.is_verified = True
        profile.save()
        user = profile.user
        user.is_active = True
        user.save()
        verification.delete()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return Response({"message": "User verified successfully."}, status=status.HTTP_200_OK)


@extend_schema(exclude=True)
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            username_or_email_or_phone = serializer.validated_data['username_or_email_or_phone']
            password = serializer.validated_data['password']

            # Try to get user by email or phone number
            try:
                if '@' in username_or_email_or_phone:
                    # It's an email
                    user = User.objects.get(email=username_or_email_or_phone)
                else:
                    # It's a phone number
                    user = User.objects.get(phone=username_or_email_or_phone)

                # Authenticate user
                user = authenticate(request, username=user.username, password=password)
                if user is not None:
                    # Generate JWT token
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    refresh = RefreshToken.for_user(user)
                    return Response({
                        'access': str(refresh.access_token),
                        'refresh': str(refresh),
                    })
                else:
                    return Response({"error": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
            except ObjectDoesNotExist:
                return Response({"error": "User with given email or phone number not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@login_required
def update_user_profile(request):
    """
    Allows a user to update their user profile.
    """
    if not request.user.is_authenticated:
        return redirect('wifi_manager_login')
    try:
        profile = UserProfile.objects.get(user=request.user)

        if request.method == "POST":
            form = ProfileChangeForm(request.POST, instance=profile)
            if form.is_valid():
                form.save()
                user = request.user
                user.first_name = profile.first_name
                user.last_name = profile.last_name
                user.save()
                messages.success(request, "User profile updated successfully.")
                return redirect("wifi_manager_dashboard")
            else:
                messages.error(request, "Please correct the errors below.")
        else:
            form = ProfileChangeForm(instance=profile)

        return render(request, "accounts/update_user_profile.html", {"form": form, "profile": profile})
    except UserProfile.DoesNotExist:
        logout(request)
        messages.warning(request, "Sorry, your user profile could not be found. Try logging in and trying again!")
    except Exception as e:
        messages.error(request, "Internal Error occurred in updating your user profile. Please contact support!")
        ErrorLogs.objects.create(error_narration=f"Error in update_user_profile: {str(e)}", stack_trace=traceback.format_exc())
    return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))


@login_required
def notification_preferences(request):
    try:
        if request.method == 'POST':
            # Get the profile instance for the current user
            profile = request.user.user_profile
            
            # Update the profile with form data
            profile.receive_email_notifications = 'receive_email_notifications' in request.POST
            profile.receive_sms_notifications = 'receive_sms_notifications' in request.POST
            profile.receive_marketing_notifications = 'receive_marketing_notifications' in request.POST
            
            # Save the updated profile
            profile.save()
            
            # Add a success message
            messages.success(request, 'Your notification preferences have been updated successfully.')
            
            # Redirect back to the same page
            return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))
        
        # For GET requests, just render the form
        return render(request, 'notification_preferences.html')
    except ObjectDoesNotExist:
        messages.error(request, "User profile not found. Please contact support.")
        return redirect('dashboard')
    except Exception as e:
        ErrorLogs.objects.create(
            error_narration=f"Error in notification_preferences: {str(e)}",
            stack_trace=traceback.format_exc()
        )
        messages.error(request, "An error occurred while updating your preferences. Please try again later.")
        return redirect('dashboard')


@login_required
def accounts_password_change(request):
    try:
        if request.method == 'POST':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            # Check if current password is correct
            if not request.user.check_password(current_password):
                messages.error(request, 'Your current password was entered incorrectly.')
                return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))
            
            # Check if new password and confirm password match
            if new_password != confirm_password:
                messages.error(request, "The two password fields didn't match.")
                return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))
            
            # Validate password strength
            if len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
                return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))
            
            if not re.search(r'\d', new_password):
                messages.error(request, 'Password must contain at least one number.')
                return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))
            
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
                messages.error(request, 'Password must contain at least one special character.')
                return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))
            
            # Change the password
            user = request.user
            user.set_password(new_password)
            user.save()
            
            # Update session to prevent user from being logged out
            update_session_auth_hash(request, user)
            
            messages.success(request, 'Your password was successfully updated!')
            return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))
        
        return render(request, 'password_change.html')
    except Exception as e:
        ErrorLogs.objects.create(
            error_narration=f"Error in accounts_password_change: {str(e)}",
            stack_trace=traceback.format_exc()
        )
        messages.error(request, "An error occurred while changing your password. Please try again later.")
        return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))



def contact_support(request):
    if request.method == 'POST':
        support_name = request.POST.get('support_name')
        support_email = request.POST.get('support_email')
        support_subject = request.POST.get('support_subject')
        support_message = request.POST.get('support_message')

        # Basic validation: ensure subject and message are provided
        if not support_subject or not support_message:
            messages.error(request, "Subject and message are required.")
            return redirect('contact_support')  # Change the URL name if needed

        # Construct the email body including the sender details.
        email_body = (
            f"Support Request from {support_name} ({support_email}):\n\n"
            f"{support_message}"
        )

        try:
            # send_mail(
            #     subject=support_subject,
            #     message=email_body,
            #     from_email=settings.DEFAULT_FROM_EMAIL,
            #     recipient_list=[settings.SUPPORT_EMAIL, 'codewithallan@gmail.com'],  # Configure this in your settings
            #     fail_silently=False,
            # )
            recipient_list=[settings.SUPPORT_EMAIL, 'codewithallan@gmail.com']
            send_email_task.apply_async(args=[recipient_list, support_subject, email_body])
            messages.success(request, "Your message has been sent successfully!")
        except Exception as e:
            messages.error(request, "There was an error sending your message. Please try again later.")

        return redirect('contact_support')
    else:
        # For GET requests, simply render the support form.
        return render(request, 'index.html')


@login_required
def delete_account(request):
    
    if request.method == "POST":
        user = request.user
        password = request.POST.get("password")
        reason = request.POST.get("reason", "")
        feedback = request.POST.get("feedback", "")

        # Verify the password
        if not user.check_password(password):
            messages.error(request, "Incorrect password. Please try again.")
            return redirect("delete_account")

        # Optionally store the deletion reason and feedback
        if reason or feedback:
            # Assuming there's a model to store feedback (optional)
            from accounts.models import AccountDeletionLog  # Create this model if needed
            AccountDeletionLog.objects.create(
                user_name=user.username, reason=reason, feedback=feedback
            )

        # Delete the user account
        with transaction.atomic():
            user.delete()

        # Log the user out
        logout(request)

        messages.success(request, "Your account has been permanently deleted.")
        return redirect("login")  # Redirect to homepage or landing page

    return render(request, "accounts/delete_account.html")



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
def profile(request, id, username, template_name='accounts/user_profile.html'):
	portfolio = None
	try:
		profile = UserProfile.objects.get(user__id=id, username=username)
	except UserProfile.DoesNotExist:
		messages.error(request, 'User profile could not be found!')
		return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))
	current_user = request.user
	try:
		portfolio = Portfolio.objects.get(user=profile)
		portfolio_form = PortfolioForm(instance=portfolio)
	except Portfolio.DoesNotExist:
		messages.info(request, 'You need to set up a business portfolio to continue')
		return redirect('create_or_update_portfolio', profile.id)
	context = {'profile': profile, 'current_user':current_user, 'portfolio': portfolio, 'portfolio_form':portfolio_form}
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
        user_to_report = User.objects.get(id=id)

        if request.method == 'POST':
            form = ReportUserForm(request.POST)
            file_form = ReportEvidenceForm(request.POST, request.FILES)

            if form.is_valid() and file_form.is_valid():
                # Save the report
                report = form.save(commit=False)
                report.reported_user = user_to_report
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
