import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime, timedelta
from config import logger

def version_compare(v1, v2):
    """Compare two version strings"""
    def normalize(v):
        return [int(x) for x in v.split('.')]
    
    v1_parts = normalize(v1)
    v2_parts = normalize(v2)
    
    for i in range(max(len(v1_parts), len(v2_parts))):
        v1_part = v1_parts[i] if i < len(v1_parts) else 0
        v2_part = v2_parts[i] if i < len(v2_parts) else 0
        
        if v1_part < v2_part:
            return -1
        elif v1_part > v2_part:
            return 1
    
    return 0

def fetch_trino_changes(from_version, to_version, app, db):
    """Fetch breaking changes and feature differences from Trino website release notes"""
    # Import models here to avoid circular imports
    from models import VersionComparison
    
    changes = {
        'breaking_changes': [],
        'new_features': [],
        'fixed_issues': [],
        'performance_improvements': []
    }
    
    # Determine version order
    if version_compare(from_version, to_version) > 0:
        # Swap versions if from_version is newer than to_version
        logger.info(f"Swapping from_version {from_version} and to_version {to_version} to maintain chronological order")
        from_version, to_version = to_version, from_version

    # Check if we have a cached result
    with app.app_context():
        try:
            cached_comparison = VersionComparison.query.filter_by(
                from_version=from_version, 
                to_version=to_version
            ).first()
            
            if cached_comparison and cached_comparison.is_valid():
                logger.info(f"Using cached comparison data for {from_version} to {to_version}")
                if cached_comparison.comparison_data:
                    cached_data = cached_comparison.get_comparison_data()
                    if cached_data:
                        logger.info(f"Successfully retrieved cached data for versions {from_version} to {to_version}")
                        return cached_data
                    else:
                        logger.warning(f"Cached data for versions {from_version} to {to_version} was invalid, scraping fresh data")
                else:
                    logger.warning(f"Cached comparison exists but has no data for {from_version} to {to_version}")
            else:
                if cached_comparison:
                    logger.info(f"Cached comparison for {from_version} to {to_version} has expired. Fetching fresh data.")
                else:
                    logger.info(f"No cached comparison found for {from_version} to {to_version}. Fetching new data.")
        except Exception as e:
            logger.error(f"Error checking cached data: {str(e)}")
            # Continue with scraping

    # Get all versions between from_version and to_version
    try:
        versions = []
        for v in range(int(from_version), int(to_version) + 1):
            versions.append(str(v))
        
        logger.info(f"Fetching changes between versions: {from_version} and {to_version}")
        logger.info(f"Processing versions: {versions}")
        
        for version in versions:
            if version == from_version:
                continue  # Skip the starting version
                
            url = f"https://trino.io/docs/current/release/release-{version}.html"
            logger.info(f"Fetching release notes from {url}")
            
            try:
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    logger.warning(f"Failed to fetch release notes for version {version}, status code: {response.status_code}")
                    continue
                    
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract breaking changes
                breaking_section = soup.find(['h2', 'h3'], text=re.compile(r'breaking changes', re.IGNORECASE))
                if breaking_section:
                    breaking_list = []
                    current = breaking_section.find_next(['p', 'ul', 'h2', 'h3'])
                    while current and current.name not in ['h2', 'h3'] or (current.name in ['h2', 'h3'] and not re.search(r'^[a-zA-Z]', current.get_text(strip=True))):
                        if current.name == 'ul':
                            for li in current.find_all('li'):
                                breaking_list.append(li.get_text(strip=True))
                        elif current.name == 'p':
                            text = current.get_text(strip=True)
                            if text and not text.lower().startswith(('note:', 'warning:')):
                                breaking_list.append(text)
                        current = current.find_next(['p', 'ul', 'h2', 'h3'])
                    
                    if breaking_list:
                        changes['breaking_changes'].append({
                            'version': version,
                            'items': breaking_list
                        })
                
                # Extract new features
                feature_section = soup.find(['h2', 'h3'], text=re.compile(r'new features|feature changes', re.IGNORECASE))
                if feature_section:
                    feature_list = []
                    current = feature_section.find_next(['p', 'ul', 'h2', 'h3'])
                    while current and current.name not in ['h2', 'h3'] or (current.name in ['h2', 'h3'] and not re.search(r'^[a-zA-Z]', current.get_text(strip=True))):
                        if current.name == 'ul':
                            for li in current.find_all('li'):
                                feature_list.append(li.get_text(strip=True))
                        current = current.find_next(['p', 'ul', 'h2', 'h3'])
                    
                    if feature_list:
                        changes['new_features'].append({
                            'version': version,
                            'items': feature_list
                        })
                
                # Try to identify connector-specific sections
                connector_sections = soup.find_all(['h2', 'h3'], text=re.compile(r'connector', re.IGNORECASE))
                for section in connector_sections:
                    connector_name = section.get_text(strip=True)
                    # Clean up connector name (e.g., "BigQuery connector" -> "BigQuery")
                    connector_name = re.sub(r'connector', '', connector_name, flags=re.IGNORECASE).strip()
                    
                    connector_changes = []
                    current = section.find_next(['p', 'ul', 'h2', 'h3'])
                    while current and current.name not in ['h2', 'h3'] or (current.name in ['h2', 'h3'] and not re.search(r'^[a-zA-Z]', current.get_text(strip=True))):
                        if current.name == 'ul':
                            for li in current.find_all('li'):
                                connector_changes.append(li.get_text(strip=True))
                        current = current.find_next(['p', 'ul', 'h2', 'h3'])
                    
                    if connector_changes:
                        # Determine if this is a new feature or breaking change
                        # For simplicity, we'll add it to new_features
                        # In a real application, you'd want to analyze the text to categorize it
                        changes['new_features'].append({
                            'version': version,
                            'connector': connector_name,
                            'items': connector_changes
                        })
            
            except Exception as e:
                logger.error(f"Error processing version {version}: {str(e)}")
                continue
        
        # Cache the result
        with app.app_context():
            # Convert to JSON
            cached_data = json.dumps(changes)
            
            # Check if we already have a record
            existing_comparison = VersionComparison.query.filter_by(
                from_version=from_version, 
                to_version=to_version
            ).first()
            
            if existing_comparison:
                existing_comparison.comparison_data = cached_data
                existing_comparison.expire_date = datetime.utcnow() + timedelta(days=30)
            else:
                new_comparison = VersionComparison(
                    from_version=from_version,
                    to_version=to_version,
                    comparison_data=cached_data,
                    expire_date=datetime.utcnow() + timedelta(days=30)
                )
                db.session.add(new_comparison)
            
            db.session.commit()
            logger.info(f"Cached comparison data for {from_version} to {to_version}")
        
        return changes
    except Exception as e:
        logger.error(f"Error fetching changes: {str(e)}")
        return changes
