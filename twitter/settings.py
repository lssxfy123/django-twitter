"""
Django settings for twitter project.

Generated by 'django-admin startproject' using Django 3.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.1/ref/settings/
"""

from kombu import Queue
from pathlib import Path
import sys

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'ew02ndil!_8ij!g2xk+*e(6d$)xrj4%c)6%l9=_&0pa9wf_#(6'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# 宿主机看虚拟机的地址
ALLOWED_HOSTS = ['127.0.0.1', '192.168.33.10', 'localhost']

# 虚拟机看宿主机的地址
INTERNAL_IPS = ['10.0.2.2', ]

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # third party
    'rest_framework',
    'debug_toolbar',
    'django_filters',
    'notifications',

    # project apps
    'accounts',
    'tweets',
    'friendships',
    'newsfeeds',
    'comments',
    'likes',
    'inbox',
]

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'EXCEPTION_HANDLER': 'utils.ratelimit.exception_handler',
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

ROOT_URLCONF = 'twitter.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'twitter.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'twitter',
        'HOST': '0.0.0.0',
        'PORT': '3306',
        'USER': 'root',
        'PASSWORD': 'yourpassword',    # 这里是自己下载mysql时候输入两次的那个密码
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = '/static/'

# 设置存储用户上传文件的 storage 用什么系统
# 本地runserver调试时，需要屏蔽掉这行代码，因为没有配置AWS S3
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

# 单元测试不应该产生外部依赖，所以python manage.py test 文件要存储在本地
TESTING = ((" ".join(sys.argv)).find('manage.py test') != -1)
if TESTING:
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

# 当用s3boto3 作为用户上传文件存储时，需要按照你在 AWS 上创建的配置来设置你的 BUCKET_NAME
# 和 REGION_NAME，这个值你可以改成你自己创建的 bucket 的名字和所在的 region
AWS_STORAGE_BUCKET_NAME = 'django-twitter'
AWS_S3_REGION_NAME = 'us-west-1'

# 你还需要在 local_settings.py 中设置你的 AWS_ACCESS_KEY_ID 和 AWS_SECRET_ACCESS_KEY
# 因为这是比较机密的信息，是不适合放在 settings.py 这种共享的配置文件中共享给所有开发者的
# 真实的开发场景下，可以使用 local_settings.py 的方式，或者设置在环境变量里的方式
# 这样这些机密信息就可以只被负责运维的核心开发人员掌控，而非所有开发者，降低泄露风险
# AWS_ACCESS_KEY_ID = 'YOUR_ACCESS_KEY_ID'
# AWS_SECRET_ACCESS_KEY = 'YOUR_SECRET_ACCESS_KEY'


# media 的作用适用于存放被用户上传的文件信息
# 当我们使用默认 FileSystemStorage 作为 DEFAULT_FILE_STORAGE 的时候
# 文件会被默认上传到 MEDIA_ROOT 指定的目录下
# media 和 static 的区别是：
# - static 里通常是 css,js 文件之类的静态代码文件，是用户可以直接访问的代码文件
# - media 里使用户上传的数据文件，而不是代码
MEDIA_ROOT = 'media/'

# https://docs.djangoproject.com/en/3.1/topics/cache/
# use `pip install python-memcached`
# DO NOT pip install memcache or django-memcached
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 86400,
    },
    'testing': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 86400,
        # 尽管配置了default和testing两个cache，但由于LOCATION是相同，本质上访问的是
        # 同一个Memcached，为了区分default和testing中的数据，KEY_PREFIX会自动添加到
        # 存储的key的前面
        'KEY_PREFIX': 'testing',
    },
    'ratelimit': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 86400 * 7,
        'KEY_PREFIX': 'rl',
    }
}

# Redis
# 安装方法: sudo apt-get install redis
# 然后安装 redis 的 python 客户端： pip install redis
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
# 正常运行使用数据库0，测试使用数据库1
REDIS_DB = 0 if TESTING else 1
# 超时时间
REDIS_KEY_EXPIRE_TIME = 7 * 86400  # in seconds
REDIS_LIST_LENGTH_LIMIT = 1000 if not TESTING else 20

# Celery配置选项
# 使用如下命令把worker进程(只执行异步任务的进程，可以不与web server在同一台机器上)
# 单独跑起来
# celery -A twitter worker -l INFO
# celery的broker选择redis
# 测试情形下使用0号database，否则使用2号database，也就是生产环境下使用的消息队列redis
# 数据库不和之前的redis在同一个库中
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/2' if not TESTING\
    else 'redis://127.0.0.1:6379/0'
CELERY_TIMEZONE = 'UTC'
# testing测试时，不要以异步的方式执行任务，而是以同步的方式执行
CELERY_TASK_ALWAYS_EAGER = TESTING

CELERY_QUEUES = (
    Queue('default', routing_key='default'),
    Queue('newsfeeds', routing_key='newsfeeds'),
)

# Rate Limiter
RATELIMIT_USE_CACHE = 'ratelimit'
RATELIMIT_CACHE_PREFIX = 'rl:'   # 避免和其他的 key 冲突
RATELIMIT_ENABLE = not TESTING  # 在某些环境下，比如内部测试等环境下，一般也会关掉

# HBase Database
HBASE_HOST = '127.0.0.1'

try:
    from .local_settings import *
except:
    pass
