from datetime import datetime, timedelta
import json
from config import db

# Define database models
class TrinoVersion(db.Model):
    """Model for tracking available Trino versions"""
    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(20), unique=True, nullable=False)
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TrinoVersion {self.version}>"

class VersionComparison(db.Model):
    """Model for caching version comparison results"""
    id = db.Column(db.Integer, primary_key=True)
    from_version = db.Column(db.String(20), nullable=False)
    to_version = db.Column(db.String(20), nullable=False)
    comparison_data = db.Column(db.Text, nullable=True)
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    expire_date = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))
    
    __table_args__ = (
        db.UniqueConstraint('from_version', 'to_version', name='unique_version_comparison'),
    )
    
    def __repr__(self):
        return f"<VersionComparison {self.from_version} to {self.to_version}>"
    
    def is_valid(self):
        """Check if the cached comparison is still valid"""
        return self.expire_date > datetime.utcnow()
    
    def get_comparison_data(self):
        """Get the comparison data as a Python dictionary"""
        if self.comparison_data:
            return json.loads(self.comparison_data)
        return {}

class ConnectorChange(db.Model):
    """Model for tracking changes by connector"""
    id = db.Column(db.Integer, primary_key=True)
    connector_name = db.Column(db.String(50), nullable=False)
    version = db.Column(db.String(20), nullable=False)
    change_type = db.Column(db.String(20), nullable=False)  # breaking, feature, other
    description = db.Column(db.Text, nullable=False)
    impact = db.Column(db.String(20), nullable=True)  # high, medium, low
    create_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ConnectorChange {self.connector_name} {self.version}>"
