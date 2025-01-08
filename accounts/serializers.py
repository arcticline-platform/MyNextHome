from rest_framework import serializers
from .models import User, UserProfile, PayLink, Portfolio, PortfolioType, Receipt

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'is_active')
        read_only_fields = ('is_active',)

class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ('id', 'user', 'username', 'first_name', 'last_name', 'photo', 
                 'cover_photo', 'bio', 'email_confirmed', 'is_active')
        read_only_fields = ('email_confirmed', 'is_active')

class PortfolioTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioType
        fields = '__all__'

class PortfolioSerializer(serializers.ModelSerializer):
    kind_of_business = PortfolioTypeSerializer(read_only=True)
    kind_of_business_id = serializers.PrimaryKeyRelatedField(
        queryset=PortfolioType.objects.filter(is_active=True),
        source='kind_of_business',
        write_only=True
    )

    class Meta:
        model = Portfolio
        fields = '__all__'
        read_only_fields = ('user',)

class PayLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayLink
        fields = '__all__'
        read_only_fields = ('user', 'link_id')

class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = '__all__'
        read_only_fields = ('user',)