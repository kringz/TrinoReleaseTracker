import logging
import traceback
from flask import render_template, request, jsonify
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import app configuration
from config import create_app, db, logger
from models import TrinoVersion, VersionComparison, ConnectorChange
from scraper import fetch_trino_changes

# Create Flask app
app = create_app()

# Routes
@app.route('/')
def index():
    """Redirect root to breaking changes page"""
    return breaking_changes()

@app.route('/breaking_changes')
def breaking_changes():
    """Page for displaying breaking changes and feature comparisons between Trino versions"""
    versions = [v.version for v in TrinoVersion.query.order_by(TrinoVersion.version.desc()).all()]
    
    # If no versions in database, add some common ones
    if not versions:
        common_versions = ['401', '406', '414', '424', '438', '442', '446', '451', '458', '465', '473', '474']
        for version in common_versions:
            db.session.add(TrinoVersion(version=version))
        db.session.commit()
        versions = common_versions
    
    # Sort versions in descending order (newest first)
    versions.sort(key=lambda x: int(x), reverse=True)
    
    # Get connectors list for the filter dropdown
    connectors = db.session.query(ConnectorChange.connector_name).distinct().all()
    connector_list = [c[0] for c in connectors]
    
    return render_template('breaking_changes.html', versions=versions, connectors=connector_list)

@app.route('/api/connector_changes/<connector_name>')
def connector_changes(connector_name):
    """API endpoint to get all changes for a specific connector"""
    try:
        # Get all changes for the connector from the database
        changes = ConnectorChange.query.filter_by(connector_name=connector_name).all()
        
        result = {
            'connector': connector_name,
            'breaking_changes': [],
            'features': []
        }
        
        for change in changes:
            change_data = {
                'version': change.version,
                'description': change.description,
                'impact': change.impact,
                'date': change.create_date.strftime('%Y-%m-%d') if change.create_date else None
            }
            
            if change.change_type == 'breaking':
                result['breaking_changes'].append(change_data)
            elif change.change_type == 'feature':
                result['features'].append(change_data)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Error fetching connector changes: {str(e)}")
        return jsonify({'error': f"Error fetching connector changes: {str(e)}"}), 500

@app.route('/api/compare_versions', methods=['POST'])
def compare_versions():
    """API endpoint to compare breaking changes and features between two Trino versions"""
    from_version = request.form.get('from_version', '')
    to_version = request.form.get('to_version', '')
    
    if not from_version or not to_version:
        return jsonify({'error': 'Both from_version and to_version are required'}), 400
    
    try:
        # Get the comparison data
        comparison_data = fetch_trino_changes(from_version, to_version, app, db)
        
        # Organize changes by connector
        connector_changes = {}
        
        # Process breaking changes by connector and store in ConnectorChange model
        for change in comparison_data.get('breaking_changes', []):
            version = change.get('version')
            for item in change.get('items', []):
                # Try to identify the connector from the item text
                connector = identify_connector(item)
                if connector not in connector_changes:
                    connector_changes[connector] = {
                        'breaking_changes': [],
                        'new_features': [],
                        'other_changes': []
                    }
                
                connector_changes[connector]['breaking_changes'].append({
                    'version': version,
                    'description': item
                })
                
                # Store in ConnectorChange model for future quick lookup
                try:
                    # Check if this change is already stored
                    existing_change = ConnectorChange.query.filter_by(
                        connector_name=connector,
                        version=version,
                        change_type='breaking',
                        description=item
                    ).first()
                    
                    if not existing_change:
                        new_change = ConnectorChange(
                            connector_name=connector,
                            version=version,
                            change_type='breaking',
                            description=item,
                            impact='high'  # Default impact for breaking changes
                        )
                        db.session.add(new_change)
                except Exception as e:
                    logger.error(f"Error storing connector change: {str(e)}")
        
        # Process new features by connector and store in ConnectorChange model
        for feature in comparison_data.get('new_features', []):
            version = feature.get('version')
            for item in feature.get('items', []):
                connector = identify_connector(item)
                if connector not in connector_changes:
                    connector_changes[connector] = {
                        'breaking_changes': [],
                        'new_features': [],
                        'other_changes': []
                    }
                
                connector_changes[connector]['new_features'].append({
                    'version': version,
                    'description': item
                })
                
                # Store in ConnectorChange model for future quick lookup
                try:
                    # Check if this feature is already stored
                    existing_feature = ConnectorChange.query.filter_by(
                        connector_name=connector,
                        version=version,
                        change_type='feature',
                        description=item
                    ).first()
                    
                    if not existing_feature:
                        new_feature = ConnectorChange(
                            connector_name=connector,
                            version=version,
                            change_type='feature',
                            description=item,
                            impact='medium'  # Default impact for features
                        )
                        db.session.add(new_feature)
                except Exception as e:
                    logger.error(f"Error storing connector feature: {str(e)}")
        
        # Commit all the new changes to the database
        try:
            db.session.commit()
            logger.info(f"Successfully stored connector changes for versions {from_version} to {to_version}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error committing connector changes: {str(e)}")
        
        return jsonify({
            'connectors': connector_changes,
            'from_version': from_version,
            'to_version': to_version
        })
        
    except Exception as e:
        logger.error(f"Error comparing versions: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': f"Error comparing versions: {str(e)}"
        }), 500

def identify_connector(text):
    """Try to extract connector name from text"""
    # List of common Trino connectors
    known_connectors = [
        'bigquery', 'clickhouse', 'delta lake', 'elasticsearch', 'hive', 'iceberg', 
        'jdbc', 'kafka', 'mongodb', 'mysql', 'oracle', 'postgresql', 'redis', 
        'redshift', 'sqlserver', 'snowflake', 'phoenix', 'pinot', 'mariadb',
        'cassandra', 'accumulo', 'druid', 'kudu', 'memory', 'thrift'
    ]
    
    # Check for connector mentions in the text
    text_lower = text.lower()
    
    for connector in known_connectors:
        if connector in text_lower or connector.replace(' ', '') in text_lower:
            # Return standardized connector name (with proper capitalization)
            if connector == 'bigquery':
                return 'BigQuery'
            elif connector == 'clickhouse':
                return 'ClickHouse'
            elif connector == 'delta lake':
                return 'Delta Lake'
            elif connector == 'elasticsearch':
                return 'Elasticsearch'
            elif connector == 'sqlserver':
                return 'SQL Server'
            else:
                # Capitalize first letter of each word
                return ' '.join(word.capitalize() for word in connector.split())
    
    # Check for connector format like "X connector" or "X Connector"
    connector_match = text_lower.split(' connector')[0].split()
    if connector_match and len(connector_match) > 0:
        last_word = connector_match[-1]
        if len(last_word) > 2 and any(c.isalpha() for c in last_word):
            return last_word.capitalize()
    
    # If no specific connector is identified, categorize as General
    return 'General'

# Initialize database
def init_db():
    with app.app_context():
        try:
            # Create the database tables
            db.create_all()
            logger.info("Database tables created")
            
            # Add initial versions if the table is empty
            if TrinoVersion.query.count() == 0:
                common_versions = ['401', '406', '414', '424', '438', '442', '446', '451', '458', '465', '473', '474']
                for version in common_versions:
                    db.session.add(TrinoVersion(version=version))
                db.session.commit()
                logger.info(f"Added initial versions: {common_versions}")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            # Ensure the session is reset in case of error
            db.session.rollback()

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
