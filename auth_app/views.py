from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login, logout
from .models import CustomUser
from .serializers import UserRegistrationSerializer, UserLoginSerializer, UserSerializer

# views.py
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserRegistrationSerializer

# users/views.py
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
import jwt
from django.conf import settings
from .models import CustomUser
from .serializers import UserRegistrationSerializer, EmailVerificationSerializer, UserSerializer
from .utils import Util

class UserRegistrationAPIView(APIView):
    authentication_classes = []  # disable auth completely
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate verification token using JWT
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken.for_user(user).access_token
            
            # Build verification link
            current_site = get_current_site(request).domain
            relative_link = reverse('email-verify')
            absurl = f'http://{current_site}{relative_link}?token={str(token)}'
            
            # Prepare email data with username
            email_data = {
                'user_first_name': user.first_name,
                'username': user.username,  # This will be your auto-generated UDOM-SDA-username
                'verification_url': absurl,
                'to_email': user.email,
                'email_subject': 'Verify your email address and get your username'
            }
            
            # Send HTML verification email
            Util.send_verification_email(email_data)
            
            return Response({
                'message': 'User registered successfully. Please check your email to verify your account and get your username.',
                'user': UserSerializer(user).data,
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyEmail(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailVerificationSerializer

    def get(self, request):
        token = request.GET.get('token')
        try:
            # Decode token
            payload = jwt.decode(token, options={"verify_signature": False})
            user = CustomUser.objects.get(id=payload['user_id'])
            
            if not user.is_active:
                user.is_active = True
                user.save()
            
            # Redirect to your Vue.js frontend
            from django.http import HttpResponseRedirect
            response = HttpResponseRedirect('http://localhost:3000/profile')
            
            return response
            
        except jwt.ExpiredSignatureError:
            return Response({'error': 'Activation link has expired'}, status=status.HTTP_400_BAD_REQUEST)
        except jwt.exceptions.DecodeError:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)






class UserLoginAPIView(APIView):
    authentication_classes = []  # disable auth completely
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            refresh = RefreshToken.for_user(user)
            
            # Get user role (you need to implement this method)
            user_role = self.get_user_role(user)
            
            return Response({
                'message': 'Login successful',
                'user': {
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_active': user.is_active,
                    'date_joined': user.date_joined,
                    'role': user_role,  # Add role here
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_user_role(self, user):
        # Method 1: If using Django groups
        if user.groups.filter(name='admin').exists():
            return 'admin'
        else:
            return 'user'
        
        # OR Method 2: If you have a custom User model with role field
        # return user.role
        
        # OR Method 3: If you have a UserProfile model
        # try:
        #     return user.profile.role
        # except UserProfile.DoesNotExist:
        #     return 'user'

class UserLogoutAPIView(APIView):
    def post(self, request):
        logout(request)
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)



# PASSWORD RESET AND CHANGE VIEWS CAN BE ADDED HERE AS NEEDED
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import PasswordResetRequestSerializer, OTPVerificationSerializer, PasswordResetSerializer
# views.py
# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .serializers import PasswordResetRequestSerializer
import threading

class EmailThread(threading.Thread):
    def __init__(self, email):
        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        self.email.send()

@method_decorator(csrf_exempt, name='dispatch')
class PasswordResetRequestAPIView(APIView):
    permission_classes = []  # No authentication required
    renderer_classes = [JSONRenderer]  # Force JSON response
    permission_classes=[permissions.AllowAny]

    def send_otp_email(self, user, otp):
        """Send OTP email with HTML template"""
        try:
            # Prepare HTML email with OTP token
            html_content = render_to_string('password_reset_otpl.html', {
                'user_first_name': user.first_name,
                'otp_code': otp,
                'expiry_minutes': 100
            })
            
            # Create plain text version
            text_content = strip_tags(html_content)
            
            # Send email
            email = EmailMultiAlternatives(
                subject="Password Reset OTP - Your App Name",
                body=text_content,
                from_email="noreply@yourapp.com",
                to=[user.email],
            )
            email.attach_alternative(html_content, "text/html")
            EmailThread(email).start()
            return True
        except Exception as e:
            print(f"Email sending error: {e}")
            return False

    def post(self, request):
        print("API View is being called!")  # Debug
        serializer = PasswordResetRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            try:
                from django.contrib.auth import get_user_model
                CustomUser = get_user_model()
                user = CustomUser.objects.get(email=email)
                
                # Generate OTP
                otp = user.generate_otp()
                print(f"Generated OTP for {email}: {otp}")
                
                # Send OTP email with HTML template
                email_sent = self.send_otp_email(user, otp)
                
                if email_sent:
                    return Response(
                        {
                            "success": True, 
                            "message": "OTP has been sent to your email.",
                            "email": email
                        },
                        status=status.HTTP_200_OK
                    )
                else:
                    return Response(
                        {
                            "success": False,
                            "message": "Failed to send OTP email. Please try again."
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
            except CustomUser.DoesNotExist:
                # Return same message for security (don't reveal if email exists)
                return Response(
                    {
                        "success": True, 
                        "message": "If your email is registered, you will receive an OTP shortly."
                    },
                    status=status.HTTP_200_OK
                )
        
        # Return serializer errors
        return Response(
            {
                "success": False,
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .serializers import OTPVerificationSerializer

@method_decorator(csrf_exempt, name='dispatch')
class OTPVerificationAPIView(APIView):
    permission_classes = []
    renderer_classes = [JSONRenderer]  # Force JSON response

    def post(self, request):
        print("OTP Verification API called")  # Debug
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            return Response(
                {
                    "success": True, 
                    "message": "OTP verified successfully.",
                    "email": serializer.validated_data['email']
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {
                "success": False,
                "errors": serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    







    

# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .serializers import PasswordResetSerializer

@method_decorator(csrf_exempt, name='dispatch')
class PasswordResetAPIView(APIView):
    permission_classes = []
    renderer_classes = [JSONRenderer]

    def post(self, request):
        print("=== PASSWORD RESET CONFIRMATION ===")
        print("Request data:", request.data)
        
        serializer = PasswordResetSerializer(data=request.data)
        
        if serializer.is_valid():
            print("Serializer is valid, saving...")
            try:
                user = serializer.save()
                print(f"Password reset successful for: {user.email}")
                return Response(
                    {
                        "success": True, 
                        "message": "Password reset successfully.",
                        "email": user.email
                    },
                    status=status.HTTP_200_OK
                )
            except Exception as e:
                print(f"Error during save: {str(e)}")
                return Response(
                    {
                        "success": False,
                        "message": f"Error during password reset: {str(e)}"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        print("Serializer errors:", serializer.errors)
        return Response(
            {
                "success": False,
                "errors": serializer.errors,
                "message": "Password reset failed. Please check your inputs."
            },
            status=status.HTTP_400_BAD_REQUEST
        )






# users/views.py
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import CustomUser, UserProfile
from .serializers import (
    CustomUserSerializer, UserCreateSerializer
)

class UserListCreateView(generics.ListCreateAPIView):
    """
    View to list all users or create new user (admin only for creation)
    """
    queryset = CustomUser.objects.all()
    permission_classes = [permissions.AllowAny]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return CustomUserSerializer
    
def get_queryset(self):
    user = self.request.user
    # Using the built-in is_staff attribute
    if user.is_staff:
        return user.objects.all()
    else:
        return user.objects.none()













# ========deactivation===============
# Add to users/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import CustomUser
from .serializers import UserListSerializer, UserDeactivateSerializer

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_list(request):
    """Get list of all users"""
    users = CustomUser.objects.all().order_by('-date_joined')
    serializer = UserListSerializer(users, many=True)
    return Response({
        'count': users.count(),
        'results': serializer.data
    })

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def deactivate_user(request):
    """Deactivate a user"""
    serializer = UserDeactivateSerializer(data=request.data)
    
    if serializer.is_valid():
        user_id = serializer.validated_data['user_id']
        
        try:
            user = CustomUser.objects.get(id=user_id)
            
            # Prevent deactivating yourself
            if user.id == request.user.id:
                return Response({
                    'error': 'You cannot deactivate your own account.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Prevent deactivating admin users (optional)
            if user.role == CustomUser.Role.ADMIN:
                return Response({
                    'error': 'Cannot deactivate admin users.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Deactivate the user
            user.is_active = False
            user.save()
            
            return Response({
                'message': f'User {user.username} has been deactivated successfully.',
                'user': UserListSerializer(user).data
            }, status=status.HTTP_200_OK)
            
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def activate_user(request):
    """Activate a user"""
    serializer = UserDeactivateSerializer(data=request.data)
    
    if serializer.is_valid():
        user_id = serializer.validated_data['user_id']
        
        try:
            user = CustomUser.objects.get(id=user_id)
            
            # Activate the user
            user.is_active = True
            user.save()
            
            return Response({
                'message': f'User {user.username} has been activated successfully.',
                'user': UserListSerializer(user).data
            }, status=status.HTTP_200_OK)
            
        except CustomUser.DoesNotExist:
            return Response({
                'error': 'User not found.'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


















# PROFILE CONCERNS

# views.py
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from .models import CustomUser
from .serializers import UserProfileSerializer,UserUpdateSerializer,UserUpdateSerializer
from .permissions import IsOwnerOrAdmin, IsAdmin

from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import CustomUser
from .serializers import FullUserSerializer, UserUpdateSerializer

class UserProfileAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Use FullUserSerializer to include profile data
        serializer = FullUserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        # Use UserUpdateSerializer for updating (which handles profile updates)
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Return updated data with FullUserSerializer
            updated_user = CustomUser.objects.get(id=request.user.id)
            return Response(FullUserSerializer(updated_user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import UserProfile
from .serializers import FullUserSerializer, UserProfileSerializer, UserUpdateSerializer

CustomUser = get_user_model()

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = FullUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        user_id = self.kwargs.get('user_id')
        if user_id and self.request.user.is_staff:  # Use is_staff instead of is_admin
            return get_object_or_404(CustomUser, id=user_id)
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        
        # Handle user data update
        user_serializer = UserUpdateSerializer(
            user, 
            data=request.data, 
            partial=True
        )
        
        # Handle profile data update
        profile_serializer = UserProfileSerializer(
            user.profile,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        
        # Validate both serializers
        user_valid = user_serializer.is_valid()
        profile_valid = profile_serializer.is_valid()
        
        if user_valid and profile_valid:
            user_serializer.save()
            profile_serializer.save()
            
            # Return updated user data
            updated_user = CustomUser.objects.get(id=user.id)
            return Response(
                FullUserSerializer(updated_user, context={'request': request}).data
            )
        else:
            errors = {}
            if not user_valid:
                errors.update(user_serializer.errors)
            if not profile_valid:
                errors.update(profile_serializer.errors)
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

class ProfileUpdateView(generics.UpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:
            # Return full user data after profile update
            user_data = FullUserSerializer(
                request.user, 
                context={'request': request}
            ).data
            response.data = user_data
        return response

class UpdateProfileView(generics.UpdateAPIView):
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        response = super().patch(request, *args, **kwargs)
        if response.status_code == 200:
            # Return the full user data with profile after update
            response.data = FullUserSerializer(self.get_object()).data
        return response
    




class UserListView(generics.ListAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    queryset = CustomUser.objects.all()

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user_data(request):
    """
    API endpoint that returns the current user's data.
    Users can only see their own data unless they're admin.
    """
    user_id = request.query_params.get('user_id')

    if user_id and request.user.is_admin():
        # Admin can view any user's data
        user = get_object_or_404(CustomUser, id=user_id)
    else:
        # Regular users can only view their own data
        user = request.user

    serializer = UserProfileSerializer(user)
    return Response(serializer.data)





# ========================================Notification Settings=================================================
# models.py
# messages/views.py
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework import viewsets, permissions
from .models import Message
from .serializers import MessageSerializer
from django.core.mail import send_mass_mail
from django.contrib.auth import get_user_model

from rest_framework import viewsets, permissions
from django.core.mail import send_mass_mail
from django.contrib.auth import get_user_model
from .models import Message
from .serializers import MessageSerializer
class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all().order_by('-created_at')
    serializer_class = MessageSerializer
    permission_classes = [permissions.AllowAny]  # Allow public access

    def perform_create(self, serializer):
        # Save message (no sender as ForeignKey)
        message = serializer.save()

        # Optionally send email to all users (if you want to keep this part)
        User = get_user_model()
        recipient_list = list(User.objects.values_list('email', flat=True))

        send_mass_mail(((
            f"New Message from {message.sender_name}: {message.subject or '(No subject)'}",
            message.body,
            'no-reply@example.com',  # use fixed sender email
            recipient_list,
        ),), fail_silently=False)



# ##################   FETCH Parent Messages with Replies  #####################
class UnreadMessageCountAPIView(APIView):
    permission_classes = [AllowAny] 
    def get(self, request):
        unread_count = Message.objects.filter(is_read=False).count()
        return Response({
            "new_messages_count": unread_count
        })


class MarkAllAsReadAPIView(APIView):
     permission_classes = [AllowAny] 
def post(self, request):
        Message.objects.filter(is_read=False).update(is_read=True)
        return Response({"message": "All messages marked as read."})

# ###################################     DISTRICT  OF UDOM    #####################################

# views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum
from .models import District, Collage
from .serializers import DistrictSerializer, CollageSerializer

class DistrictViewSet(viewsets.ModelViewSet):
    queryset = District.objects.all().order_by('name')
    serializer_class = DistrictSerializer
    
    def get_queryset(self):
        queryset = District.objects.all().order_by('name')
        # Annotate with real-time counts and sums
        queryset = queryset.annotate(
            collages_count=Count('collages'),
            calculated_total_members=Sum('collages__total_members')
        )
        return queryset
    
    def perform_create(self, serializer):
        instance = serializer.save()
        # Update statistics after creation
        instance.update_statistics()
    
    def perform_update(self, serializer):
        instance = serializer.save()
        # Update statistics after update
        instance.update_statistics()
    
    @action(detail=True, methods=['get'])
    def collages(self, request, pk=None):
        """Get all collages for a specific district"""
        district = self.get_object()
        collages = district.collages.all()
        serializer = CollageSerializer(collages, many=True)
        return Response(serializer.data)

# ######################## MEMBERS  VIEWS##########################
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Members
from .serializers import MembersSerializer, MembersCreateSerializer

class MembersViewSet(viewsets.ModelViewSet):
    queryset = Members.objects.all().select_related('user')
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MembersCreateSerializer
        return MembersSerializer
    
    def get_queryset(self):
        """Optionally filter by user role or other criteria"""
        queryset = super().get_queryset()
        
        # If user is authenticated and not admin, only show their own member profile
        if self.request.user.is_authenticated and not getattr(self.request.user, 'is_admin', False):
            queryset = queryset.filter(user=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        # You can add custom logic here when creating a member
        serializer.save()
    
    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        """Get the current user's member profile"""
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            member = Members.objects.get(user=request.user)
            serializer = MembersSerializer(member)
            return Response(serializer.data)
        except Members.DoesNotExist:
            return Response(
                {"detail": "Member profile not found."},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a member"""
        member = self.get_object()
        member.is_active = True
        member.save()
        return Response({"status": "member activated"})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a member"""
        member = self.get_object()
        member.is_active = False
        member.save()
        return Response({"status": "member deactivated"})
    

# ############################ CHARITY VIEWS #############################
from django.http import FileResponse
from rest_framework import viewsets
from .models import CharityPerformance,Collage,CollageMembers,DistrictCalendar,CollageCalendar,CollageTimetable
from .serializers import CharityPerformanceSerializer,CollageCreateSerializer,CollageDetailSerializer,CollageSerializer,CollageMembers,CollageMembersCreateSerializer,CollageMembersSerializer,CollageCalendarSerializer,DistrictCalendarSerializer,CollageCalendar,CollageTimetable,DistrictTimetable,CollageTimetableSerializer,DistrictTimetableSerializer

from django.http import FileResponse, HttpResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
import pandas as pd
import json
from datetime import datetime
from .models import CharityPerformance
from .serializers import CharityPerformanceSerializer

class CharityPerformanceViewSet(viewsets.ModelViewSet):
    queryset = CharityPerformance.objects.all().order_by('period_date')
    serializer_class = CharityPerformanceSerializer

    def get_queryset(self):
        queryset = CharityPerformance.objects.all().order_by('period_date')
        
        # Filter by period type
        period_type = self.request.query_params.get('period_type')
        if period_type:
            queryset = queryset.filter(period_type=period_type)
        
        # Filter by year
        year = self.request.query_params.get('year')
        if year:
            queryset = queryset.filter(period_date__year=year)
        
        # Filter by period label
        period_label = self.request.query_params.get('period_label')
        if period_label:
            queryset = queryset.filter(period_label=period_label)
        
        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get summary statistics for charity performance"""
        queryset = self.get_queryset()
        
        total_donations = sum([item.donations_received for item in queryset])
        total_distributed = sum([item.funds_distributed for item in queryset])
        net_balance = total_donations - total_distributed
        
        return Response({
            'total_donations': total_donations,
            'total_distributed': total_distributed,
            'net_balance': net_balance,
            'record_count': queryset.count()
        })

    @action(detail=False, methods=['get'])
    def export_excel(self, request):
        """Export charity performance data to Excel"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Create DataFrame
        df = pd.DataFrame(serializer.data)
        
        # Create response
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="charity_performance.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Charity Performance', index=False)
            
            # Add summary sheet
            summary_data = {
                'Metric': ['Total Donations', 'Total Distributed', 'Net Balance', 'Records'],
                'Value': [
                    sum([item.donations_received for item in queryset]),
                    sum([item.funds_distributed for item in queryset]),
                    sum([item.donations_received - item.funds_distributed for item in queryset]),
                    queryset.count()
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
        
        return response

    @action(detail=False, methods=['get'])
    def chart_data(self, request):
        """Get formatted data for charts"""
        queryset = self.get_queryset().order_by('period_date')
        
        # Group by period type for different chart views
        monthly_data = queryset.filter(period_type='monthly')
        quarterly_data = queryset.filter(period_type='quarterly')
        annual_data = queryset.filter(period_type='annually')
        
        chart_data = {
            'monthly': {
                'categories': [item.period_label for item in monthly_data],
                'donations': [float(item.donations_received) for item in monthly_data],
                'distributions': [float(item.funds_distributed) for item in monthly_data],
                'balances': [float(item.donations_received - item.funds_distributed) for item in monthly_data]
            },
            'quarterly': {
                'categories': [item.period_label for item in quarterly_data],
                'donations': [float(item.donations_received) for item in quarterly_data],
                'distributions': [float(item.funds_distributed) for item in quarterly_data],
                'balances': [float(item.donations_received - item.funds_distributed) for item in quarterly_data]
            },
            'annual': {
                'categories': [item.period_label for item in annual_data],
                'donations': [float(item.donations_received) for item in annual_data],
                'distributions': [float(item.funds_distributed) for item in annual_data],
                'balances': [float(item.donations_received - item.funds_distributed) for item in annual_data]
            }
        }
        
        return Response(chart_data)

    @action(detail=False, methods=['get'])
    def available_filters(self, request):
        """Get available filter options"""
        periods = CharityPerformance.objects.values_list('period_type', flat=True).distinct()
        years = CharityPerformance.objects.dates('period_date', 'year').distinct()
        labels = CharityPerformance.objects.values_list('period_label', flat=True).distinct()
        
        return Response({
            'period_types': list(periods),
            'years': [year.year for year in years],
            'period_labels': list(labels)
        })



# ################################ COLLAGE #########################
class CollageViewSet(viewsets.ModelViewSet):
    queryset = Collage.objects.all()
    serializer_class = CollageSerializer
    
    def get_queryset(self):
        queryset = Collage.objects.all()
        district_id = self.request.query_params.get('district_id')
        
        if district_id:
            queryset = queryset.filter(district_id=district_id)
        return queryset
    
    def perform_create(self, serializer):
        instance = serializer.save()
        # District statistics will be updated automatically via save() method
    
    def perform_update(self, serializer):
        instance = serializer.save()
        # District statistics will be updated automatically via save() method
    
    def perform_destroy(self, instance):
        district = instance.district
        instance.delete()
        # District statistics will be updated automatically via delete() method
    
    @action(detail=False, methods=['get'])
    def by_district(self, request):
        district_id = request.query_params.get('district_id')
        if not district_id:
            return Response(
                {"error": "district_id parameter is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        collages = Collage.objects.filter(district_id=district_id)
        serializer = self.get_serializer(collages, many=True)
        return Response(serializer.data)

        # views.py
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

class CollageMembersViewSet(viewsets.ModelViewSet):
    """
    Simple ViewSet for CollageMembers that accepts any JSON data
    No authentication required, all fields optional
    """
    queryset = CollageMembers.objects.all()
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['nationality', 'region', 'collage_name', 'education_level']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CollageMembersCreateSerializer
        return CollageMembersSerializer
    
    def get_queryset(self):
        return CollageMembers.objects.select_related(
            'user', 'member', 'collage_name', 'district'
        ).all()
    
    def create(self, request, *args, **kwargs):
        """
        Create collage member with any data - no validation constraints
        """
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            collage_member = serializer.save()
            read_serializer = CollageMembersSerializer(collage_member)
            return Response(read_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # ADD THIS ACTION FOR DEACTIVATION
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a collage member"""
        try:
            collage_member = self.get_object()
            
            # Option 1: If you have an is_active field
            # collage_member.is_active = False
            # collage_member.save()
            
            # Option 2: If you want to delete instead
            # collage_member.delete()
            
            # Option 3: Custom deactivation logic
            collage_member.status = 'inactive'  # If you have a status field
            collage_member.save()
            
            return Response({
                'status': 'success',
                'message': 'Collage member deactivated successfully',
                'member_id': collage_member.id
            })
            
        except CollageMembers.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Collage member not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error deactivating member: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def nationality_choices(self, request):
        """Get available nationality choices"""
        choices = CollageMembers.NationalityChoices.choices
        return Response(dict(choices))
    
    @action(detail=False, methods=['get'])
    def education_level_choices(self, request):
        """Get available education level choices"""
        choices = CollageMembers.EducationLevelChoices.choices
        return Response(dict(choices))
    
    @action(detail=False, methods=['get'])
    def tanzania_regions(self, request):
        """Get Tanzania regions choices"""
        choices = CollageMembers.TanzaniaRegions.choices
        return Response(dict(choices))
    
    @action(detail=False, methods=['get'])
    def test_endpoint(self, request):
        """Test endpoint to verify API is working"""
        return Response({
            'message': 'Collage Members API is working!',
            'total_members': CollageMembers.objects.count(),
            'endpoints': {
                'list': '/collage-members/',
                'create': '/collage-members/ (POST)',
                'deactivate': '/collage-members/{id}/deactivate/ (POST)',
                'choices': '/collage-members/nationality_choices/'
            }
        })


# views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from django.db import transaction
from .models import CustomUser

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    permission_classes = [permissions.AllowAny]
    
    def get_serializer_class(self):
        from rest_framework import serializers
        
        class UserSerializer(serializers.ModelSerializer):
            class Meta:
                model = CustomUser
                fields = ['id', 'username', 'role', 'first_name', 'last_name', 'email', 'is_active']
                read_only_fields = ['username', 'id']
                
            def validate_role(self, value):
                # Ensure only valid roles are accepted
                if value not in [CustomUser.Role.ADMIN, CustomUser.Role.USER]:
                    raise serializers.ValidationError("Invalid role selected.")
                return value
                
        return UserSerializer

    def create(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                # Get the data from request
                data = request.data.copy()
                
                # Auto-generate username
                last_user = CustomUser.objects.order_by('-id').first()
                next_id = (last_user.id + 1) if last_user else 1
                data['username'] = f"UDOM-ZONE-{next_id:04d}"
                
                # Set default values
                data.setdefault('is_active', False)
                data.setdefault('agree_to_terms', False)
                
                # Handle role-based staff status
                if data.get('role') == CustomUser.Role.ADMIN:
                    data['is_staff'] = True
                else:
                    data['is_staff'] = False
                
                serializer = self.get_serializer(data=data)
                serializer.is_valid(raise_exception=True)
                self.perform_create(serializer)
                
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
                
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )

    def perform_create(self, serializer):
        serializer.save()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()
        
        # Handle role changes for staff status
        if 'role' in data:
            if data['role'] == CustomUser.Role.ADMIN:
                data['is_staff'] = True
            else:
                data['is_staff'] = False
        
        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)



# ======================================== CALENDARS AND TIMETABLES VIEW =================================================
class CollageCalendarViewSet(viewsets.ModelViewSet):
    queryset = CollageCalendar.objects.all()
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['academic_year', 'is_active']
    
    def get_serializer_class(self):
        return CollageCalendarSerializer
    
    def get_queryset(self):
        return CollageCalendar.objects.select_related('created_by').order_by('-created_at')
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download the calendar document"""
        calendar = self.get_object()
        if calendar.document:
            response = FileResponse(calendar.document.open(), as_attachment=True)
            response['Content-Disposition'] = f'attachment; filename="{calendar.document.name}"'
            return response
        return Response({'error': 'Document not found'}, status=404)


class DistrictCalendarViewSet(viewsets.ModelViewSet):
    queryset = DistrictCalendar.objects.all()
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['district', 'year', 'is_active']
    
    def get_serializer_class(self):
        return DistrictCalendarSerializer
    
    def get_queryset(self):
        return DistrictCalendar.objects.select_related('district', 'created_by').order_by('-created_at')
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download the calendar document"""
        calendar = self.get_object()
        if calendar.document:
            response = FileResponse(calendar.document.open(), as_attachment=True)
            response['Content-Disposition'] = f'attachment; filename="{calendar.document.name}"'
            return response
        return Response({'error': 'Document not found'}, status=404)

# views.py
class CollageTimetableViewSet(viewsets.ModelViewSet):
    queryset = CollageTimetable.objects.all()
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'collage']  # Remove academic_year and semester
    
    def get_serializer_class(self):
        return CollageTimetableSerializer
    
    def get_queryset(self):
        queryset = CollageTimetable.objects.select_related('created_by', 'collage').order_by('-created_at')
        
        # Optional: Filter by collage if collage_id is provided in query params
        collage_id = self.request.query_params.get('collage_id')
        if collage_id:
            queryset = queryset.filter(collage_id=collage_id)
            
        return queryset
    
    def perform_create(self, serializer):
        # Automatically set the created_by user
        if self.request.user.is_authenticated:
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download the timetable document"""
        timetable = self.get_object()
        if timetable.document:
            response = FileResponse(timetable.document.open(), as_attachment=True)
            response['Content-Disposition'] = f'attachment; filename="{timetable.document.name}"'
            return response
        return Response({'error': 'Document not found'}, status=404)

class DistrictTimetableViewSet(viewsets.ModelViewSet):
    queryset = DistrictTimetable.objects.all()
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['district', 'period', 'is_active']
    
    def get_serializer_class(self):
        return DistrictTimetableSerializer
    
    def get_queryset(self):
        return DistrictTimetable.objects.select_related('district', 'created_by').order_by('-created_at')
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download the timetable document"""
        timetable = self.get_object()
        if timetable.document:
            response = FileResponse(timetable.document.open(), as_attachment=True)
            response['Content-Disposition'] = f'attachment; filename="{timetable.document.name}"'
            return response
        return Response({'error': 'Document not found'}, status=404)



# ########################    VIEWS FOR WRITINGS  ##########################

from .models import Writings
from .serializers import WritingsSerializer, WritingsCreateSerializer

class WritingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Writings with document upload/download functionality
    """
    queryset = Writings.objects.all()
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['document_type', 'is_active', 'created_by']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return WritingsCreateSerializer
        return WritingsSerializer
    
    def get_queryset(self):
        return Writings.objects.select_related('created_by').order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def document_type_choices(self, request):
        """Get available document type choices"""
        choices = Writings.DocumentType.choices
        return Response(dict(choices))
    
    @action(detail=False, methods=['get'])
    def filter_by_type(self, request):
        """Filter writings by document type"""
        document_type = request.query_params.get('document_type')
        if document_type:
            writings = self.get_queryset().filter(document_type=document_type)
            serializer = self.get_serializer(writings, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download the writing document"""
        writing = self.get_object()
        if writing.document:
            try:
                # Get the filename using your model property
                filename = writing.filename
                if not filename:
                    filename = os.path.basename(writing.document.name)
                
                response = FileResponse(
                    writing.document.open('rb'),
                    as_attachment=True,
                    filename=filename
                )
                response['Content-Type'] = 'application/octet-stream'
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            except Exception as e:
                return Response(
                    {'error': f'Error downloading file: {str(e)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'])
    def download_by_id(self, request):
        """Download document by writing ID via query parameter"""
        writing_id = request.query_params.get('id')
        if not writing_id:
            return Response({'error': 'ID parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        writing = get_object_or_404(Writings, id=writing_id)
        return self.download(request, pk=writing.id)
    
    @action(detail=False, methods=['get'])
    def recent_writings(self, request):
        """Get recent writings (last 10)"""
        writings = self.get_queryset()[:10]
        serializer = self.get_serializer(writings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active_writings(self, request):
        """Get all active writings"""
        writings = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(writings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def spiritual_writings(self, request):
        """Get all spiritual writings"""
        writings = self.get_queryset().filter(document_type='spiritual', is_active=True)
        serializer = self.get_serializer(writings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def education_writings(self, request):
        """Get all education writings"""
        writings = self.get_queryset().filter(document_type='education', is_active=True)
        serializer = self.get_serializer(writings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def philosophy_writings(self, request):
        """Get all philosophy writings"""
        writings = self.get_queryset().filter(document_type='philosophy', is_active=True)
        serializer = self.get_serializer(writings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def economy_writings(self, request):
        """Get all economy writings"""
        writings = self.get_queryset().filter(document_type='economy', is_active=True)
        serializer = self.get_serializer(writings, many=True)
        return Response(serializer.data)
# =================================   MINISTRIES ===================================
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import FileResponse, HttpResponse
import os
from .models import Ministry, MinistryInfos
from .serializers import MinistrySerializer, MinistryInfosSerializer

class MinistryViewSet(viewsets.ModelViewSet):
    queryset = Ministry.objects.all()
    serializer_class = MinistrySerializer
    
    @action(detail=True, methods=['post'])
    def create_info(self, request, pk=None):
        """Create MinistryInfos from a Ministry instance"""
        ministry = self.get_object()
        
        ministry_info_data = {
            'ministry_name': ministry.ministry_name,
            'services': ministry.services,
            'performance': ministry.performance,
            'ministry_members': request.data.get('ministry_members', ''),
            'ministry_assets': request.data.get('ministry_assets', ''),
            'ministry_orders': request.data.get('ministry_orders', ''),
            'costs_per_ministry': request.data.get('costs_per_ministry', 0.00),
            'pdf_report': request.data.get('pdf_report')
        }
        
        serializer = MinistryInfosSerializer(data=ministry_info_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MinistryInfosViewSet(viewsets.ModelViewSet):
    queryset = MinistryInfos.objects.all()
    serializer_class = MinistryInfosSerializer
    
    def get_queryset(self):
        """Optionally filter by ministry name"""
        queryset = MinistryInfos.objects.all()
        ministry_name = self.request.query_params.get('ministry_name', None)
        if ministry_name is not None:
            queryset = queryset.filter(ministry_name__icontains=ministry_name)
        return queryset
    
    @action(detail=True, methods=['get'])
    def download_report(self, request, pk=None):
        """Download the PDF report for a ministry info"""
        ministry_info = self.get_object()
        
        if not ministry_info.pdf_report:
            return Response(
                {'error': 'No PDF report available for this ministry'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Get the file path
            file_path = ministry_info.pdf_report.path
            file_name = os.path.basename(file_path)
            
            # Open the file and create response
            response = FileResponse(
                open(file_path, 'rb'),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="{file_name}"'
            response['Content-Length'] = ministry_info.pdf_report.size
            
            return response
            
        except Exception as e:
            return Response(
                {'error': f'Error downloading file: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def download_all_reports(self, request):
        """Get all ministry infos with download URLs"""
        ministry_infos = self.get_queryset()
        serializer = self.get_serializer(ministry_infos, many=True)
        
        # Add download URL to each ministry info
        data = serializer.data
        for item in data:
            if item['pdf_report']:
                item['download_url'] = f"{request.build_absolute_uri('/')}api/ministry-infos/{item['id']}/download_report/"
            else:
                item['download_url'] = None
                
        return Response(data)






# ================================// CALENDAR //===============================
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import CalendarEvent
from .serializers import CalendarEventSerializer

class CalendarEventViewSet(viewsets.ModelViewSet):
    serializer_class = CalendarEventSerializer
    queryset = CalendarEvent.objects.all()
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        event = self.get_object()
        new_status = request.data.get('is_done')
        
        if new_status not in dict(CalendarEvent.EVENT_STATUS).keys():
            return Response(
                {'error': 'Invalid status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        event.is_done = new_status
        event.save()
        
        serializer = self.get_serializer(event)
        return Response(serializer.data)
    

# =============================// VIDEOS //============================
from django.db import models  # This fixes the undefined variable error
from rest_framework.decorators import action
from rest_framework.response import Response
from moviepy import VideoFileClip
import os
from django.conf import settings
from .models import Video
from .serializers import VideoSerializer
from rest_framework import viewsets  # Make sure this is also imported

class VideoViewSet(viewsets.ModelViewSet):
    serializer_class = VideoSerializer
    queryset = Video.objects.all()
    
    def get_queryset(self):
        queryset = Video.objects.all()
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset
    
    def perform_create(self, serializer):
        video_file = serializer.validated_data['video_file']
        
        # Save the instance first to get the file path
        instance = serializer.save()
        
        try:
            # Calculate duration using moviepy
            video_path = os.path.join(settings.MEDIA_ROOT, instance.video_file.name)
            with VideoFileClip(video_path) as video:
                instance.duration = video.duration
            
            # Get file size
            instance.file_size = video_file.size
            
            instance.save()
        except Exception as e:
            # If duration calculation fails, still save the video
            print(f"Error calculating video duration: {e}")
            instance.file_size = video_file.size
            instance.save()
    
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        video = self.get_object()
        video.status = 'active' if video.status == 'inactive' else 'inactive'
        video.save()
        serializer = self.get_serializer(video)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        total_videos = Video.objects.count()
        active_videos = Video.objects.filter(status='active').count()
        total_size = Video.objects.aggregate(models.Sum('file_size'))['file_size__sum'] or 0
        total_size_mb = round(total_size / (1024 * 1024), 2)
        
        return Response({
            'total_videos': total_videos,
            'active_videos': active_videos,
            'total_size_mb': total_size_mb
        })


# ======================// IMAGES  //====================
# views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import AllowAny
from .models import Image
from .serializers import ImageSerializer
import os

class ImageViewSet(viewsets.ModelViewSet):
    serializer_class = ImageSerializer
    permission_classes = [AllowAny]  # Make API public
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'file_format']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'file_size', 'title']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = Image.objects.all()
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        return queryset
    
    def perform_create(self, serializer):
        """Save without user - already handled in serializer"""
        serializer.save()
    
    @action(detail=True, methods=['post'], permission_classes=[AllowAny])
    def toggle_status(self, request, pk=None):
        """Toggle image status between active and inactive"""
        image = self.get_object()
        image.status = 'active' if image.status == 'inactive' else 'inactive'
        image.save()
        serializer = self.get_serializer(image)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def stats(self, request):
        """Get image statistics"""
        total_images = Image.objects.count()
        active_images = Image.objects.filter(status='active').count()
        total_size = Image.objects.aggregate(Sum('file_size'))['file_size__sum'] or 0
        total_size_mb = round(total_size / (1024 * 1024), 2)
        
        # Format statistics
        format_stats = Image.objects.values('file_format').annotate(
            count=Count('id'),
            total_size=Sum('file_size')
        ).order_by('-count')
        
        return Response({
            'total_images': total_images,
            'active_images': active_images,
            'total_size_mb': total_size_mb,
            'format_stats': format_stats
        })
    
    @action(detail=False, methods=['get'], permission_classes=[AllowAny])
    def formats(self, request):
        """Get available image formats"""
        formats = Image.objects.values_list('file_format', flat=True).distinct()
        return Response({'formats': list(formats)})
    

# =====================================  TREASURER =======================
# views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from datetime import datetime
from django.http import HttpResponse

from .models import RevenueSource, ExpenseCategory, FinancialRecord
from .serializers import (
    RevenueSourceSerializer, 
    ExpenseCategorySerializer, 
    FinancialRecordSerializer,
    FinancialRecordCreateSerializer
)

# ==================== REVENUE SOURCE CRUD ====================
class RevenueSourceViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Revenue Sources
    """
    queryset = RevenueSource.objects.all()
    serializer_class = RevenueSourceSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    filterset_fields = ['name']
    ordering_fields = ['name', 'id']
    ordering = ['name']

# ==================== EXPENSE CATEGORY CRUD ====================
class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Expense Categories
    """
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description']
    filterset_fields = ['name']
    ordering_fields = ['name', 'id']
    ordering = ['name']

# ==================== FINANCIAL RECORD CRUD ====================
class FinancialRecordViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Financial Records with automatic reporting
    """
    queryset = FinancialRecord.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = [
        'source__name', 
        'expense_reason', 
        'expense_category__name',
        'notes'
    ]
    filterset_fields = {
        'date': ['exact', 'gte', 'lte', 'year', 'month'],
        'source': ['exact'],
        'expense_category': ['exact'],
        'amount_received': ['exact', 'gte', 'lte'],
        'amount_used': ['exact', 'gte', 'lte'],
    }
    ordering_fields = ['date', 'amount_received', 'amount_used', 'created_at']
    ordering = ['-date']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return FinancialRecordCreateSerializer
        return FinancialRecordSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by transaction type
        transaction_type = self.request.query_params.get('transaction_type', None)
        if transaction_type == 'revenue':
            queryset = queryset.filter(amount_received__gt=0)
        elif transaction_type == 'expense':
            queryset = queryset.filter(amount_used__gt=0)
        
        return queryset

    # ========== AUTOMATIC REPORTING ENDPOINTS ==========
    
    @action(detail=False, methods=['get'])
    def financial_summary(self, request):
        """
        Get complete financial summary with all calculations
        URL: /api/financial-records/financial_summary/?year=2024&month=12&quarter=4
        """
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        quarter = request.query_params.get('quarter')
        
        try:
            if year:
                year = int(year)
            if month:
                month = int(month)
            if quarter:
                quarter = int(quarter)
        except (TypeError, ValueError):
            year = datetime.now().year
            month = None
            quarter = None
        
        # Calculate all financial metrics
        total_revenue = FinancialRecord.get_total_revenue(year=year, month=month, quarter=quarter)
        total_expenses = FinancialRecord.get_total_expenses(year=year, month=month, quarter=quarter)
        net_income = FinancialRecord.get_net_income(year=year, month=month, quarter=quarter)
        
        # Get transaction counts
        revenue_count = FinancialRecord.objects.filter(amount_received__gt=0)
        expense_count = FinancialRecord.objects.filter(amount_used__gt=0)
        
        if year:
            revenue_count = revenue_count.filter(date__year=year)
            expense_count = expense_count.filter(date__year=year)
        if month:
            revenue_count = revenue_count.filter(date__month=month)
            expense_count = expense_count.filter(date__month=month)
        if quarter:
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            revenue_count = revenue_count.filter(date__month__range=[start_month, end_month])
            expense_count = expense_count.filter(date__month__range=[start_month, end_month])
        
        revenue_count = revenue_count.count()
        expense_count = expense_count.count()
        
        # Calculate profit margin
        profit_margin = (net_income / total_revenue * 100) if total_revenue > 0 else 0
        
        return Response({
            'period': {
                'year': year,
                'month': month,
                'quarter': quarter
            },
            'summary': {
                'total_revenue': float(total_revenue),
                'total_expenses': float(total_expenses),
                'net_income': float(net_income),
                'profit_margin_percent': round(float(profit_margin), 2)
            },
            'transaction_counts': {
                'revenue_transactions': revenue_count,
                'expense_transactions': expense_count,
                'total_transactions': revenue_count + expense_count
            }
        })
    
    @action(detail=False, methods=['get'])
    def quarterly_report(self, request):
        """
        Get detailed quarterly financial report
        URL: /api/financial-records/quarterly_report/?year=2024
        """
        year = request.query_params.get('year', datetime.now().year)
        try:
            year = int(year)
        except (TypeError, ValueError):
            year = datetime.now().year
        
        quarterly_data = FinancialRecord.get_quarterly_summary(year)
        
        # Calculate yearly totals from quarters
        yearly_revenue = sum(q['revenue'] for q in quarterly_data.values())
        yearly_expenses = sum(q['expenses'] for q in quarterly_data.values())
        yearly_net = yearly_revenue - yearly_expenses
        
        return Response({
            'year': year,
            'quarterly_breakdown': quarterly_data,
            'yearly_totals': {
                'total_revenue': float(yearly_revenue),
                'total_expenses': float(yearly_expenses),
                'net_income': float(yearly_net)
            }
        })
    
    @action(detail=False, methods=['get'])
    def monthly_report(self, request):
        """
        Get detailed monthly financial report
        URL: /api/financial-records/monthly_report/?year=2024
        """
        year = request.query_params.get('year', datetime.now().year)
        try:
            year = int(year)
        except (TypeError, ValueError):
            year = datetime.now().year
        
        monthly_data = FinancialRecord.get_monthly_summary(year)
        
        # Calculate quarterly totals from months
        quarterly_totals = {}
        for quarter in range(1, 5):
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            quarter_revenue = sum(
                monthly_data[datetime(year, month, 1).strftime('%B')]['revenue'] 
                for month in range(start_month, end_month + 1)
            )
            quarter_expenses = sum(
                monthly_data[datetime(year, month, 1).strftime('%B')]['expenses'] 
                for month in range(start_month, end_month + 1)
            )
            quarterly_totals[f'Q{quarter}'] = {
                'revenue': float(quarter_revenue),
                'expenses': float(quarter_expenses),
                'net_income': float(quarter_revenue - quarter_expenses)
            }
        
        return Response({
            'year': year,
            'monthly_breakdown': monthly_data,
            'quarterly_totals': quarterly_totals
        })
    
    @action(detail=False, methods=['get'])
    def generate_pdf(self, request):
        """
        Generate comprehensive PDF report
        URL: /api/financial-records/generate_pdf/?type=yearly&year=2024&month=12&quarter=4
        """
        report_type = request.query_params.get('type', 'yearly')
        year = request.query_params.get('year', datetime.now().year)
        month = request.query_params.get('month')
        quarter = request.query_params.get('quarter')
        
        try:
            year = int(year)
            if month:
                month = int(month)
            if quarter:
                quarter = int(quarter)
        except (TypeError, ValueError):
            year = datetime.now().year
            month = None
            quarter = None
        
        try:
            # Call the PDF generation method from the model
            buffer = FinancialRecord.generate_pdf_report(
                report_type=report_type,
                year=year,
                month=month,
                quarter=quarter
            )
            
            filename = f"financial_report_{year}"
            if month:
                filename += f"_{month:02d}"
            if quarter:
                filename += f"_Q{quarter}"
            filename += ".pdf"
            
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
        except Exception as e:
            return Response(
                {"error": f"Failed to generate PDF: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def revenue_analysis(self, request):
        """
        Revenue analysis by source
        URL: /api/financial-records/revenue_analysis/?year=2024
        """
        year = request.query_params.get('year', datetime.now().year)
        try:
            year = int(year)
        except (TypeError, ValueError):
            year = datetime.now().year
        
        # Get revenue by source
        revenue_by_source = FinancialRecord.objects.filter(
            amount_received__gt=0,
            date__year=year
        ).values('source__name').annotate(
            total_revenue=Sum('amount_received'),
            transaction_count=models.Count('id')
        ).order_by('-total_revenue')
        
        return Response({
            'year': year,
            'revenue_by_source': list(revenue_by_source)
        })
    
    @action(detail=False, methods=['get'])
    def expense_analysis(self, request):
        """
        Expense analysis by category
        URL: /api/financial-records/expense_analysis/?year=2024
        """
        year = request.query_params.get('year', datetime.now().year)
        try:
            year = int(year)
        except (TypeError, ValueError):
            year = datetime.now().year
        
        # Get expenses by category
        expenses_by_category = FinancialRecord.objects.filter(
            amount_used__gt=0,
            date__year=year
        ).values('expense_category__name').annotate(
            total_expenses=Sum('amount_used'),
            transaction_count=models.Count('id')
        ).order_by('-total_expenses')
        
        return Response({
            'year': year,
            'expenses_by_category': list(expenses_by_category)
        })

# ==================== DASHBOARD API ====================
class DashboardAPIView(APIView):
    """
    Comprehensive dashboard overview
    URL: /api/dashboard/
    """
    
    def get(self, request):
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Current year statistics
        current_year_revenue = FinancialRecord.get_total_revenue(year=current_year)
        current_year_expenses = FinancialRecord.get_total_expenses(year=current_year)
        current_year_net = FinancialRecord.get_net_income(year=current_year)
        
        # Current month statistics
        current_month_revenue = FinancialRecord.get_total_revenue(year=current_year, month=current_month)
        current_month_expenses = FinancialRecord.get_total_expenses(year=current_year, month=current_month)
        current_month_net = FinancialRecord.get_net_income(year=current_year, month=current_month)
        
        # Previous month statistics
        prev_month = current_month - 1 if current_month > 1 else 12
        prev_month_year = current_year if current_month > 1 else current_year - 1
        prev_month_revenue = FinancialRecord.get_total_revenue(year=prev_month_year, month=prev_month)
        prev_month_expenses = FinancialRecord.get_total_expenses(year=prev_month_year, month=prev_month)
        prev_month_net = FinancialRecord.get_net_income(year=prev_month_year, month=prev_month)
        
        # Recent transactions (last 10)
        recent_transactions = FinancialRecord.objects.all()[:10]
        transaction_serializer = FinancialRecordSerializer(recent_transactions, many=True)
        
        # Monthly data for current year
        monthly_data = FinancialRecord.get_monthly_summary(current_year)
        
        return Response({
            'current_period': {
                'year': current_year,
                'month': current_month
            },
            'current_year': {
                'revenue': float(current_year_revenue),
                'expenses': float(current_year_expenses),
                'net_income': float(current_year_net),
            },
            'current_month': {
                'revenue': float(current_month_revenue),
                'expenses': float(current_month_expenses),
                'net_income': float(current_month_net),
            },
            'previous_month': {
                'revenue': float(prev_month_revenue),
                'expenses': float(prev_month_expenses),
                'net_income': float(prev_month_net),
            },
            'recent_transactions': transaction_serializer.data,
            'monthly_data': monthly_data,
        })



# ==========================// LIBRARY  //=====================
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Document
from .serializers import DocumentSerializer

class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    # Optional: Custom action to download file
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        document = self.get_object()
        response = Response()
        # You can customize the download response here
        return response





# ======================================// APTEC VIEWS //=====================

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from .models import APTEC, APTEC_MISSION
from .serializers import APTECSerializer, APTEC_MISSIONSerializer

class APTECViewSet(viewsets.ModelViewSet):
    queryset = APTEC.objects.all()
    serializer_class = APTECSerializer

class APTEC_MISSIONViewSet(viewsets.ModelViewSet):
    queryset = APTEC_MISSION.objects.all()
    serializer_class = APTEC_MISSIONSerializer
    
    def get_queryset(self):
        queryset = APTEC_MISSION.objects.all()
        aptec_group_id = self.request.query_params.get('aptec_group_id')
        success_reached = self.request.query_params.get('success_reached')
        
        if aptec_group_id:
            queryset = queryset.filter(aptec_group_id=aptec_group_id)
        if success_reached:
            queryset = queryset.filter(success_reached=success_reached)
            
        return queryset
