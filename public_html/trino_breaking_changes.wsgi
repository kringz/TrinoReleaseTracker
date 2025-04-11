#!/usr/bin/env python3
import sys
import logging
import site

# Logging for Apache error log
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

# Path to your Flask app
sys.path.insert(0, '/var/www/xsidebyside.com/app')

# Ensure site-packages from virtual environment are in the path
site_packages = '/var/www/xsidebyside.com/venv/lib/python3.10/site-packages'
if os.path.exists(site_packages):
    if site_packages not in sys.path:
        sys.path.insert(0, site_packages)
else:
    # Try to find the correct Python version
    import glob
    site_packages_paths = glob.glob('/var/www/xsidebyside.com/venv/lib/python3.*/site-packages')
    if site_packages_paths:
        site_packages = site_packages_paths[0]
        if site_packages not in sys.path:
            sys.path.insert(0, site_packages)

# Log the Python path for debugging
logging.info("Python path: %s", sys.path)

# Import and get the Flask application
try:
    from main import app as application
    logging.info("Successfully imported the Flask application")
except ImportError as e:
    logging.error("Error importing application: %s", e)
    # Try alternative import approach
    try:
        logging.info("Attempting alternative import from app.py directly")
        from app import app as application
        logging.info("Successfully imported Flask application from app")
    except ImportError as e2:
        logging.error("Failed alternative import: %s", e2)
        raise

# Production config
application.config['DEBUG'] = False

