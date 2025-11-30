from django.urls import path
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views
from .views import MessageViewSet
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
from . import views
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'districts', views.DistrictViewSet)
router.register(r'members', views.MembersViewSet, basename='member')
router.register(r'charity-performances', views.CharityPerformanceViewSet, basename='charityperformance')
router.register(r'collages', views.CollageViewSet, basename='collage')
router.register(r'collage-members', views.CollageMembersViewSet, basename='collagemembers')
router.register(r'writings', views.WritingsViewSet, basename='writings')
router.register(r'api/calendar-events', views.CalendarEventViewSet, basename='calendar-events')



# New calendar and timetable routes
router.register(r'collage-calendars', views.CollageCalendarViewSet, basename='collagecalendar')

router.register(r'district-calendars', views.DistrictCalendarViewSet, basename='districtcalendar')
router.register(r'collage-timetables', views.CollageTimetableViewSet, basename='collagetimetable')
router.register(r'district-timetables', views.DistrictTimetableViewSet, basename='districttimetable')

# =========================== FINANCE ==============================
router.register(r'revenue-sources', views.RevenueSourceViewSet)
router.register(r'expense-categories', views.ExpenseCategoryViewSet)
router.register(r'financial-records', views.FinancialRecordViewSet)




# ============================ MINISTRIES ==============================
router.register(r'api/ministries', views.MinistryViewSet)
router.register(r'api/ministry-infos', views.MinistryInfosViewSet)


# ===========================// VIDEOS //==========================
router.register(r'api/videos', views.VideoViewSet, basename='videos')

# =====================/ /  IMAGES  //=====================
router.register(r'api/images', views.ImageViewSet, basename='image')


# ======================= // LIBRARY  //========================
router.register(r'api/documents', views.DocumentViewSet)
router.register(r'users', views.UserViewSet, basename='user')


# ===================// APTEC //=============================
router.register(r'aptec', views.APTECViewSet, basename='aptec')
router.register(r'aptec-mission', views.APTEC_MISSIONViewSet, basename='aptec-mission')


urlpatterns = [
    # Authentication endpoints
    path('register/', views.UserRegistrationAPIView.as_view(), name='register'),
    path('email-verify/', views.VerifyEmail.as_view(), name='email-verify'),
    path('api/register/', views.UserRegistrationAPIView.as_view(), name='register'),
    path('api/login/', views.UserLoginAPIView.as_view(), name='login'),
    path('api/logout/', views.UserLogoutAPIView.as_view(), name='logout'),
    
    # Password reset endpoints
    path('api/password-reset/', views.PasswordResetRequestAPIView.as_view(), name='password-reset-request'),
    path('api/password-reset/verify-otp/', views.OTPVerificationAPIView.as_view(), name='password-reset-verify-otp'),
    path('api/password-reset/confirm/', views.PasswordResetAPIView.as_view(), name='password-reset-confirm'),

    # Profile endpoints
    path('api/profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('api/profile/update/', views.ProfileUpdateView.as_view(), name='update_profile'),
    path('api/profile/<int:user_id>/', views.UserProfileView.as_view(), name='user_profile_by_id'),


    path('current-user/', views.current_user_data, name='current_user_data'),
    # path('users/', views.UserListCreateView.as_view(), name='user_list'),
    # JWT endpoints
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('admin/users/', views.UserListView.as_view(), name='user_list'),

    # Messaging/Notification endpoints
    path('api/messages/unread-count/', views.UnreadMessageCountAPIView.as_view(), name='unread-message-count'),
    path('api/messages/mark-all-read/', views.MarkAllAsReadAPIView.as_view(), name='mark-all-read'),
    path('dashboard/', views.DashboardAPIView.as_view(), name='dashboard'),
   


    path('', include(router.urls)),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
