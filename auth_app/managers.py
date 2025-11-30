# users/managers.py
from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

class CustomUserManager(BaseUserManager):
    def generate_username(self):
        """
        Generates a unique username starting with UDOM-ZONE- followed by incremental numbers.
        """
        prefix = "UDOM-ZONE-"
        # Find the last used number for this prefix
        last_user = self.model.objects.filter(username__startswith=prefix).order_by('username').last()
        
        if last_user:
            try:
                # Extract the number part and increment
                last_number = int(last_user.username.replace(prefix, ""))
                new_number = last_number + 1
            except (ValueError, TypeError):
                new_number = 1
        else:
            new_number = 1
            
        return f"{prefix}{new_number:04d}"  # Format with leading zeros (0001, 0002, etc.)

    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        
        # Generate unique username before creating user
        if 'username' not in extra_fields or not extra_fields['username']:
            extra_fields['username'] = self.generate_username()
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)