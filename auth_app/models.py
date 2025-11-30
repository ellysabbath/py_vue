# users/models.py
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .managers import CustomUserManager

class CustomUser(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Admin')
        USER = 'user', _('User')
    
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        blank=True,
        help_text=_('Auto-generated username starting with UDOM-ZONE-')
    )
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=150)
    last_name = models.CharField(_('last name'), max_length=150)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
        verbose_name=_('Role')
    )
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    agree_to_terms = models.BooleanField(default=False)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    objects = CustomUserManager()

    def __str__(self):
        return self.username

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_short_name(self):
        return self.first_name
    
    def save(self, *args, **kwargs):
        # Auto-set is_staff for admin users
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)
    
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN
    
    # OTP fields
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_expiry = models.DateTimeField(blank=True, null=True)
    otp_verified = models.BooleanField(default=False)
    otp_attempts = models.IntegerField(default=0)
    otp_max_out = models.DateTimeField(blank=True, null=True)
    
    def generate_otp(self):
        import random
        from datetime import timedelta
        from django.utils import timezone
        
        self.otp = str(random.randint(100000, 999999))
        self.otp_expiry = timezone.now() + timedelta(minutes=10)
        self.otp_verified = False
        self.otp_attempts = 0
        self.save()
        return self.otp
    
    def verify_otp(self, entered_otp):
        from django.utils import timezone
        
        if self.otp_max_out and timezone.now() < self.otp_max_out:
            return False, "Maximum OTP attempts reached. Please request a new OTP."
            
        if self.otp_expiry and timezone.now() > self.otp_expiry:
            return False, "OTP has expired. Please request a new OTP."
            
        if self.otp == entered_otp:
            self.otp_verified = True
            self.otp_attempts = 0
            self.save()
            return True, "OTP verified successfully."
        else:
            self.otp_attempts += 1
            if self.otp_attempts >= 3:
                from datetime import timedelta
                self.otp_max_out = timezone.now() + timedelta(minutes=30)
            self.save()
            return False, f"Invalid OTP. {3 - self.otp_attempts} attempts remaining."
        
    # users/models.py - Add this method to CustomUser model
def save(self, *args, **kwargs):
    # Auto-generate username if not provided and this is a new user
    if not self.username and not self.pk:
        last_user = CustomUser.objects.order_by('-id').first()
        next_id = (last_user.id + 1) if last_user else 1
        self.username = f"UDOM-ZONE-{next_id:04d}"
    
    # Auto-set is_staff for admin users
    if self.role == self.Role.ADMIN:
        self.is_staff = True
    else:
        self.is_staff = False
        
    super().save(*args, **kwargs)


class UserProfile(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='profile',
        primary_key=True
    )
    
    # Social media links
    facebook_url = models.URLField(max_length=255, blank=True, null=True)
    twitter_url = models.URLField(max_length=255, blank=True, null=True)
    linkedin_url = models.URLField(max_length=255, blank=True, null=True)
    instagram_url = models.URLField(max_length=255, blank=True, null=True)
    
    # Personal information
    bio = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    
    # Address information
    country = models.CharField(max_length=100, blank=True, null=True)
    city_state = models.CharField(max_length=255, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    
    # Profile image
    profile_picture = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
    
    def __str__(self):
        return f"{self.user.get_full_name()} - Profile"

# Signals
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()




# ===============================NOTIFICATION SETTINGS=================================
class Message(models.Model):
    sender_name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')
    
    is_read = models.BooleanField(default=False)  # NEW FIELD




# ###################################     DISTRICT CHURCH OF UDOM    #####################################
# models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Sum

class District(models.Model):
    name = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Enter the district name (must be unique)"
    )
    date_created = models.DateTimeField(default=timezone.now)
    pastor_name = models.CharField(
        max_length=100,
        help_text="Enter the pastor's full name"
    )
    number_churches = models.PositiveIntegerField(
        default=0,
        help_text="Auto-calculated: Number of churches in this district"
    )
    number_collages = models.PositiveIntegerField(
        default=0,
        help_text="Auto-calculated: Number of collages in this district"
    )
    total_members = models.PositiveIntegerField(
        default=0,
        help_text="Auto-calculated: Total members across all collages"
    )
    
    def __str__(self):
        return self.name
    
    def update_statistics(self, save=True):
        """Update auto-calculated fields without causing recursion"""
        # Use the correct related name 'collages'
        self.number_collages = self.collages.count()
        self.total_members = self.collages.aggregate(
            total=Sum('total_members')
        )['total'] or 0
        
        # Only save if explicitly requested
        if save:
            # Use super().save() to avoid calling our custom save method
            super().save(update_fields=['number_collages', 'total_members'])
    
    def save(self, *args, **kwargs):
        # Call the parent save method first
        super().save(*args, **kwargs)
        # Update statistics after saving (but don't save again in update_statistics)
        self.update_statistics(save=False)
    
    class Meta:
        ordering = ['name']

