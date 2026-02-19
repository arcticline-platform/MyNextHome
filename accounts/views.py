import os
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
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import update_session_auth_hash
# from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.decorators import login_required
from django.contrib.sites.shortcuts import get_current_site
# from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.shortcuts import render, redirect, get_object_or_404 #, HttpResponseRedirect
# from django.views.generic import CreateView, TemplateView, UpdateView, DeleteView, DetailView

from PIL import UnidentifiedImageError
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
from .models import User, UserProfile, Property, Receipt, VerificationToken, FavoriteProperty
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

			# Split full name safely
			name_parts = fullname.strip().split(' ')
			first_name = name_parts[0] if name_parts else "New"
			last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "User"

			user.first_name = first_name
			user.last_name = last_name
			user.save()
			
			profile = user.user_profile
			profile.first_name = first_name
			profile.last_name = last_name
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
				user.first_name = profile.first_name or ""
				user.last_name = profile.last_name or ""
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
def profile(request, template_name='accounts/user_profile.html'):
	try:
		profile, created = UserProfile.objects.get_or_create(user=request.user, username=request.user.username)
		
		if request.method == 'POST':
			form_type = request.POST.get('form_type')
			
			if form_type == 'profile_settings':
				# Update User and Profile basic info
				first_name = request.POST.get('first_name', '')
				last_name = request.POST.get('last_name', '')
				email = request.POST.get('email', '')
				phone = request.POST.get('phone', '')
				bio = request.POST.get('bio', '')
				city = request.POST.get('location', '') # Map template 'location' to model 'city'
				
				# Update local variables for template rendering if needed
				user = request.user
				user.first_name = first_name
				user.last_name = last_name
				user.email = email
				# user.phone = phone # User model also has phone in some versions, check if needed
				user.save()
				
				profile.first_name = first_name
				profile.last_name = last_name
				profile.email = email
				profile.phone = phone
				profile.bio = bio
				profile.city = city
				
				# Handle avatar/photo upload
				if 'avatar' in request.FILES:
					avatar = request.FILES['avatar']
					ext = os.path.splitext(avatar.name)[1].lower()
					if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
						return JsonResponse({'success': False, 'message': f'Unsupported image format: {ext}. Please upload JPG, PNG, WebP, or GIF.'})
					
					profile.photo = avatar
				
				try:
					profile.save()
				except UnidentifiedImageError:
					return JsonResponse({'success': False, 'message': 'The uploaded file could not be identified as a valid image.'})
				except Exception as e:
					logger.error(f"Save error: {str(e)}")
					return JsonResponse({'success': False, 'message': f'Error saving profile: {str(e)}'})
				
				# Handle password change if requested
				old_password = request.POST.get('old_password')
				new_password1 = request.POST.get('new_password1')
				new_password2 = request.POST.get('new_password2')
				
				if old_password and new_password1:
					if not user.check_password(old_password):
						return JsonResponse({'success': False, 'message': 'Current password incorrect.'})
					if new_password1 != new_password2:
						return JsonResponse({'success': False, 'message': 'New passwords do not match.'})
					
					user.set_password(new_password1)
					user.save()
					update_session_auth_hash(request, user)
				
				return JsonResponse({'success': True, 'message': 'Profile updated successfully.'})

		user_listings = Property.objects.filter(listed_by=profile.user).select_related('address').prefetch_related('amenities', 'images')
		# Get saved properties for the user
		from .models import FavoriteProperty
		saved_properties = Property.objects.filter(
			favorites__user=request.user
		).select_related('address', 'property_type').prefetch_related('images', 'amenities').distinct()
	except UserProfile.DoesNotExist:
		messages.error(request, 'User profile could not be found!')
		return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))
	except Exception as e:
		logger.exception(f"Error in profile view: {str(e)}")
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.method == 'POST':
			return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'})
		raise e
		
	current_user = request.user
	context = {
		'profile': profile, 
		'current_user': current_user, 
		'user_listings': user_listings,
		'saved_properties': saved_properties if 'saved_properties' in locals() else Property.objects.none()
	}
	Tracker.objects.create_from_request(request, profile)
	return render(request, template_name, context)


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


