"""
Django settings for sunshine project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import environ
import os
import sys

root = environ.Path(__file__) - 2  # two folders back (/a/b/ - 3 = /)

env = environ.Env(DEBUG=(bool, False),
                  PAYPAL_TEST=(bool, False),
                  USE_MAILCATCHER=(bool, False),
                  SHOW_DEBUG_TOOLBAR=(bool, False),
                  AUTO_BOOK_EMAILS=(list, []),
                  LOCAL=(bool, False),
                  CACHE_BACKEND=(str, 'django.core.cache.backends.memcached.MemcachedCache'),
                  CACHE_LOCATION=(str, '127.0.0.1:11211')
                  )

environ.Env.read_env(root('sunshine/.env'))  # reading .env file
BASE_DIR = root()


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')
if SECRET_KEY is None:  # pragma: no cover
    print("No secret key!")

DEBUG = env('DEBUG')
# when env variable is changed it will be a string, not bool
if str(DEBUG).lower() in ['true', 'on']:  # pragma: no cover
    DEBUG = True
else:  # pragma: no cover
    DEBUG = False

DOMAIN = "sunshinefitness.co.uk"
ALLOWED_HOSTS = [DOMAIN]
if env('LOCAL'):  # pragma: no cover
    ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = (
    'apps.SuitConfig',
    'django.contrib.admin',
    'studioadmin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.humanize',
    'cookielaw',
    'crispy_forms',
    'allauth',
    'allauth.account',
    'django_extensions',
    'bootstrap4',
    'paypal.standard.ipn',
    'debug_toolbar',
    'dynamic_forms',
    'django_object_actions',
    'payments',
    'accounts',
    'timetable',
    'website',
    'activitylog',
    'booking',
    'email_obfuscator',
)


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


CACHES = {
    'default': {
        'BACKEND': env("CACHE_BACKEND"),
        'LOCATION': env("CACHE_LOCATION"),
    }
}


SITE_ID = 1
ROOT_URLCONF = 'sunshine.urls'

WSGI_APPLICATION = 'sunshine.wsgi.application'

DATABASES = {}
DATABASES['default'] = env.db()

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

LANGUAGE_CODE = 'en-GB'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_L10N = True
USE_TZ = True


AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",

    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)


ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_EMAIL_SUBJECT_PREFIX = "[sunshine fitness]"
ACCOUNT_SIGNUP_FORM_CLASS = 'accounts.forms.SignupForm'
ACCOUNT_LOGOUT_REDIRECT_URL ="/about"

ABSOLUTE_URL_OVERRIDES = {
    'auth.user': lambda o: "/users/%s/" % o.username,
}

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'collected-static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [root('templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                # Required by allauth template tags
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.media",
                "booking.context_processors.future_events",
            ),
            'debug': DEBUG,
        },
    },
]

if env('LOCAL'):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_USE_TLS = True
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_HOST_USER = 'sunshinefitnessweb@gmail.com'
    EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', None)
    if EMAIL_HOST_PASSWORD is None:  # pragma: no cover
        print("No email host password provided!")
    EMAIL_PORT = 587
DEFAULT_FROM_EMAIL = 'sunshinefitnessweb@gmail.com'
DEFAULT_STUDIO_EMAIL = 'sunshinefitnessfife@gmail.com'

SUPPORT_EMAIL = 'rebkwok@gmail.com'
AUTO_BOOK_EMAILS = env('AUTO_BOOK_EMAILS')

# MAILCATCHER
if env('USE_MAILCATCHER'):  # pragma: no cover
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = '127.0.0.1'
    EMAIL_HOST_USER = ''
    EMAIL_HOST_PASSWORD = ''
    EMAIL_PORT = 1025
    EMAIL_USE_TLS = False


LOG_FOLDER = env('LOG_FOLDER')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(levelname)s] - %(asctime)s - %(name)s - '
                      '%(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        }
    },
    'handlers': {
        'file_app': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_FOLDER, 'sunshine.log'),
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'mail_admins': {
                'level': 'ERROR',
                'class': 'django.utils.log.AdminEmailHandler',
                'include_html': True,
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file_app', 'mail_admins'],
            'level': 'WARNING',
            'propagate': True,
        },
        'accounts': {
            'handlers': ['console', 'file_app', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'booking': {
            'handlers': ['console', 'file_app', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'payments': {
            'handlers': ['console', 'file_app', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'website': {
            'handlers': ['console', 'file_app', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'timetable': {
            'handlers': ['console', 'file_app', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'gallery': {
            'handlers': ['console', 'file_app', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

ADMINS = [("Becky Smith", SUPPORT_EMAIL)]


from django.contrib import messages
MESSAGE_TAGS = {
    messages.ERROR: 'danger'
}

APPEND_SLASH = True


# DJANGO-PAYPAL
DEFAULT_PAYPAL_EMAIL = env('DEFAULT_PAYPAL_EMAIL')
PAYPAL_TEST = env('PAYPAL_TEST')


def show_toolbar(request):  # pragma: no cover
    return True


if 'test' in sys.argv:  # use local cache for tests
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'test-cache',
        }
    }

if env('SHOW_DEBUG_TOOLBAR') and 'test' not in sys.argv:  # pragma: no cover
    ENABLE_DEBUG_TOOLBAR = True
    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": show_toolbar,
    }

# Activitylogs
EMPTY_JOB_TEXT = ["CRON: auto cancel bookings run; nothing to cancel",]

S3_LOG_BACKUP_PATH = "s3://backups.sunshinestarlet.co.uk/sunshine_activitylogs"
S3_LOG_BACKUP_ROOT_FILENAME = "sunshine_activity_logs_backup"

# for dynamic disclaimer form
CRISPY_TEMPLATE_PACK = 'bootstrap4'
USE_CRISPY = True