class Collage(models.Model):
    collage_name = models.CharField(max_length=100)
    total_members = models.PositiveIntegerField(default=0)
    district = models.ForeignKey(
        District, 
        on_delete=models.CASCADE,
        related_name='collages'
    )
    
    @property
    def district_name(self):
        return self.district.name
    
    def __str__(self):
        return self.collage_name
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        # Update district statistics when collage is saved
        self.district.update_statistics()
    
    def delete(self, *args, **kwargs):
        district = self.district
        super().delete(*args, **kwargs)
        # Update district statistics when collage is deleted
        district.update_statistics()

# ############################ MEMBERS ##############################

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class Members(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Admin')
        USER = 'user', _('User')
        
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='member_profile',
        help_text="Select the user account for this member"
    )

    # CORRECTED: Use CharField with choices instead of ForeignKey
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
        help_text="Select the role for this member"
    )
    middle_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Enter the member's middle name (optional)"
    )
    
    mobile_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Enter mobile number"
    )
    
    image = models.ImageField(
        upload_to='members/images/',
        null=True,
        blank=True,
        help_text="Upload a profile picture for the member"
    )
    
    date_joined = models.DateField(
        auto_now_add=True,
        help_text="Date when this member record was created"
    )
    is_active = models.BooleanField(
        default=False,
        help_text="Designates whether this member is currently active"
    )
    
    def __str__(self):
        return self.full_name
    
    @property
    def first_name(self):
        """Get first name from the associated user"""
        return self.user.first_name
    
    @property
    def last_name(self):
        """Get last name from the associated user"""
        return self.user.last_name
    
    @property
    def email(self):
        """Get email from the associated user"""
        return self.user.email
    
    @property
    def full_name(self):
        """Return the full name of the member"""
        if self.middle_name:
            return f"{self.user.first_name} {self.middle_name} {self.user.last_name}"
        return f"{self.user.first_name} {self.user.last_name}"
    
    @property
    def username(self):
        """Get username from the associated user"""
        return self.user.username
    
    class Meta:
        ordering = ['user__first_name', 'user__last_name']
        verbose_name_plural = "Members"
        constraints = [
            models.UniqueConstraint(
                fields=['user'], 
                name='unique_user_membership'
            )
        ]

# ############################ CHARITY  ###########################
from django.db import models
from django.core.exceptions import ValidationError
import datetime
from django.db.models import Sum