# Saved Properties Views
@login_required
@require_http_methods(["POST"])
def toggle_save_property(request, property_id):
	"""Toggle save/unsave a property for the current user"""
	try:
		property_obj = get_object_or_404(Property, id=property_id)
		favorite, created = FavoriteProperty.objects.get_or_create(
			user=request.user,
			property=property_obj
		)
		
		if not created:
			# Property was already saved, so unsave it
			favorite.delete()
			is_saved = False
			message = 'Property removed from saved list'
		else:
			# Property was just saved
			is_saved = True
			message = 'Property saved successfully'
		
		# Update favorite count
		property_obj.update_favorite_count()
		
		return JsonResponse({
			'success': True,
			'is_saved': is_saved,
			'message': message,
			'favorite_count': property_obj.favorite_count
		})
	except Exception as e:
		logger.error(f"Error toggling save property: {str(e)}")
		return JsonResponse({
			'success': False,
			'error': 'An error occurred while saving the property'
		}, status=500)


@login_required
def check_property_saved(request, property_id):
	"""Check if a property is saved by the current user"""
	try:
		property_obj = get_object_or_404(Property, id=property_id)
		is_saved = FavoriteProperty.objects.filter(
			user=request.user,
			property=property_obj
		).exists()
		
		return JsonResponse({
			'is_saved': is_saved
		})
	except Exception as e:
		logger.error(f"Error checking property saved status: {str(e)}")
		return JsonResponse({
			'is_saved': False,
			'error': 'An error occurred'
		}, status=500)


@login_required
@require_http_methods(["POST", "DELETE"])
def remove_saved_property(request, property_id):
	"""Remove a property from saved list"""
	try:
		property_obj = get_object_or_404(Property, id=property_id)
		favorite = FavoriteProperty.objects.filter(
			user=request.user,
			property=property_obj
		).first()
		
		if favorite:
			favorite.delete()
			# Update favorite count
			property_obj.update_favorite_count()
			
			return JsonResponse({
				'success': True,
				'message': 'Property removed from saved list',
				'favorite_count': property_obj.favorite_count
			})
		else:
			return JsonResponse({
				'success': False,
				'error': 'Property not found in saved list'
			}, status=404)
	except Exception as e:
		logger.error(f"Error removing saved property: {str(e)}")
		return JsonResponse({
			'success': False,
			'error': 'An error occurred while removing the property'
		}, status=500)


@login_required
def saved_properties_list(request):
	"""List all saved properties for the current user"""
	try:
		saved_properties = Property.objects.filter(
			favorites__user=request.user
		).select_related('address', 'property_type').prefetch_related(
			'images', 'amenities'
		).distinct().order_by('-favorites__created')
		
		# If AJAX request, return JSON
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			properties_data = []
			for prop in saved_properties:
				primary_image = prop.get_primary_image()
				properties_data.append({
					'id': prop.id,
					'title': prop.title,
					'price': float(prop.price),
					'currency': prop.price_currency,
					'bedrooms': prop.bedrooms,
					'bathrooms': float(prop.bathrooms),
					'square_feet': prop.square_feet,
					'address': str(prop.address),
					'image_url': primary_image.image.url if primary_image else None,
				})
			return JsonResponse({
				'success': True,
				'properties': properties_data
			})
		
		# Regular request, render template
		context = {
			'saved_properties': saved_properties,
			'user': request.user
		}
		return render(request, 'accounts/saved_properties.html', context)
	except Exception as e:
		logger.error(f"Error listing saved properties: {str(e)}")
		messages.error(request, 'An error occurred while loading saved properties')
		return redirect('profile')
