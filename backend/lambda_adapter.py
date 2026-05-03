import os
from django.core.wsgi import get_wsgi_application
from apig_wsgi import make_lambda_handler

# ระบุชื่อโมดูล Settings ของโปรเจกต์ (แก้ 'core.settings' ให้ตรงกับของคุณ)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# Load Django Application
application = get_wsgi_application()

# Wrap Django App with API Gateway
handler = make_lambda_handler(application)