class CharityPerformance(models.Model):
    class PeriodType(models.TextChoices):
        MONTHLY = 'monthly', 'Monthly'
        QUARTERLY = 'quarterly', 'Quarterly'
        ANNUALLY = 'annually', 'Annually'

    # Define choices
    MONTH_CHOICES = [
        ('Jan', 'Jan'), ('Feb', 'Feb'), ('Mar', 'Mar'), ('Apr', 'Apr'),
        ('May', 'May'), ('Jun', 'Jun'), ('Jul', 'Jul'), ('Aug', 'Aug'),
        ('Sep', 'Sep'), ('Oct', 'Oct'), ('Nov', 'Nov'), ('Dec', 'Dec'),
    ]

    QUARTER_CHOICES = [
        ('Q1', 'Q1'), ('Q2', 'Q2'), ('Q3', 'Q3'), ('Q4', 'Q4'),
    ]

    # Generate year choices (2020–2060)
    YEAR_CHOICES = [(str(y), str(y)) for y in range(2020, 2061)]

    # Combine all for model-level dropdown display
    PERIOD_LABEL_CHOICES = MONTH_CHOICES + QUARTER_CHOICES + YEAR_CHOICES

    period_type = models.CharField(
        max_length=10,
        choices=PeriodType.choices,
        default=PeriodType.MONTHLY,
        help_text="Defines whether this data is monthly, quarterly, or annually"
    )

    period_label = models.CharField(
        max_length=20,
        choices=PERIOD_LABEL_CHOICES,
        help_text="Display label like 'Jan', 'Q1', or '2024'."
    )

    period_date = models.DateField(
        help_text="Reference date (e.g., Jan 1 for January, first day of quarter/year)."
    )

    donations_received = models.DecimalField(max_digits=12, decimal_places=2)
    funds_distributed = models.DecimalField(max_digits=12, decimal_places=2)

    def clean(self):
        # Validate label based on period_type
        if self.period_type == self.PeriodType.MONTHLY:
            valid = dict(self.MONTH_CHOICES)
        elif self.period_type == self.PeriodType.QUARTERLY:
            valid = dict(self.QUARTER_CHOICES)
        elif self.period_type == self.PeriodType.ANNUALLY:
            valid = dict(self.YEAR_CHOICES)
        else:
            valid = {}

        if self.period_label not in valid:
            raise ValidationError({
                'period_label': f"'{self.period_label}' is not a valid label for {self.period_type}."
            })

    @property
    def total_donations_received(self):
        """
        Calculate the sum of all donations received across all records
        """
        total = CharityPerformance.objects.aggregate(
            total=Sum('donations_received')
        )['total'] or 0
        return total

    @property
    def total_funds_distributed(self):
        """
        Calculate the sum of all funds distributed across all records
        """
        total = CharityPerformance.objects.aggregate(
            total=Sum('funds_distributed')
        )['total'] or 0
        return total

    @property
    def net_funds_balance(self):
        """
        Calculate the difference between total donations received and total funds distributed
        """
        return self.total_donations_received - self.total_funds_distributed

    @property
    def current_period_balance(self):
        """
        Calculate the difference for the current period only
        """
        return self.donations_received - self.funds_distributed

    def __str__(self):
        return f"{self.get_period_type_display()} - {self.period_label}"

    class Meta:
        verbose_name = "Charity Performance"
        verbose_name_plural = "Charity Performance Records"



# ################################### COLLAGES  ########################

class Collage(models.Model):
    collage_name = models.CharField(max_length=100)
    total_members = models.PositiveIntegerField(default=0)
    district = models.ForeignKey(
        District, 
        on_delete=models.CASCADE,
        related_name='collages'  # This should match what you're using in queries
    )
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update the district statistics
        self.district.update_statistics()
    
    def delete(self, *args, **kwargs):
        district = self.district
        super().delete(*args, **kwargs)
        district.update_statistics()




