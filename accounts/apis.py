from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import account_activation_token
from tracking_analyzer.models import Tracker
from .models import User, UserProfile, PayLink, Portfolio, PortfolioType,  Receipt
from .serializers import UserSerializer, UserProfileSerializer, PayLinkSerializer, PortfolioSerializer, ReceiptSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['post'])
    def signup(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Send activation email
            domain_url = get_current_site(request)
            subject = 'Activate your PayLink Account'
            message = render_to_string('accounts/auth/registration/account_activation_email.html', {
                'user': user,
                'domain': domain_url.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            user.email_user(subject, message)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def resend_activation(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
            if user.is_active:
                return Response({'message': 'Account already active'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            domain_url = get_current_site(request)
            subject = 'Resend: Activate Your PayLink Account'
            message = render_to_string('accounts/auth/registration/account_activation_email.html', {
                'user': user,
                'domain': domain_url.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            user.email_user(subject, message)
            return Response({'message': 'Activation email sent'}, 
                          status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'message': 'User not found'}, 
                          status=status.HTTP_404_NOT_FOUND)

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.action in ['list', 'retrieve']:
            return self.queryset
        return self.queryset.filter(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def check_username(self, request):
        username = request.query_params.get('username')
        exists = UserProfile.objects.filter(username__iexact=username).exists()
        return Response({'username_exists': exists})

class PortfolioViewSet(viewsets.ModelViewSet):
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user.user_profile)

class PayLinkViewSet(viewsets.ModelViewSet):
    queryset = PayLink.objects.all()
    serializer_class = PayLinkSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ReceiptViewSet(viewsets.ModelViewSet):
    queryset = Receipt.objects.all()
    serializer_class = ReceiptSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)