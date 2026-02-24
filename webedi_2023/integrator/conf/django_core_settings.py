"""Django settings for WebEDI project."""

import datetime
import logging

from dateutil.relativedelta import relativedelta

from spices import slack_utils
from spices.django3 import coreobjects
from spices.django3.conf import *  # pylint: disable=wildcard-import,unused-wildcard-import
from spices.django3.conf.aws_settings import *  # pylint: disable=wildcard-import,unused-wildcard-import

from apps.utils.piq_core import PIQCoreClient

env = environ.Env()
BASE_DIR = str(
    environ.Path(__file__) - 3
)  # BASE_DIR gives Spices venv path which is wrong.We need BASE_DIR of webedi
PROJECT_DIR = BASE_DIR

INSTALLED_APPS = [
    "admin_auto_filters",
    "corsheaders",
    "dal",
    "dal_select2",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_better_admin_arrayfield.apps.DjangoBetterAdminArrayfieldConfig",
    "django_filters",
    "django_json_widget",
    "rest_framework",
    "modelclone",
    "spices.django3.accounts",
    "spices.django3.base_model",
    "spices.django3.coreobjects",
    "spices.django3.credentials",
    "spices.django3.issues",
    "apps.definitions",
    "apps.jobconfig",
    "apps.runs",
    "integrator",
]

if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]

    DEBUG_TOOLBAR_CONFIG = {
        "SHOW_TOOLBAR_CALLBACK": show_toolbar,
        "INTERCEPT_REDIRECTS": True,
    }

ROOT_URLCONF = "integrator.urls"
ALLOWED_HOSTS = ["*"]
WSGI_APPLICATION = "integrator.wsgi.application"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"],
    "DEFAULT_RENDERER_CLASSES": REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"],
    "EXCEPTION_HANDLER": REST_FRAMEWORK["EXCEPTION_HANDLER"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.utils.paginator.DefaultPagination",
    "PAGE_SIZE": 100,
}

# ############################################
# Logging (Will use Spices LOGGING in Future, as of now causing some trouble)
# ############################################
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}
    },
    "handlers": {
        "console": {
            "level": "DEBUG" if DEBUG else "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "DEBUG", "handlers": ["console"]},
}

# logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
# AWS
AWS_DEFAULT_ACL = None
AWS_BATCH_CLIENT = BOTO3_SESSION.client("batch")
INTEGRATOR_BUCKET = env.str(
    "INTEGRATOR_BUCKET",
    default="com.qubiqle.integrator.dev" if LOCAL_ENV else env.NOTSET,
)
INTEGRATOR_ICON_BUCKET = env.str(
    "INTEGRATOR_ICON_BUCKET",
    default="com.qubiqle.integrator.dev" if LOCAL_ENV else "assets.plateiq.com",
)

# ############################################
# Plate IQ Services
# ############################################
PIQ_DEFAULT_AUTH_COLUMN = "account"
PIQ_API_BASE_URL = env("PIQ_API_BASE_URL", default="")
PIQ_API_TOKEN = env("PIQ_API_TOKEN", default="")
PIQ_CORE_CLIENT = PIQCoreClient(PIQ_API_BASE_URL, PIQ_API_TOKEN)
PIQ_UNKNOWN_RESTAURANT_ID = env.int("PIQ_UNKNOWN_RESTAURANT_ID", default=50)
PIQ_AUTH_ACL_MODEL = env.int("PIQ_AUTH_ACL_MODEL", default="coreobjects.Account")
coreobjects.api_key = PIQ_API_TOKEN

# ############################################
# Feature Flags
# ############################################
DJANGO_ADMIN_ALLOW_DELETE = env.bool("DJANGO_ADMIN_ALLOW_DELETE", default=LOCAL_ENV)

RUN_SUBMIT_TO_AWS_BATCH = env.bool("RUN_SUBMIT_TO_AWS_BATCH", default=False)

DISCOVERED_FILE_PIQ_API_SWITCH = env.bool(
    "DISCOVERED_FILE_PIQ_API_SWITCH", default=(not LOCAL_ENV)
)
DISCOVERED_FILE_PIQ_CREATE_DOC = DISCOVERED_FILE_PIQ_API_SWITCH and env.bool(
    "DISCOVERED_FILE_PIQ_CREATE_DOC", default=(not LOCAL_ENV)
)

PROXY_SERVER = os.environ.get(
    "PROXY_SERVER", "http://ec2-54-161-205-186.compute-1.amazonaws.com:8888"
)
RUN_DEFAULT_START_DATE = datetime.date.today() + relativedelta(days=-30)

for template in TEMPLATES:
    template["DIRS"].append(os.path.join(BASE_DIR, "frontend"))

PIQ_API_URL = os.environ.get("PIQ_API_URL", "https://sandbox.qubiqle.com/")
PIQ_AUTH_SERVER_URL = os.environ.get(
    "PIQ_AUTH_SERVER_URL", "https://sandbox.qubiqle.com/"
)
PIQ_OAUTH_CLIENT_ID = os.environ.get("PIQ_OAUTH_CLIENT_ID", None)
PIQ_OAUTH_CLIENT_SECRET = os.environ.get("PIQ_OAUTH_CLIENT_SECRET", None)

# CORS settings: Allow access to specific domains
CORS_ORIGIN_ALLOW_ALL = env.bool("CORS_ORIGIN_ALLOW_ALL", default=False)
if not CORS_ORIGIN_ALLOW_ALL:
    CORS_ORIGIN_WHITELIST = env.str(
        "CORS_ORIGIN_WHITELIST", default="http://127.0.0.1:8000"
    ).split(",")

DJANGO_ADMIN_SITE_HEADER = "PlateIQ - WebEDI"
if APP_VERSION:
    DJANGO_ADMIN_SITE_HEADER += f" ({APP_VERSION})"
EDI_STEP_FUNCTION_URL = os.environ.get("EDI_STEP_FUNCTION_URL", None)

TEMPLATES = [
    {
        # Template backend to be used, For example Jinja
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Directories for templates
        "DIRS": [os.path.join(PROJECT_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
BILL_PAY_SERVER_URL = os.environ.get(
    "BILL_PAY_SERVER_URL", "https://admin.plateiq.com/admin/"
)
BILL_PAY_CLIENT_TOKEN = os.environ.get("BILL_PAY_CLIENT_TOKEN", None)

IGNORE_RETRYING_FAILED_CHECKRUN = env.bool(
    "IGNORE_RETRYING_FAILED_CHECKRUN", default=True
)
PAPERTRAIL_API_TOKEN = os.environ.get("PAPERTRAIL_API_TOKEN", default=None)
PAPERTRAIL_SYSTEM_ID = os.environ.get("PAPERTRAIL_SYSTEM_ID", default=None)

SLACK_CLIENT = slack_utils.Slack(env.str("SLACK_WEBHOOK_URL", default=None))
SLACK_CHANNEL = "#ops-webedi"