class CollageMembers(models.Model):
    class NationalityChoices(models.TextChoices):
        TANZANIA = 'tanzania', 'Tanzania'
        KENYA = 'kenya', 'Kenya'
        UGANDA = 'uganda', 'Uganda'
        RWANDA = 'rwanda', 'Rwanda'
        BURUNDI = 'burundi', 'Burundi'
        OTHER = 'other', 'Other'
    
    class EducationLevelChoices(models.TextChoices):
        FIRST_YEAR = 'first_year', 'First Year'
        SECOND_YEAR = 'second_year', 'Second Year'
        THIRD_YEAR = 'third_year', 'Third Year'
        FOURTH_YEAR = 'fourth_year', 'Fourth Year'
        FIFTH_YEAR = 'fifth_year', 'Fifth Year'
        SIXTH_YEAR = 'sixth_year', 'Sixth Year'
    
    class TanzaniaRegions(models.TextChoices):
        ARUSHA = 'arusha', 'Arusha'
        DAR_ES_SALAAM = 'dar_es_salaam', 'Dar es Salaam'
        DODOMA = 'dodoma', 'Dodoma'
        GEITA = 'geita', 'Geita'
        IRINGA = 'iringa', 'Iringa'
        KAGERA = 'kagera', 'Kagera'
        KATAVI = 'katavi', 'Katavi'
        KIGOMA = 'kigoma', 'Kigoma'
        KILIMANJARO = 'kilimanjaro', 'Kilimanjaro'
        LINDI = 'lindi', 'Lindi'
        MANYARA = 'manyara', 'Manyara'
        MARA = 'mara', 'Mara'
        MBEYA = 'mbeya', 'Mbeya'
        MOROGORO = 'morogoro', 'Morogoro'
        MTWARA = 'mtwara', 'Mtwara'
        MWANZA = 'mwanza', 'Mwanza'
        NJOMBE = 'njombe', 'Njombe'
        PWANI = 'pwani', 'Pwani'
        RUKWA = 'rukwa', 'Rukwa'
        RUVUMA = 'ruvuma', 'Ruvuma'
        SHINYANGA = 'shinyanga', 'Shinyanga'
        SIMIYU = 'simiyu', 'Simiyu'
        SINGIDA = 'singida', 'Singida'
        TABORA = 'tabora', 'Tabora'
        TANGA = 'tanga', 'Tanga'

    # All fields are optional for maximum flexibility
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='collage_members',
        null=True,
        blank=True
    )
    
    member = models.ForeignKey(
        Members,
        on_delete=models.CASCADE,
        related_name='collage_member_profiles',
        null=True,
        blank=True
    )
    
    nationality = models.CharField(
        max_length=20,
        choices=NationalityChoices.choices,
        blank=True,
        null=True
    )
    
    region = models.CharField(
        max_length=50,
        choices=TanzaniaRegions.choices,
        blank=True,
        null=True
    )
    
    collage_name = models.ForeignKey(
        Collage,
        on_delete=models.CASCADE,
        related_name='members',
        null=True,
        blank=True
    )
    

    
    district = models.ForeignKey(
        District,
        on_delete=models.CASCADE,
        related_name='collage_members',
        null=True,
        blank=True
    )
    
    date_of_birth = models.DateField(null=True, blank=True)
    
    education_level = models.CharField(
        max_length=20,
        choices=EducationLevelChoices.choices,
        blank=True,
        null=True
    )
    
    your_course = models.CharField(max_length=200, blank=True, null=True)
    your_origin_church = models.CharField(max_length=200, blank=True, null=True)
    your_origin_district = models.CharField(max_length=200, blank=True, null=True)
    your_secretary_name = models.CharField(max_length=200, blank=True, null=True)
    your_elder_from = models.CharField(max_length=200, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Collage Member'
        verbose_name_plural = 'Collage Members'
        ordering = ['-created_at']
    
    def __str__(self):
        user_name = self.user.get_full_name() if self.user else "Unknown User"
        collage_name = self.collage_name.collage_name if self.collage_name else "Unknown Collage"
        return f"{user_name} - {collage_name}"













# ########################################    CALENDARS AND TIMETABLES   #########################################
# users/models.py
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class CollageCalendar(models.Model):
    title = models.CharField(max_length=200, help_text="Title of the calendar event/document")
    description = models.TextField(blank=True, null=True, help_text="Description of the calendar")
    document = models.FileField(
        upload_to='calendars/collage/',
        help_text="Upload calendar document (PDF, Word, Excel, etc.)"
    )
    academic_year = models.CharField(max_length=20, help_text="e.g., 2024/2025")
    start_date = models.DateField(help_text="Calendar start date")
    end_date = models.DateField(help_text="Calendar end date")
    is_active = models.BooleanField(default=True, help_text="Is this calendar currently active?")
    
    # Metadata
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_collage_calendars'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Collage Calendar"
        verbose_name_plural = "Collage Calendars"
        ordering = ['-start_date', '-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.academic_year}"

class ChurchCalendar(models.Model):
    title = models.CharField(max_length=200, help_text="Title of the church calendar event/document")
    description = models.TextField(blank=True, null=True, help_text="Description of the calendar")
    document = models.FileField(
        upload_to='calendars/church/',
        help_text="Upload calendar document (PDF, Word, Excel, etc.)"
    )

    year = models.CharField(max_length=10, help_text="e.g., 2024")
    start_date = models.DateField(help_text="Calendar start date")
    end_date = models.DateField(help_text="Calendar end date")
    is_active = models.BooleanField(default=True, help_text="Is this calendar currently active?")
    
    # Metadata
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_church_calendars'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Church Calendar"
        verbose_name_plural = "Church Calendars"
        ordering = ['-start_date', '-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.church.church_name} ({self.year})"

class DistrictCalendar(models.Model):
    title = models.CharField(max_length=200, help_text="Title of the district calendar event/document")
    description = models.TextField(blank=True, null=True, help_text="Description of the calendar")
    document = models.FileField(
        upload_to='calendars/district/',
        help_text="Upload calendar document (PDF, Word, Excel, etc.)"
    )
    district = models.ForeignKey(
        District,
        on_delete=models.CASCADE,
        related_name='calendars',
        help_text="Select the district this calendar belongs to"
    )
    year = models.CharField(max_length=10, help_text="e.g., 2024")
    start_date = models.DateField(help_text="Calendar start date")
    end_date = models.DateField(help_text="Calendar end date")
    is_active = models.BooleanField(default=True, help_text="Is this calendar currently active?")
    
    # Metadata
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_district_calendars'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "District Calendar"
        verbose_name_plural = "District Calendars"
        ordering = ['-start_date', '-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.district.name} ({self.year})"

class CollageTimetable(models.Model):
    title = models.CharField(max_length=200, help_text="Title of the timetable")
    description = models.TextField(blank=True, null=True, help_text="Description of the timetable")
    document = models.FileField(
        upload_to='timetables/collage/',
        help_text="Upload timetable document (PDF, Word, Excel, etc.)"
    )

    start_date = models.DateField(help_text="Timetable start date")
    end_date = models.DateField(help_text="Timetable end date")
    is_active = models.BooleanField(default=True, help_text="Is this timetable currently active?")
    collage=models.ForeignKey(
        Collage,
        on_delete=models.CASCADE,
        related_name='timetables',
        help_text="Select the collage this timetable belongs to"
    )
    # Metadata
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_collage_timetables'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Collage Timetable"
        verbose_name_plural = "Collage Timetables"
        ordering = ['-start_date', '-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.collage.collage_name}"

class ChurchTimetable(models.Model):
    title = models.CharField(max_length=200, help_text="Title of the church timetable")
    description = models.TextField(blank=True, null=True, help_text="Description of the timetable")
    document = models.FileField(
        upload_to='timetables/church/',
        help_text="Upload timetable document (PDF, Word, Excel, etc.)"
    )

    period = models.CharField(
        max_length=50,
        help_text="e.g., Weekly, Monthly, Quarterly, Annual"
    )
    start_date = models.DateField(help_text="Timetable start date")
    end_date = models.DateField(help_text="Timetable end date")
    is_active = models.BooleanField(default=True, help_text="Is this timetable currently active?")
    
    # Metadata
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_church_timetables'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Church Timetable"
        verbose_name_plural = "Church Timetables"
        ordering = ['-start_date', '-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.church.church_name} - {self.period}"

class DistrictTimetable(models.Model):
    title = models.CharField(max_length=200, help_text="Title of the district timetable")
    description = models.TextField(blank=True, null=True, help_text="Description of the timetable")
    document = models.FileField(
        upload_to='timetables/district/',
        help_text="Upload timetable document (PDF, Word, Excel, etc.)"
    )
    district = models.ForeignKey(
        District,
        on_delete=models.CASCADE,
        related_name='timetables',
        help_text="Select the district this timetable belongs to"
    )
    period = models.CharField(
        max_length=50,
        help_text="e.g., Weekly, Monthly, Quarterly, Annual"
    )
    start_date = models.DateField(help_text="Timetable start date")
    end_date = models.DateField(help_text="Timetable end date")
    is_active = models.BooleanField(default=True, help_text="Is this timetable currently active?")
    
    # Metadata
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_district_timetables'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "District Timetable"
        verbose_name_plural = "District Timetables"
        ordering = ['-start_date', '-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.district.name} - {self.period}"




# ###########################################   WRITINGS MODEL   ##########################################
# users/models.py
class Writings(models.Model):
    class DocumentType(models.TextChoices):
        SPIRITUAL = 'spiritual', _('Spiritual')
        EDUCATION = 'education', _('Education')
        PHILOSOPHY = 'philosophy', _('Philosophy')
        ECONOMY = 'economy', _('Economy')
    
    title = models.CharField(
        max_length=200, 
        help_text="Title of the writing/document"
    )
    description = models.TextField(
        blank=True, 
        null=True, 
        help_text="Description of the writing"
    )
    document = models.FileField(
        upload_to='writings/',
        help_text="Upload document (PDF, Word, Excel, etc.)"
    )
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.SPIRITUAL,
        help_text="Select the type of document"
    )
    
    # Metadata
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_writings'
    )
    is_active = models.BooleanField(default=True, help_text="Is this writing currently active?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Writing"
        verbose_name_plural = "Writings"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.get_document_type_display()}"
    
    @property
    def filename(self):
        """Get the filename from the document path"""
        if self.document:
            return (self.document.name)
        return None




# ===========================================  MINISTRIES =================================
from django.db import models
from django.core.validators import MinValueValidator

class Ministry(models.Model):
    ministry_name = models.CharField(max_length=200, unique=True)
    services = models.TextField(help_text="Services offered by the ministry")
    performance = models.TextField(
        max_length=500,
        help_text="Short description of performance",
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ministry"
        verbose_name_plural = "Ministries"
        ordering = ['ministry_name']

    def __str__(self):
        return self.ministry_name

class MinistryInfos(models.Model):
    ministry_name = models.CharField(max_length=200)
    services = models.TextField()
    performance = models.TextField(max_length=500, blank=True, null=True)
    ministry_members = models.TextField(help_text="List of ministry members", blank=True, null=True)
    ministry_assets = models.TextField(help_text="Assets owned by the ministry", blank=True, null=True)
    ministry_orders = models.TextField(help_text="Current orders or projects", blank=True, null=True)
    costs_per_ministry = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0.00,
        help_text="Total costs for this ministry"
    )
    pdf_report = models.FileField(
        upload_to='ministry_reports/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text="PDF report for the ministry"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ministry Info"
        verbose_name_plural = "Ministry Infos"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ministry_name} - Info"



# ====================== // CALENDAR //===============
from django.db import models
from django.core.validators import FileExtensionValidator

class CalendarEvent(models.Model):
    EVENT_STATUS = [
        ('pending', 'Pending'),
        ('on_process', 'On Process'),
        ('done', 'Done'),
    ]
    
    title = models.CharField(max_length=200)
    date = models.DateTimeField()
    description = models.TextField(blank=True, null=True)
    event = models.CharField(max_length=300, blank=True, null=True)
    is_done = models.CharField(max_length=20, choices=EVENT_STATUS, default='pending')
    calendar_document = models.FileField(
        upload_to='calendar_documents/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date']
    
    def __str__(self):
        return f"{self.title} - {self.date}"


# =============================// VIDEOS //=================
from django.db import models
from django.core.validators import FileExtensionValidator

class Video(models.Model):
    VIDEO_STATUS = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    title = models.CharField(max_length=200)
    video_file = models.FileField(
        upload_to='videos/',
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm'])]
    )
    description = models.TextField(blank=True, null=True)
    duration = models.FloatField(blank=True, null=True, help_text="Duration in seconds")
    file_size = models.BigIntegerField(blank=True, null=True, help_text="File size in bytes")
    status = models.CharField(max_length=20, choices=VIDEO_STATUS, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def delete(self, *args, **kwargs):
        # Delete the actual file when the model is deleted
        if self.video_file:
            self.video_file.delete(save=False)
        super().delete(*args, **kwargs)



# ==================// IMAGES //==============
# models.py
from django.db import models
from django.contrib.auth import get_user_model
import os
from uuid import uuid4

User = get_user_model()

def image_upload_path(instance, filename):
    # Generate unique filename using UUID
    ext = filename.split('.')[-1].lower()
    unique_filename = f"{uuid4().hex}.{ext}"
    return f"images/{unique_filename}"

class Image(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image_file = models.ImageField(
        upload_to=image_upload_path,
        max_length=500
    )
    file_size = models.BigIntegerField(null=True, blank=True)  # Size in bytes
    file_format = models.CharField(max_length=10, blank=True)  # jpg, png, etc.
    dimensions = models.CharField(max_length=20, blank=True)  # e.g., "1920x1080"
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='active'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'images'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
           
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Set file format before saving
        if self.image_file:
            self.file_format = self.get_file_extension()
        super().save(*args, **kwargs)
    
    def get_file_extension(self):
        """Get the file extension in lowercase"""
        if self.image_file:
            filename = self.image_file.name
            return filename.split('.')[-1].lower() if '.' in filename else ''
        return ''
    
    @property
    def file_size_mb(self):
        """Return file size in MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0
    
    @property
    def image_url(self):
        """Return absolute image URL"""
        if self.image_file:
            return self.image_file.url
        return ''
    
    @property
    def dimensions_display(self):
        """Return dimensions in readable format"""
        if self.dimensions:
            return f"{self.dimensions}px"
        return "Unknown"





# =================================  TREASURER  ========================
# models.py
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import io
from django.http import HttpResponse

class RevenueSource(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class FinancialRecord(models.Model):
    date = models.DateField(default=timezone.now)
    
    # Revenue fields
    source = models.ForeignKey(RevenueSource, on_delete=models.CASCADE, null=True, blank=True)
    amount_received = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Expense fields
    expense_reason = models.TextField(blank=True)
    expense_category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE, null=True, blank=True)
    amount_used = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        if self.amount_received > 0:
            return f"Revenue: {self.source} - {self.amount_received}Tsh/= on {self.date}"
        else:
            return f"Expense: {self.expense_reason} - {self.amount_used}Tsh/= on {self.date}Tsh/="
    
    @classmethod
    def get_total_revenue(cls, year=None, month=None, quarter=None):
        queryset = cls.objects.filter(amount_received__gt=0)
        
        if year:
            queryset = queryset.filter(date__year=year)
        if month:
            queryset = queryset.filter(date__month=month)
        if quarter:
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            queryset = queryset.filter(date__month__range=[start_month, end_month])
            
        return queryset.aggregate(total=Sum('amount_received'))['total'] or 0
    
    @classmethod
    def get_total_expenses(cls, year=None, month=None, quarter=None):
        queryset = cls.objects.filter(amount_used__gt=0)
        
        if year:
            queryset = queryset.filter(date__year=year)
        if month:
            queryset = queryset.filter(date__month=month)
        if quarter:
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            queryset = queryset.filter(date__month__range=[start_month, end_month])
            
        return queryset.aggregate(total=Sum('amount_used'))['total'] or 0
    
    @classmethod
    def get_net_income(cls, year=None, month=None, quarter=None):
        revenue = cls.get_total_revenue(year, month, quarter)
        expenses = cls.get_total_expenses(year, month, quarter)
        return revenue - expenses
    
    @classmethod
    def get_quarterly_summary(cls, year):
        quarters = {}
        for quarter in range(1, 5):
            revenue = cls.get_total_revenue(year=year, quarter=quarter)
            expenses = cls.get_total_expenses(year=year, quarter=quarter)
            net_income = revenue - expenses
            quarters[f'Q{quarter}'] = {
                'revenue': revenue,
                'expenses': expenses,
                'net_income': net_income
            }
        return quarters
    
    @classmethod
    def get_monthly_summary(cls, year):
        months = {}
        for month in range(1, 13):
            revenue = cls.get_total_revenue(year=year, month=month)
            expenses = cls.get_total_expenses(year=year, month=month)
            net_income = revenue - expenses
            month_name = datetime(year, month, 1).strftime('%B')
            months[month_name] = {
                'revenue': revenue,
                'expenses': expenses,
                'net_income': net_income
            }
        return months
    
    @classmethod
    def generate_pdf_report(cls, report_type='monthly', year=None, month=None, quarter=None):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title = Paragraph("Financial Report", styles['Title'])
        elements.append(title)
        
        # Summary Section
        if report_type == 'monthly' and month:
            summary_data = [
                ['Period', f"{datetime(year, month, 1).strftime('%B %Y')}"],
                ['Total Revenue', f"{cls.get_total_revenue(year=year, month=month):,.2f}Tsh/="],
                ['Total Expenses', f"{cls.get_total_expenses(year=year, month=month):,.2f}Tsh/="],
                ['Net Income', f"{cls.get_net_income(year=year, month=month):,.2f}Tsh/="]
            ]
        elif report_type == 'quarterly' and quarter:
            summary_data = [
                ['Period', f"Q{quarter} {year}"],
                ['Total Revenue', f"{cls.get_total_revenue(year=year, quarter=quarter):,.2f}Tsh/="],
                ['Total Expenses', f"{cls.get_total_expenses(year=year, quarter=quarter):,.2f}Tsh/="],
                ['Net Income', f"{cls.get_net_income(year=year, quarter=quarter):,.2f}Tsh/="]
            ]
        else:  # Yearly
            summary_data = [
                ['Period', f"Year {year}"],
                ['Total Revenue', f"{cls.get_total_revenue(year=year):,.2f}Tsh/="],
                ['Total Expenses', f"{cls.get_total_expenses(year=year):,.2f}Tsh/="],
                ['Net Income', f"{cls.get_net_income(year=year):,.2f}Tsh/="]
            ]
        
        summary_table = Table(summary_data, colWidths=[200, 200])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
        ]))
        elements.append(summary_table)
        
        # Transactions Section
        elements.append(Paragraph("<br/><br/>Transactions:", styles['Heading2']))
        
        transactions = cls.objects.all()
        if year:
            transactions = transactions.filter(date__year=year)
        if month:
            transactions = transactions.filter(date__month=month)
        if quarter:
            start_month = (quarter - 1) * 3 + 1
            end_month = start_month + 2
            transactions = transactions.filter(date__month__range=[start_month, end_month])
        
        transaction_data = [['Date', 'Type', 'Description', 'Amount']]
        for transaction in transactions:
            if transaction.amount_received > 0:
                trans_type = 'Revenue'
                description = str(transaction.source)
                amount = f"{transaction.amount_received:,.2f}Tsh/="
            else:
                trans_type = 'Expense'
                description = transaction.expense_reason
                amount = f"{transaction.amount_used:,.2f}Tsh/="
            
            transaction_data.append([
                transaction.date.strftime('%Y-%m-%d'),
                trans_type,
                description,
                amount
            ])
        
        if len(transaction_data) > 1:
            trans_table = Table(transaction_data, colWidths=[80, 80, 200, 100])
            trans_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(trans_table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer




# ===========================//  LIBRARY  //==================
from django.db import models

class Document(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='documents/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title





# =========================// APTEC  //=================
from django.db import models

class APTEC(models.Model):
    name = models.CharField(max_length=100, verbose_name="APTEC Name")
    mobile = models.CharField(max_length=100, verbose_name="mobile number of member", blank=True, null=True)
    name_collage = models.CharField(max_length=100, verbose_name="College Name")
    name_member = models.CharField(max_length=100, verbose_name="Member Name")
    # total_members = models.PositiveIntegerField(verbose_name="Total Members")
    talent_member = models.TextField(verbose_name="Talent of member", help_text="talent of a member")

    class Meta:
        verbose_name = "APTEC"
        verbose_name_plural = "APTEC Groups"
    
    def __str__(self):
        return f"{self.name} - {self.name_collage}"

class APTEC_MISSION(models.Model):

    
    title_mission = models.CharField(max_length=200, verbose_name="Mission Title")
    description = models.TextField(verbose_name="Mission Description")
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Mission Cost")
    success_expected = models.TextField(default=False, verbose_name="Success Expected")
    location_expected = models.CharField(max_length=700, verbose_name="Expected Location")
    list_members_expected = models.TextField(verbose_name="Expected Members List")
    role_per_member = models.TextField(verbose_name="Role per Member")
    success_reached = models.TextField(
        max_length=7000, 
      
        verbose_name="Success Reached"
    )
    assets_required = models.TextField(verbose_name="Assets Required")
    
    # Foreign key relationship to APTEC (optional - if missions belong to specific APTEC groups)
    aptec_group = models.ForeignKey(
        APTEC, 
        on_delete=models.CASCADE, 
        related_name='missions',
        null=True, 
        blank=True,
        verbose_name="Associated APTEC Group"
    )
    
    class Meta:
        verbose_name = "APTEC Mission"
        verbose_name_plural = "APTEC Missions"
    
    def __str__(self):
        return f"{self.title_mission} - {self.get_success_reached_display()}"