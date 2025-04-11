from app import app
from config import db, logger

# Initialize the database when the application starts
def init_db():
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created")
            
            # Import models here to avoid circular imports
            from models import TrinoVersion
            
            # Add initial versions if the table is empty
            if TrinoVersion.query.count() == 0:
                common_versions = ['401', '406', '414', '424', '438', '442', '446', '451', '458', '465', '473', '474']
                for version in common_versions:
                    db.session.add(TrinoVersion(version=version))
                db.session.commit()
                logger.info(f"Added initial versions: {common_versions}")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            db.session.rollback()

# Initialize database on import
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
