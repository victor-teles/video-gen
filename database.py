"""
Database connection and session management
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.pool import QueuePool
from models import Base
import config
import time
import logging

logger = logging.getLogger(__name__)

def create_engine_with_retries():
    """Create database engine with retry logic"""
    if "sqlite" in config.DATABASE_URL:
        # SQLite-specific settings
        return create_engine(
            config.DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
    else:
        # PostgreSQL/other database settings with enhanced settings
        return create_engine(
            config.DATABASE_URL,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,  # Recycle connections after 30 minutes
            pool_pre_ping=True,  # Enable connection health checks
            connect_args={
                "connect_timeout": 10,  # Connection timeout in seconds
                "keepalives": 1,        # Enable TCP keepalive
                "keepalives_idle": 60,  # Idle time before sending keepalive
                "keepalives_interval": 10,  # Interval between keepalives
                "keepalives_count": 5    # Number of keepalive retries
            }
        )

# Create database engine
engine = create_engine_with_retries()

# Add event listeners for connection pool
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    """Set up connection-specific settings"""
    if "postgresql" in config.DATABASE_URL:
        # Set session parameters for PostgreSQL
        cursor = dbapi_connection.cursor()
        cursor.execute("SET SESSION statement_timeout = '300s'")  # 5-minute statement timeout
        cursor.close()

@event.listens_for(engine, "checkout")
def checkout(dbapi_connection, connection_record, connection_proxy):
    """Verify the connection is still valid on checkout"""
    try:
        # Test the connection before using it
        cursor = dbapi_connection.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
    except Exception:
        # If the connection is invalid, remove it from the pool
        connection_record.invalidate()
        raise

# Create session factory with transaction handling
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Prevent expired object issues
)

def get_db() -> Session:
    """Get database session with retry logic and proper error handling"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            try:
                yield db
            finally:
                try:
                    db.close()
                except Exception as e:
                    logger.warning(f"Error closing database connection: {e}")
        except (DBAPIError, SQLAlchemyError) as e:
            if attempt == max_retries - 1:  # Last attempt
                logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                raise
            logger.warning(f"Database connection attempt {attempt + 1} failed: {e}")
            time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            continue
        break

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def init_database():
    """Initialize database with tables"""
    print("🗄️  Initializing database...")
    create_tables()
    print("✅ Database initialized successfully") 