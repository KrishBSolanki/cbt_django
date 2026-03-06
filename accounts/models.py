"""
Accounts Models - Faculty Authentication System
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class FacultyManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, password, **extra_fields)


class Faculty(AbstractBaseUser, PermissionsMixin):
    """
    Custom Faculty User Model
    Table: dj_faculty
    """
    DEPARTMENT_CHOICES = [
        ('CSE', 'Computer Science & Engineering'),
        ('ECE', 'Electronics & Communication'),
        ('ME', 'Mechanical Engineering'),
        ('CE', 'Civil Engineering'),
        ('EEE', 'Electrical & Electronics'),
        ('IT', 'Information Technology'),
        ('MBA', 'Business Administration'),
        ('MCA', 'Computer Applications'),
        ('OTHER', 'Other'),
    ]

    email = models.EmailField(unique=True, verbose_name='Email Address')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    department = models.CharField(max_length=10, choices=DEPARTMENT_CHOICES, default='CSE')
    designation = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    profile_picture = models.ImageField(upload_to='faculty_profiles/', null=True, blank=True)
    trms_faculty_id = models.IntegerField(null=True, blank=True, help_text='External TRMS faculty ID')

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = FacultyManager()

    class Meta:
        db_table = 'dj_faculty'
        verbose_name = 'Faculty'
        verbose_name_plural = 'Faculty Members'
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    @property
    def initials(self):
        return f"{self.first_name[0]}{self.last_name[0]}".upper() if self.first_name and self.last_name else "FA"
