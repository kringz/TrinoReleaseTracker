# Trino Breaking Changes - Deployment Guide

This guide explains how to deploy the Trino Breaking Changes application on Ubuntu using Apache2 and mod_wsgi.

## Prerequisites

- Ubuntu server with Apache2 installed
- Python 3.11 or higher
- PostgreSQL database
- Domain name configured to point to your server

## Installation Steps

### 1. Install Required Packages

```bash
# Update package list
sudo apt update

# Install Apache2, WSGI module, PostgreSQL and development libraries
sudo apt install -y apache2 apache2-dev libapache2-mod-wsgi-py3 python3-dev python3-pip postgresql postgresql-contrib libpq-dev

# Enable required Apache modules
sudo a2enmod wsgi
sudo a2enmod rewrite
```

### 2. Create a Python Virtual Environment

```bash
# Navigate to your home directory or desired location
cd /var/www/xsidebyside.com

# Ensure the public_html directory exists
sudo mkdir -p public_html
sudo chown www-data:www-data public_html
cd public_html

# Create and activate virtual environment
sudo -u www-data python3 -m venv venv
source venv/bin/activate
```

### 3. Copy Application Files

Copy all application files to `/var/www/xsidebyside.com/public_html/`. You can use SCP, SFTP, or Git to transfer files.

```bash
# Example using SCP (run this on your local machine)
scp -r * user@your-server:/var/www/xsidebyside.com/public_html/
```

### 4. Install Python Dependencies

```bash
# Navigate to the application directory and activate virtual environment
cd /var/www/xsidebyside.com
# Create the virtual environment in the parent directory, not in public_html
sudo -u www-data python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
# Or install them individually if requirements.txt doesn't exist
pip install flask flask-sqlalchemy psycopg2-binary gunicorn beautifulsoup4 requests trafilatura
```

### 5. Set up PostgreSQL Database

```bash
# Log in to PostgreSQL as postgres user
sudo -u postgres psql

# Create a new database and user
CREATE DATABASE trino_breaking_changes;
CREATE USER trino_user WITH PASSWORD 'strong-password-here';
GRANT ALL PRIVILEGES ON DATABASE trino_breaking_changes TO trino_user;
\q

# Update the DATABASE_URL in the application configuration
# Edit config.py and update DATABASE_URL
# Example: "postgresql://trino_user:strong-password-here@localhost/trino_breaking_changes"
```

### 6. Configure Apache2

Copy the `trino_breaking_changes_apache.conf` file to Apache's sites-available directory:

```bash
sudo cp trino_breaking_changes_apache.conf /etc/apache2/sites-available/xsidebyside.com.conf

# Edit the configuration file to update paths and settings
sudo nano /etc/apache2/sites-available/xsidebyside.com.conf
```

Edit the configuration file to:
- Update `python-home` to point to your virtual environment: `/var/www/xsidebyside.com/venv`
- Update other paths if necessary

Enable the site and disable the default site:

```bash
sudo a2dissite 000-default.conf
sudo a2ensite xsidebyside.com.conf
```

### 7. Set Permissions

Ensure Apache can access all necessary files:

```bash
# Set correct permissions
sudo chown -R www-data:www-data /var/www/xsidebyside.com
sudo chmod -R 755 /var/www/xsidebyside.com
```

### 8. Restart Apache

```bash
sudo systemctl restart apache2
```

### 9. Test the Deployment

Open your browser and navigate to your domain name (http://xsidebyside.com). You should see the Trino Breaking Changes application running.

If you encounter issues, check the Apache error logs:

```bash
sudo tail -f /var/log/apache2/error.log
```

## Troubleshooting

### Directory Listing Appears Instead of Application

If you see a directory listing instead of your application, it means:

1. The WSGI configuration is not correct or not enabled
2. The "Options -Indexes" directive is not applied

Check the following:

- Ensure mod_wsgi is installed and enabled: `sudo a2enmod wsgi`
- Make sure the WSGIScriptAlias directive in your config points to the correct .wsgi file
- Check that Options -Indexes is set in your VirtualHost config
- Verify permissions on the .wsgi file: `sudo chmod 755 /var/www/xsidebyside.com/public_html/trino_breaking_changes.wsgi`

### 500 Internal Server Error

If you get 500 errors:

1. Check the Apache error log: `sudo tail -f /var/log/apache2/error.log`
2. Verify the WSGI file is correctly formatted and permissions are set
3. Make sure the virtual environment contains all required packages
4. Check database connection details are correct

### Database Connection Issues

If the application fails to connect to the database:

1. Verify the DATABASE_URL environment variable or configuration is correct
2. Check PostgreSQL is running: `sudo systemctl status postgresql`
3. Make sure the database user has the correct permissions
4. Test the connection manually using psql: `psql -U trino_user -h localhost -d trino_breaking_changes`