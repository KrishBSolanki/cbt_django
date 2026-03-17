"""
Django Settings for Exam Paper Generation System
University Lab Examination Question Paper Generation
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-exam-paper-system-change-in-production-xyz-123'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    # Local apps
    'accounts',
    'courses',
    'questions',
    'papers',
    'integration',
    'departments',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'exam_paper_system.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'exam_paper_system.wsgi.application'

# =============================================================================
# MULTI-DATABASE CONFIGURATION
# =============================================================================
DATABASES = {
    # Primary Django database
    'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'exam_paper_system',
            'USER': 'root',
            'PASSWORD': 'root',
            'HOST': '127.0.0.1',
            'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    },
    # Moodle external database (read-only)
   'moodle': {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': 'testcbt',
    'USER': 'cbt_user',
    'PASSWORD': 'Surket',
    'HOST': 'testcbt.itfarmer.in',
    'PORT': '3306',
},
    # TRMS external database (read-only)
    'trms': {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': 'zrtiudp',
    'USER': 'itms_cloud',
    'PASSWORD': 'Ns546dfAYQBT',
    'HOST': '69.62.80.57',
    'PORT': '3306',
    'OPTIONS': {
        'charset': 'utf8mb4',
    },
},
}

DATABASE_ROUTERS = ['integration.routers.MultiDBRouter']

AUTH_USER_MODEL = 'accounts.Faculty'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

# Paper generation settings
PAPER_SETS = ['A', 'B', 'C']
DEFAULT_DIFFICULTY_DISTRIBUTION = {
    'easy': 40,
    'medium': 40,
    'hard': 20,
}
