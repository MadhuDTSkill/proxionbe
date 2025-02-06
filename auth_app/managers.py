from django.contrib.auth.models import BaseUserManager
from django.db import transaction
from helper.validators import valid_email
from helper import exceptions


class UserManager(BaseUserManager):
    """Manager for creating users and superusers with validation and atomic transactions."""
     
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise exceptions.SmoothException('The Email field must be set')
        
        if not valid_email(email):
            raise exceptions.SmoothException('Invalid email address')
        
        # Normalize the email address
        email = self.normalize_email(email)
        
        # Using atomic transactions to ensure all operations succeed or roll back entirely.
        with transaction.atomic():
            user = self.model(email=email, **extra_fields)
            user.set_password(password)
            user.save(using=self._db)
            
        return user

    def create_adminuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_admin', True)
        return self.create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        user = self.create_user(email, password, **extra_fields)        
        return user
