"""
Database Connection Module

Provides SQLAlchemy engine, session management, connection pooling,
health check functions, and database initialization utilities.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, text, event, Engine, exc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from shared.config.settings import Settings

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize settings
settings = Settings()


def create_database_engine(
    echo: Optional[bool] = None,
    pool_size: Optional[int] = None,
    max_overflow: Optional[int] = None,
    pool_timeout: Optional[int] = None,
) -> Engine:
    """
    Create SQLAlchemy engine with connection pooling.
    
    Args:
        echo: Whether to log SQL queries (defaults to app_debug setting)
        pool_size: Number of connections to maintain (default: 10)
        max_overflow: Max overflow connections (default: 20)
        pool_timeout: Connection timeout in seconds (default: 30)
        
    Returns:
        SQLAlchemy Engine instance
        
    Example:
        >>> engine = create_database_engine()
        >>> with engine.connect() as conn:
        ...     result = conn.execute(text("SELECT 1"))
    """
    # Use provided values or fall back to settings/defaults
    echo_sql = echo if echo is not None else settings.app_debug
    pool_size_val = pool_size if pool_size is not None else 10
    max_overflow_val = max_overflow if max_overflow is not None else 20
    pool_timeout_val = pool_timeout if pool_timeout is not None else settings.postgres_pool_timeout
    
    logger.info(
        f"Creating database engine: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
    logger.info(
        f"Pool configuration: size={pool_size_val}, max_overflow={max_overflow_val}, timeout={pool_timeout_val}"
    )
    
    # Create engine with QueuePool
    engine = create_engine(
        settings.postgres_url,
        echo=echo_sql,
        poolclass=QueuePool,
        pool_size=pool_size_val,
        max_overflow=max_overflow_val,
        pool_timeout=pool_timeout_val,
        pool_pre_ping=True,  # Verify connections before using them
        pool_recycle=3600,   # Recycle connections after 1 hour
        connect_args={
            "application_name": settings.app_name,
            "options": f"-c search_path={settings.postgres_schema}",
        },
    )
    
    # Add event listeners for connection lifecycle
    @event.listens_for(engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Log when a new connection is created."""
        logger.debug(f"New database connection created: {id(dbapi_conn)}")
    
    @event.listens_for(engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        """Log when a connection is checked out from the pool."""
        logger.debug(f"Connection checked out from pool: {id(dbapi_conn)}")
    
    @event.listens_for(engine, "checkin")
    def receive_checkin(dbapi_conn, connection_record):
        """Log when a connection is returned to the pool."""
        logger.debug(f"Connection returned to pool: {id(dbapi_conn)}")
    
    return engine


# Create global engine instance
engine = create_database_engine()

# Create SessionLocal factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Don't expire objects after commit
)


