# =====================================================
# DATABASE CONFIGURATION CHO POSTGRESQL
# =====================================================

import os
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from models import Base, order_number_seq
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'bookstore_online'),
    'username': os.getenv('DB_USER', 'openpg'),
    'password': os.getenv('DB_PASSWORD', 'openpgpwd')
}

# Tạo connection string
DATABASE_URL = f"postgresql://{DATABASE_CONFIG['username']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"

# Tạo engine với các tùy chọn tối ưu
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,  # Set to True để debug SQL queries
    echo_pool=False
)

# Tạo session factory
SessionLocal = scoped_session(sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
))

# Dependency để lấy database session
def get_db():
    """Dependency để lấy database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Tạo tất cả các bảng trong database"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tất cả các bảng đã được tạo thành công!")
        
        # Tạo sequence cho order number
        with engine.connect() as conn:
            conn.execute(text("CREATE SEQUENCE IF NOT EXISTS order_number_seq START 1;"))
            conn.commit()
        logger.info("✅ Sequence order_number_seq đã được tạo!")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi tạo bảng: {e}")
        raise

def drop_tables():
    """Xóa tất cả các bảng trong database"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("✅ Tất cả các bảng đã được xóa!")
    except Exception as e:
        logger.error(f"❌ Lỗi khi xóa bảng: {e}")
        raise

def init_database():
    """Khởi tạo database với dữ liệu mẫu"""
    try:
        # Tạo các bảng
        create_tables()
        
        # Import và chạy dữ liệu mẫu
        from seed_data import seed_database
        seed_database()
        
        logger.info("🎉 Database đã được khởi tạo thành công!")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi khởi tạo database: {e}")
        raise

# Event listeners để log các hoạt động database
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Thiết lập các pragma cho PostgreSQL"""
    with dbapi_connection.cursor() as cursor:
        # Thiết lập timezone
        cursor.execute("SET timezone = 'UTC'")
        # Thiết lập encoding
        cursor.execute("SET client_encoding = 'UTF8'")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log khi checkout connection"""
    logger.debug("Database connection checked out")

@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log khi checkin connection"""
    logger.debug("Database connection checked in")

# Test connection
def test_connection():
    """Test kết nối database"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Kết nối database thành công!")
            return True
    except Exception as e:
        logger.error(f"❌ Lỗi kết nối database: {e}")
        return False

# Health check function
def health_check():
    """Kiểm tra sức khỏe database"""
    try:
        with engine.connect() as conn:
            # Kiểm tra số lượng bảng
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = result.scalar()
            
            # Kiểm tra số lượng connection
            result = conn.execute(text("SELECT COUNT(*) FROM pg_stat_activity"))
            connection_count = result.scalar()
            
            return {
                'status': 'healthy',
                'tables': table_count,
                'connections': connection_count,
                'database': DATABASE_CONFIG['database']
            }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'database': DATABASE_CONFIG['database']
        }

if __name__ == "__main__":
    # Test connection khi chạy trực tiếp file
    if test_connection():
        print("Database connection successful!")
        print(f"Database: {DATABASE_CONFIG['database']}")
        print(f"Host: {DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}")
    else:
        print("Database connection failed!")




