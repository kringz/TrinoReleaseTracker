#!/bin/bash

# Trino Breaking Changes Deployment Script
# ----------------------------------------
# This script automates the deployment of the Trino Breaking Changes application 
# on Ubuntu with Apache2 and PostgreSQL.

set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Log function
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Check if script is run with sudo
if [ "$EUID" -ne 0 ]; then
    error "Please run this script with sudo: sudo ./deploy.sh"
fi

# Get inputs
read -p "Enter PostgreSQL database name (default: trino_breaking_changes): " DB_NAME
DB_NAME=${DB_NAME:-trino_breaking_changes}
read -p "Enter PostgreSQL username (default: trino_user): " DB_USER
DB_USER=${DB_USER:-trino_user}
read -s -p "Enter PostgreSQL password: " DB_PASSWORD
echo ""
if [ -z "$DB_PASSWORD" ]; then
    error "Database password cannot be empty"
fi
read -p "Enter domain name (default: xsidebyside.com): " DOMAIN_NAME
DOMAIN_NAME=${DOMAIN_NAME:-xsidebyside.com}

# Set paths
APP_PATH="/var/www/$DOMAIN_NAME"
PUBLIC_HTML_PATH="$APP_PATH/public_html"
VENV_PATH="$APP_PATH/venv"

log "Starting deployment of Trino Breaking Changes application..."

# 1. Install Required Packages
log "Installing required packages..."
apt update
apt install -y apache2 apache2-dev libapache2-mod-wsgi-py3 python3-dev python3-pip python3-venv postgresql postgresql-contrib libpq-dev

# Enable required Apache modules
a2enmod wsgi
a2enmod rewrite

# 2. Configure directories
log "Setting up directories..."
mkdir -p $PUBLIC_HTML_PATH
chown -R www-data:www-data $APP_PATH

# 3. Create Python Virtual Environment
log "Creating Python virtual environment..."
python3 -m venv $VENV_PATH
source $VENV_PATH/bin/activate

# 4. Copy configuration files
log "Copying configuration files..."
cp trino_breaking_changes.wsgi $PUBLIC_HTML_PATH/
cp trino_breaking_changes_apache.conf /etc/apache2/sites-available/$DOMAIN_NAME.conf

# 5. Install Python Dependencies
log "Installing Python dependencies..."
if [ -f deployment_requirements.txt ]; then
    pip install -r deployment_requirements.txt
else
    pip install flask flask-sqlalchemy psycopg2-binary gunicorn beautifulsoup4 requests trafilatura
fi

# 6. Copy application files to public_html
log "Copying application files..."
for file in app.py config.py main.py models.py scraper.py; do
    if [ -f "$file" ]; then
        cp $file $PUBLIC_HTML_PATH/
    else
        warning "File $file not found, skipping."
    fi
done

# Copy directories if they exist
for dir in static templates; do
    if [ -d "$dir" ]; then
        cp -r $dir $PUBLIC_HTML_PATH/
    else
        warning "Directory $dir not found, skipping."
    fi
done

# 7. Set up PostgreSQL Database
log "Setting up PostgreSQL database..."
# Check if the role already exists
if sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1; then
    warning "PostgreSQL user $DB_USER already exists, skipping user creation."
else
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
fi

# Check if the database already exists
if sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw $DB_NAME; then
    warning "PostgreSQL database $DB_NAME already exists, skipping database creation."
else
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
fi

# 8. Update database configuration
log "Updating database configuration..."
# Create a database URL
DB_URL="postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME"

# Update the config.py file to use the correct DATABASE_URL
if [ -f "$PUBLIC_HTML_PATH/config.py" ]; then
    sed -i "s|app.config\[\"SQLALCHEMY_DATABASE_URI\"\] = os.environ.get(\"DATABASE_URL\")|app.config\[\"SQLALCHEMY_DATABASE_URI\"\] = \"$DB_URL\"|g" $PUBLIC_HTML_PATH/config.py
    log "Updated DATABASE_URL in config.py"
else
    warning "config.py not found, couldn't update DATABASE_URL."
fi

# 9. Set permissions
log "Setting permissions..."
chown -R www-data:www-data $APP_PATH
chmod -R 755 $APP_PATH
chmod 755 $PUBLIC_HTML_PATH/trino_breaking_changes.wsgi

# 10. Configure Apache
log "Configuring Apache..."
# Disable default site if it's enabled
if [ -L /etc/apache2/sites-enabled/000-default.conf ]; then
    a2dissite 000-default.conf
fi

# Enable the application site
a2ensite $DOMAIN_NAME.conf

# Create .htaccess file to disable directory listing
echo "Options -Indexes" > $PUBLIC_HTML_PATH/.htaccess
chmod 644 $PUBLIC_HTML_PATH/.htaccess

# 11. Restart Apache
log "Restarting Apache..."
systemctl restart apache2

# 12. Final notes
log "Deployment completed successfully!"
log "Your Trino Breaking Changes application should now be available at: http://$DOMAIN_NAME"
log "If you encounter any issues, check the Apache error log:"
log "  sudo tail -f /var/log/apache2/error.log"

exit 0
