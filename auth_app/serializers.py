# users/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.password_validation import validate_password

from .models import (
    CustomUser, UserProfile, Members, Collage, District, 
    CollageMembers, CharityPerformance, DistrictCalendar, 
    CollageCalendar, DistrictTimetable, CollageTimetable,
    Writings, Ministry, MinistryInfos, Message
)

CustomUser = get_user_model()

# User Registration Serializer
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password_confirm', 'agree_to_terms']
        extra_kwargs = {
            'username': {'read_only': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        if not attrs.get('agree_to_terms'):
            raise serializers.ValidationError({"agree_to_terms": "You must agree to the terms and conditions."})
            
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = CustomUser.objects.create_user(**validated_data)
        return user

class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=555)
class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            
            if not user:
                raise serializers.ValidationError('Invalid username or password.')
            
            if not user.is_active:
                raise serializers.ValidationError('Account is not active. Please verify your email first.')
            
            # Add user role to the response
            attrs['user'] = user
            # Assuming you have a way to get the user's role
            # This could be from a UserProfile model or directly from the User model
            attrs['role'] = self.get_user_role(user)
            return attrs
        
        raise serializers.ValidationError('Must include "username" and "password".')

    def get_user_role(self, user):
        # Method 1: If role is stored in UserProfile
        try:
            if hasattr(user, 'profile'):
                return user.profile.role  # e.g., 'admin' or 'user'
        except:
            pass
        
        # Method 2: If using Django groups
        try:
            if user.groups.filter(name='admin').exists():
                return 'admin'
            else:
                return 'user'
        except:
            pass
        
        # Method 3: If role is a field on User model
        try:
            return user.role  # if you have a role field on User model
        except:
            pass
        
        # Default fallback
        return 'user'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined']

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = CustomUser.objects.get(email=value)
            return value
        except CustomUser.DoesNotExist:
            return value

class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        try:
            user = CustomUser.objects.get(email=data["email"])
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})

        if hasattr(user, 'verify_otp'):
            is_valid, message = user.verify_otp(data["otp"])
            if not is_valid:
                raise serializers.ValidationError({"otp": message})
        else:
            if not hasattr(user, 'otp') or not hasattr(user, 'otp_expiry'):
                raise serializers.ValidationError({
                    "otp": "OTP system not properly configured. Please request a new OTP."
                })
                
            if user.otp != data["otp"]:
                raise serializers.ValidationError({"otp": "Invalid OTP."})
                
            if user.otp_expiry < timezone.now():
                raise serializers.ValidationError({"otp": "OTP expired."})

        user.otp_verified = True
        user.save()
        return data

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except Exception as e:
            raise serializers.ValidationError(str(e))
        return value

    def validate(self, data):
        email = data["email"]
        otp = data["otp"]
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})

        if not hasattr(user, 'otp'):
            if len(otp) != 6 or not otp.isdigit():
                raise serializers.ValidationError({"otp": "OTP must be 6 digits."})
        else:
            if not user.otp:
                raise serializers.ValidationError({"otp": "No OTP set for this user."})
                
            if user.otp != otp:
                raise serializers.ValidationError({"otp": "Invalid OTP."})
                
            if user.otp_expiry and user.otp_expiry < timezone.now():
                raise serializers.ValidationError({"otp": "OTP expired. Please request a new one."})

        return data

    def save(self):
        user = CustomUser.objects.get(email=self.validated_data["email"])
        new_password = self.validated_data["new_password"]
        
        user.set_password(new_password)
        
        if hasattr(user, 'otp'):
            user.otp = None
            user.otp_expiry = None
        
        user.save()
        return user

# User Profile Serializer
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            'bio', 'phone', 'location', 'profile_picture',
            'facebook_url', 'twitter_url', 'linkedin_url', 'instagram_url',
            'country', 'city_state', 'postal_code', 'tax_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class CustomUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'is_staff', 'is_active', 'date_joined', 'agree_to_terms',
            'profile'
        ]
        read_only_fields = [
            'id', 'username', 'role', 'is_staff', 'date_joined', 
            'agree_to_terms'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name()

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'username', 'email', 'password', 'confirm_password',
            'first_name', 'last_name', 'agree_to_terms'
        ]
        extra_kwargs = {
            'agree_to_terms': {'required': True}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs.pop('confirm_password'):
            raise serializers.ValidationError("Passwords do not match.")
        
        if not attrs.get('agree_to_terms'):
            raise serializers.ValidationError("You must agree to the terms and conditions.")
        
        return attrs
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('confirm_password', None)
        
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.is_active = False
        user.save()
        return user

# FULL USER PROFILE SERIALIZERS
class FullUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'date_joined', 'profile'
        ]
        read_only_fields = ['id', 'username', 'is_active', 'date_joined']

class UserUpdateSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(required=False)

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'profile']
        read_only_fields = ['username', 'email', 'role', 'is_staff', 'is_active', 'date_joined']

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        instance = super().update(instance, validated_data)
        
        if profile_data is not None:
            profile_serializer = UserProfileSerializer(
                instance=instance.profile,
                data=profile_data,
                partial=True
            )
            if profile_serializer.is_valid(raise_exception=True):
                profile_serializer.save()
        
        return instance

# =============================NOTIFICATIONS SERIALIZERS=============================
class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'

# serializers.py
from rest_framework import serializers
from .models import District, Collage

class CollageSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source='district.name', read_only=True)
    
    class Meta:
        model = Collage
        fields = ['id', 'collage_name', 'total_members', 'district', 'district_name']
        read_only_fields = ['id']

class DistrictSerializer(serializers.ModelSerializer):
    collages = CollageSerializer(many=True, read_only=True)
    collages_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = District
        fields = [
            'id', 'name', 'date_created', 'pastor_name', 'number_collages',
            'total_members', 'collages', 'collages_count'
        ]
        read_only_fields = ['id', 'date_created', 'number_collages', 'total_members']


# ####################### MEMBERS #########################
class MembersSerializer(serializers.ModelSerializer):
    user_details = CustomUserSerializer(source='user', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    user_is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    
    class Meta:
        model = Members
        fields = [
            'id', 'user', 'user_details', 'first_name', 'last_name', 'email', 'username',
            'middle_name', 'mobile_number', 'image', 'role', 'date_joined', 
            'is_active', 'user_is_active', 'full_name'
        ]
        read_only_fields = ['id', 'date_joined', 'full_name']


class MembersCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Members
        fields = [
            'id', 'user', 'role', 'middle_name', 'mobile_number', 'image', 'is_active'
        ]
        read_only_fields = ['id']

# ############################ CHARITY SERIALIZER #############################
from rest_framework import serializers
from .models import CharityPerformance

class CharityPerformanceSerializer(serializers.ModelSerializer):
    current_period_balance = serializers.ReadOnlyField()
    period_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CharityPerformance
        fields = [
            'id', 'period_type', 'period_label', 'period_date',
            'donations_received', 'funds_distributed', 
            'current_period_balance', 'period_display'
        ]
        read_only_fields = ['id', 'current_period_balance', 'period_display']
    
    def get_period_display(self, obj):
        return f"{obj.get_period_type_display()} - {obj.period_label}"

# ######################################### COLLAGE ###############################
class CollageDetailSerializer(serializers.ModelSerializer):
    district = DistrictSerializer(read_only=True)
    
    class Meta:
        model = Collage
        fields = ['id', 'collage_name', 'total_members', 'district']

class CollageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collage
        fields = ['id', 'collage_name', 'total_members', 'district']

# ############################ COLLAGE MEMBERS SERIALIZERS #############################
class CollageMembersSerializer(serializers.ModelSerializer):
    # User fields with safe access
    username = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    
    # Member fields with safe access
    middle_name = serializers.SerializerMethodField()
    mobile_number = serializers.SerializerMethodField()
    picture = serializers.SerializerMethodField()
    
    # Related fields with safe access
    district_name = serializers.SerializerMethodField()
    collage_display_name = serializers.SerializerMethodField()

    class Meta:
        model = CollageMembers
        fields = [
            'id',
            # User fields
            'username', 'first_name', 'middle_name', 'last_name', 'email',
            # Member fields
            'mobile_number', 'picture',
            # Collage member fields
            'nationality', 'region', 'collage_name', 'collage_display_name',
            'district_name', 'date_of_birth',
            'education_level', 'your_course', 'your_origin_church',
            'your_origin_district', 'your_secretary_name', 'your_elder_from',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_username(self, obj):
        return obj.user.username if obj.user else None

    def get_first_name(self, obj):
        return obj.user.first_name if obj.user else None

    def get_last_name(self, obj):
        return obj.user.last_name if obj.user else None

    def get_email(self, obj):
        return obj.user.email if obj.user else None

    def get_middle_name(self, obj):
        return obj.member.middle_name if obj.member else None

    def get_mobile_number(self, obj):
        return obj.member.mobile_number if obj.member else None

    def get_picture(self, obj):
        if obj.member and obj.member.image:
            return obj.member.image.url
        return None

    def get_district_name(self, obj):
        return obj.district.name if obj.district else None

    def get_collage_display_name(self, obj):
        return obj.collage_name.collage_name if obj.collage_name else None

class CollageMembersCreateSerializer(serializers.ModelSerializer):
    # All fields are optional for maximum flexibility
    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), 
        required=False,
        allow_null=True
    )
    member = serializers.PrimaryKeyRelatedField(
        queryset=Members.objects.all(),
        required=False,
        allow_null=True
    )
    district = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.all(),
        required=False,
        allow_null=True
    )
    collage_name = serializers.PrimaryKeyRelatedField(
        queryset=Collage.objects.all(),
        required=False,
        allow_null=True
    )
    nationality = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    region = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    education_level = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    your_course = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    your_origin_church = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    your_origin_district = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    your_secretary_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    your_elder_from = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = CollageMembers
        fields = [
            'user', 'member', 'nationality', 'region', 'collage_name',
            'district', 'date_of_birth', 'education_level',
            'your_course', 'your_origin_church', 'your_origin_district',
            'your_secretary_name', 'your_elder_from'
        ]

    def create(self, validated_data):
        return CollageMembers.objects.create(**validated_data)

