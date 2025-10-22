# =====================================================
# SETUP DATABASE ĐƠN GIẢN - CHỈ CẦN CHẠY 1 LỆNH
# =====================================================

import os
import sys
from database import create_tables, test_connection, health_check
from seed_data import seed_database
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_database():
    """Setup database hoàn chỉnh - tạo bảng và thêm dữ liệu mẫu"""
    try:
        logger.info("🚀 Bắt đầu setup database...")
        
        # 1. Test kết nối database
        logger.info("📡 Đang test kết nối database...")
        if not test_connection():
            logger.error("❌ Không thể kết nối database!")
            logger.error("💡 Hãy kiểm tra:")
            logger.error("   - PostgreSQL đã được cài đặt và chạy")
            logger.error("   - Database 'bookstore_online' đã được tạo")
            logger.error("   - Username/password đúng")
            logger.error("   - File .env có cấu hình đúng")
            return False
        
        # 2. Tạo các bảng
        logger.info("🏗️ Đang tạo các bảng...")
        create_tables()
        
        # 3. Thêm dữ liệu mẫu
        logger.info("🌱 Đang thêm dữ liệu mẫu...")
        seed_database()
        
        # 4. Kiểm tra kết quả
        logger.info("🔍 Đang kiểm tra kết quả...")
        health = health_check()
        
        if health['status'] == 'healthy':
            logger.info("🎉 Setup database thành công!")
            logger.info(f"📊 Số bảng đã tạo: {health['tables']}")
            logger.info(f"🔗 Số kết nối: {health['connections']}")
            logger.info("")
            logger.info("✅ Database đã sẵn sàng!")
            logger.info("📝 Thông tin đăng nhập mẫu:")
            logger.info("   👤 Admin: admin@bookstore.com / admin123")
            logger.info("   👤 Customer: customer@example.com / customer123")
            logger.info("   👤 Staff: staff@bookstore.com / staff123")
            return True
        else:
            logger.error(f"❌ Database không khỏe mạnh: {health.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Lỗi khi setup database: {e}")
        logger.error("💡 Hãy kiểm tra lại cấu hình database")
        return False

def check_environment():
    """Kiểm tra environment variables"""
    logger.info("🔧 Đang kiểm tra cấu hình...")
    
    required_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"⚠️ Thiếu environment variables: {', '.join(missing_vars)}")
        logger.info("💡 Tạo file .env với nội dung:")
        logger.info("DB_HOST=localhost")
        logger.info("DB_PORT=5432")
        logger.info("DB_NAME=bookstore_online")
        logger.info("DB_USER=openpg")
        logger.info("DB_PASSWORD=18102004")
        return False
    
    logger.info("✅ Cấu hình environment OK!")
    return True

def main():
    """Main function"""
    print("=" * 60)
    print("📚 BOOKSTORE DATABASE SETUP")
    print("=" * 60)
    
    # Kiểm tra environment
    if not check_environment():
        logger.info("🔄 Sử dụng cấu hình mặc định...")
    
    # Setup database
    success = setup_database()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 HOÀN THÀNH!")
        print("=" * 60)
        print("📖 Database đã sẵn sàng cho ứng dụng bán sách!")
        print("🚀 Bạn có thể bắt đầu phát triển API và kết nối Flutter app")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ SETUP THẤT BẠI!")
        print("=" * 60)
        print("💡 Hãy kiểm tra lại:")
        print("   1. PostgreSQL đã được cài đặt và chạy")
        print("   2. Database 'bookstore_online' đã được tạo")
        print("   3. Username/password đúng")
        print("   4. File .env có cấu hình đúng")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
