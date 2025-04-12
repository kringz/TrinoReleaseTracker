
import os
import sys

# Add application directory to python path
app_path = '/var/www/xsidebyside.com/app'
if app_path not in sys.path:
    sys.path.insert(0, app_path)

# Reference the WSGI callable from app.py
from app import app as application