def get_db() -> Generator[Session, None, None]:
    """
    Context manager that yields a database session.
    
    Ensures the session is properly closed after use.
    Use this in FastAPI dependency injection or with context managers.
    
    Yields:
        SQLAlchemy Session instance
        
    Example:
        >>> with get_db() as db:
        ...     result = db.execute(text("SELECT 1"))
        
        # Or in FastAPI:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        logger.debug("Database session created")
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        logger.debug("Database session closed")
        db.close()


@contextmanager
def get_db_context():
    """
    Alternative context manager for database sessions.
    
    Provides a more explicit context manager interface.
    
    Example:
        >>> with get_db_context() as db:
        ...     result = db.execute(text("SELECT 1"))
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database transaction error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def test_connection() -> bool:
    """
    Test database connectivity and return connection status.
    
    Returns:
        True if connection successful, False otherwise
        
    Example:
        >>> if test_connection():
        ...     print("Database is accessible")
        ... else:
        ...     print("Database connection failed")
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()
            
            if row and row[0] == 1:
                logger.info("Database connection test successful")
                return True
            else:
                logger.error("Database connection test returned unexpected result")
                return False
                
    except exc.OperationalError as e:
        logger.error(f"Database connection test failed (OperationalError): {e}")
        return False
    except exc.DatabaseError as e:
        logger.error(f"Database connection test failed (DatabaseError): {e}")
        return False
    except Exception as e:
        logger.error(f"Database connection test failed (unexpected error): {e}")
        return False


def check_database_health() -> dict:
    """
    Perform comprehensive database health check.
    
    Returns detailed information about database connectivity,
    pool status, and basic metrics.
    
    Returns:
        Dictionary containing health check results
        
    Example:
        >>> health = check_database_health()
        >>> print(health['status'])
        'healthy'
    """
    health_status = {
        "status": "unknown",
        "database": settings.postgres_db,
        "host": settings.postgres_host,
        "port": settings.postgres_port,
        "connection_test": False,
        "pool_size": engine.pool.size(),
        "pool_checked_out": engine.pool.checkedout(),
        "pool_overflow": engine.pool.overflow(),
        "pool_checked_in": engine.pool.checkedin(),
    }
    
    try:
        # Test basic connectivity
        connection_ok = test_connection()
        health_status["connection_test"] = connection_ok
        
        if connection_ok:
            # Get additional database info
            with engine.connect() as connection:
                # Check PostgreSQL version
                result = connection.execute(text("SELECT version()"))
                version_row = result.fetchone()
                if version_row:
                    health_status["postgres_version"] = version_row[0].split(",")[0]
                
                # Check if schema exists
                result = connection.execute(
                    text(
                        "SELECT schema_name FROM information_schema.schemata "
                        "WHERE schema_name = :schema"
                    ),
                    {"schema": settings.postgres_schema}
                )
                schema_row = result.fetchone()
                health_status["schema_exists"] = schema_row is not None
                
                # Count tables in schema
                result = connection.execute(
                    text(
                        "SELECT COUNT(*) FROM information_schema.tables "
                        "WHERE table_schema = :schema AND table_type = 'BASE TABLE'"
                    ),
                    {"schema": settings.postgres_schema}
                )
                count_row = result.fetchone()
                health_status["table_count"] = count_row[0] if count_row else 0
            
            health_status["status"] = "healthy"
        else:
            health_status["status"] = "unhealthy"
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
    
    return health_status


def init_database():
    """
    Initialize database schema and extensions.
    
    This is a scaffold function that should be expanded to:
    - Create database schema if it doesn't exist
    - Install required PostgreSQL extensions
    - Run migrations
    - Seed initial data
    
    Note: In production, use Alembic migrations instead of this function.
    
    Example:
        >>> init_database()
        Database initialized successfully
    """
    logger.info("Initializing database...")
    
    try:
        with engine.connect() as connection:
            # Ensure schema exists
            connection.execute(
                text(f"CREATE SCHEMA IF NOT EXISTS {settings.postgres_schema}")
            )
            connection.commit()
            logger.info(f"Schema '{settings.postgres_schema}' ready")
            
            # Install required extensions (schema.sql should handle this)
            try:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\""))
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS \"pg_trgm\""))
                connection.commit()
                logger.info("Required PostgreSQL extensions installed")
            except exc.ProgrammingError as e:
                logger.warning(f"Extension installation skipped (may already exist): {e}")
            
            logger.info("Database initialization complete")
            
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def close_database_connections():
    """
    Close all database connections and dispose of the engine.
    
    Should be called during application shutdown.
    
    Example:
        >>> close_database_connections()
        All database connections closed
    """
    logger.info("Closing database connections...")
    engine.dispose()
    logger.info("All database connections closed")


def get_pool_status() -> dict:
    """
    Get current connection pool status.
    
    Returns:
        Dictionary with pool metrics
        
    Example:
        >>> status = get_pool_status()
        >>> print(f"Active connections: {status['checked_out']}")
    """
    return {
        "size": engine.pool.size(),
        "checked_out": engine.pool.checkedout(),
        "overflow": engine.pool.overflow(),
        "checked_in": engine.pool.checkedin(),
        "pool_size_limit": 10,  # From create_database_engine
        "max_overflow_limit": 20,
    }


# Configure logging based on debug mode
if settings.app_debug:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger.setLevel(logging.DEBUG)
    logger.debug("SQL query logging enabled (debug mode)")
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger.setLevel(logging.INFO)


# Export public interface
__all__ = [
    "engine",
    "SessionLocal",
    "get_db",
    "get_db_context",
    "test_connection",
    "check_database_health",
    "init_database",
    "close_database_connections",
    "get_pool_status",
    "create_database_engine",
]