# ############################ CALENDAR SERIALIZERS #############################
class CollageCalendarSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    document_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CollageCalendar
        fields = [
            'id', 'title', 'description', 'document', 'document_url',
            'academic_year', 'start_date', 'end_date', 'is_active',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_document_url(self, obj):
        if obj.document:
            return obj.document.url
        return None

class DistrictCalendarSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True)
    document_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DistrictCalendar
        fields = [
            'id', 'title', 'description', 'document', 'document_url',
            'district', 'district_name', 'year', 'start_date', 'end_date',
            'is_active', 'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_document_url(self, obj):
        if obj.document:
            return obj.document.url
        return None

# serializers.py
class CollageTimetableSerializer(serializers.ModelSerializer):

    document_url = serializers.SerializerMethodField()
    collage_name = serializers.CharField(source='collage.collage_name', read_only=True)
    
    class Meta:
        model = CollageTimetable
        fields = [
            'id', 'title', 'description', 'document', 'document_url',
            'start_date', 'end_date', 'collage', 'collage_name', 'is_active',
            'created_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_document_url(self, obj):
        if obj.document:
            return obj.document.url
        return None



class DistrictTimetableSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True)
    document_url = serializers.SerializerMethodField()
    
    class Meta:
        model = DistrictTimetable
        fields = [
            'id', 'title', 'description', 'document', 'document_url',
            'district', 'district_name', 'period', 'start_date', 'end_date',
            'is_active', 'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_document_url(self, obj):
        if obj.document:
            return obj.document.url
        return None

# ################################ WRITINGS SERIALIZERS #############################
class WritingsSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    document_url = serializers.SerializerMethodField()
    filename = serializers.CharField(source='get_filename', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    
    class Meta:
        model = Writings
        fields = [
            'id', 'title', 'description', 'document', 'document_url', 'filename',
            'document_type', 'document_type_display', 'is_active',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_document_url(self, obj):
        if obj.document:
            return obj.document.url
        return None

class WritingsCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Writings
        fields = [
            'title', 'description', 'document', 'document_type', 
            'is_active', 'created_by'
        ]

# ======================================== MINISTRIES ===========================
class MinistrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ministry
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class MinistryInfosSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = MinistryInfos
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'download_url']
    
    def get_download_url(self, obj):
        request = self.context.get('request')
        if obj.pdf_report and request:
            return f"{request.build_absolute_uri('/')}api/ministry-infos/{obj.id}/download_report/"
        return None



# ================================// CALENDAR //=====================
from rest_framework import serializers
from .models import CalendarEvent

class CalendarEventSerializer(serializers.ModelSerializer):
    calendar_document_url = serializers.SerializerMethodField()
    
    class Meta:
        model = CalendarEvent
        fields = [
            'id', 'title', 'date', 'description', 'event', 
            'is_done', 'calendar_document', 'calendar_document_url',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'calendar_document_url']
    
    def get_calendar_document_url(self, obj):
        if obj.calendar_document:
            return obj.calendar_document.url
        return None
    

# ================================// VIDEOS //=====================
from rest_framework import serializers
from .models import Video
import os

class VideoSerializer(serializers.ModelSerializer):
    video_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    duration_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Video
        fields = [
            'id', 'title', 'video_file', 'video_url', 'description',
            'duration', 'duration_formatted', 'file_size', 'file_size_mb',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'duration', 'file_size']
    
    def get_video_url(self, obj):
        if obj.video_file:
            return obj.video_file.url
        return None
    
    def get_file_size_mb(self, obj):
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0
    
    def get_duration_formatted(self, obj):
        if obj.duration:
            minutes = int(obj.duration // 60)
            seconds = int(obj.duration % 60)
            return f"{minutes}:{seconds:02d}"
        return "0:00"
    
    def validate_video_file(self, value):
        # Validate file size (max 500MB)
        max_size = 500 * 1024 * 1024  # 500MB
        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 500MB")
        return value
    

    # =================================// IMAGES //==============
# serializers.py
from rest_framework import serializers
from .models import Image
import os
from PIL import Image as PILImage
from io import BytesIO
from django.core.files.base import ContentFile

class ImageSerializer(serializers.ModelSerializer):
    image_url = serializers.ReadOnlyField()
    file_size_mb = serializers.ReadOnlyField()
    dimensions_display = serializers.ReadOnlyField()
    
    class Meta:
        model = Image
        fields = [
            'id', 'title', 'description', 'image_file', 'image_url',
            'file_size', 'file_size_mb', 'file_format', 'dimensions',
            'dimensions_display', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_size', 'file_format', 'dimensions', 
            'created_at', 'updated_at'
        ]
    
    def validate_image_file(self, value):
        """Validate the uploaded image file"""
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Image file too large. Size should not exceed 10MB."
            )
        
        # Check file extensions
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in valid_extensions:
            raise serializers.ValidationError(
                f"Unsupported file extension. Supported formats: {', '.join(valid_extensions)}"
            )
        
        return value
    
    def create(self, validated_data):
        # Create the image instance without user
        instance = super().create(validated_data)
        
        # Process image to get dimensions and file size
        self._process_image(instance)
        
        return instance
    
    def update(self, instance, validated_data):
        # Update the instance
        instance = super().update(instance, validated_data)
        
        # If image file was updated, reprocess it
        if 'image_file' in validated_data:
            self._process_image(instance)
        
        return instance
    
    def _process_image(self, instance):
        """Process image to extract dimensions and file size"""
        try:
            if instance.image_file:
                # Get file size
                instance.file_size = instance.image_file.size
                
                # Get dimensions for raster images (not SVG)
                if instance.file_format not in ['svg']:
                    with PILImage.open(instance.image_file) as img:
                        width, height = img.size
                        instance.dimensions = f"{width}x{height}"
                
                instance.save()
        except Exception as e:
            # If processing fails, still save the instance without dimensions
            print(f"Error processing image: {e}")
            instance.file_size = instance.image_file.size
            instance.save()



# =================================== / / TREASURER //===========================
# serializers.py
from rest_framework import serializers
from .models import RevenueSource, ExpenseCategory, FinancialRecord

class RevenueSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevenueSource
        fields = ['id', 'name', 'description']
        read_only_fields = ['id']

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'description']
        read_only_fields = ['id']

class FinancialRecordSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    category_name = serializers.CharField(source='expense_category.name', read_only=True)
    transaction_type = serializers.SerializerMethodField()
    
    class Meta:
        model = FinancialRecord
        fields = [
            'id', 'date', 'source', 'source_name', 'amount_received',
            'expense_reason', 'expense_category', 'category_name', 'amount_used',
            'notes', 'created_at', 'updated_at', 'transaction_type'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_transaction_type(self, obj):
        if obj.amount_received > 0:
            return 'Revenue'
        elif obj.amount_used > 0:
            return 'Expense'
        return 'Unknown'

class FinancialRecordCreateSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    category_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = FinancialRecord
        fields = [
            'date', 'source', 'source_name', 'amount_received',
            'expense_reason', 'expense_category', 'category_name', 'amount_used', 'notes'
        ]
    
    def validate(self, data):
        # Ensure at least one amount field is provided
        if data.get('amount_received', 0) == 0 and data.get('amount_used', 0) == 0:
            raise serializers.ValidationError({
                "error": "Either amount_received or amount_used must be greater than 0."
            })
        
        # Validate revenue transaction
        if data.get('amount_received', 0) > 0:
            if not data.get('source') and not data.get('source_name'):
                raise serializers.ValidationError({
                    "source": "Source is required for revenue transactions."
                })
        
        # Validate expense transaction
        if data.get('amount_used', 0) > 0:
            if not data.get('expense_reason'):
                raise serializers.ValidationError({
                    "expense_reason": "Expense reason is required for expense transactions."
                })
        
        return data
    
    def create(self, validated_data):
        source_name = validated_data.pop('source_name', None)
        category_name = validated_data.pop('category_name', None)
        
        # Handle source creation if name provided
        if source_name and not validated_data.get('source'):
            source, created = RevenueSource.objects.get_or_create(name=source_name)
            validated_data['source'] = source
        
        # Handle category creation if name provided
        if category_name and not validated_data.get('expense_category'):
            category, created = ExpenseCategory.objects.get_or_create(name=category_name)
            validated_data['expense_category'] = category
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        source_name = validated_data.pop('source_name', None)
        category_name = validated_data.pop('category_name', None)
        
        # Handle source creation if name provided
        if source_name and not validated_data.get('source'):
            source, created = RevenueSource.objects.get_or_create(name=source_name)
            validated_data['source'] = source
        
        # Handle category creation if name provided
        if category_name and not validated_data.get('expense_category'):
            category, created = ExpenseCategory.objects.get_or_create(name=category_name)
            validated_data['expense_category'] = category
        
        return super().update(instance, validated_data)
    

# =========================// LIBRARY //===========================
from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'title', 'description', 'file', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']




# ==============================//   ADD SERIALIZERS //==================
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser

class AddSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'role', 'is_active', 'date_joined', 'agree_to_terms',
            'password', 'password2'
        ]
        read_only_fields = ['id', 'date_joined', 'username']
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'agree_to_terms': {'required': True}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        if not attrs.get('agree_to_terms'):
            raise serializers.ValidationError({"agree_to_terms": "You must agree to the terms."})
            
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        
        # Generate username if not provided
        if not validated_data.get('username'):
            validated_data['username'] = self.generate_username()
            
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        validated_data.pop('password2', None)
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        if password:
            instance.set_password(password)
            
        instance.save()
        return instance
    
    def generate_username(self):
        import uuid
        return f"UDOM-ZONE-{uuid.uuid4().hex[:8].upper()}"


    # ==========================DEACTVATION=================
    # Add to users/serializers.py
class UserDeactivateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
    
    def validate_user_id(self, value):
        try:
            user = CustomUser.objects.get(id=value)
            return value
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("User not found.")

class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'is_staff', 'is_active', 'date_joined'
        ]
        read_only_fields = fields
    
    def get_full_name(self, obj):
        return obj.get_full_name()


# ======================= // APTEC //=================
from rest_framework import serializers
from .models import APTEC, APTEC_MISSION

class APTECSerializer(serializers.ModelSerializer):
    class Meta:
        model = APTEC
        fields = '__all__'

class APTEC_MISSIONSerializer(serializers.ModelSerializer):
    aptec_group_name = serializers.CharField(source='aptec_group.name', read_only=True)
    
    class Meta:
        model = APTEC_MISSION
        fields = '__all__'
