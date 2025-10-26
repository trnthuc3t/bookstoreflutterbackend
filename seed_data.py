# =====================================================
# DỮ LIỆU MẪU CHO DATABASE BÁN SÁCH ONLINE
# =====================================================

from database import SessionLocal, engine
from models import *
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def seed_database():
    """Thêm dữ liệu mẫu vào database"""
    db = SessionLocal()
    try:
        logger.info("🌱 Bắt đầu thêm dữ liệu mẫu...")
        
        # 1. Thêm User Roles
        seed_user_roles(db)
        
        # 2. Thêm Payment Methods
        seed_payment_methods(db)
        
        # 3. Thêm Categories
        seed_categories(db)
        
        # 4. Thêm Publishers
        seed_publishers(db)
        
        # 5. Thêm Suppliers
        seed_suppliers(db)
        
        # 6. Thêm Authors
        seed_authors(db)
        
        # 7. Thêm Sample Users
        seed_users(db)
        
        # 8. Thêm Sample Books
        seed_books(db)
        
        # 9. Thêm Sample Vouchers
        seed_vouchers(db)
        
        db.commit()
        logger.info("✅ Dữ liệu mẫu đã được thêm thành công!")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Lỗi khi thêm dữ liệu mẫu: {e}")
        raise
    finally:
        db.close()

def seed_user_roles(db):
    """Thêm các vai trò người dùng"""
    roles_data = [
        {
            'role_name': 'admin',
            'description': 'Quản trị viên hệ thống',
            'permissions': {
                'all': True,
                'manage_users': True,
                'manage_products': True,
                'manage_orders': True,
                'manage_settings': True,
                'view_reports': True
            }
        },
        {
            'role_name': 'staff',
            'description': 'Nhân viên',
            'permissions': {
                'manage_products': True,
                'manage_orders': True,
                'view_reports': True,
                'manage_reviews': True
            }
        },
        {
            'role_name': 'customer',
            'description': 'Khách hàng',
            'permissions': {
                'place_orders': True,
                'write_reviews': True,
                'manage_profile': True,
                'view_orders': True
            }
        }
    ]
    
    for role_data in roles_data:
        existing_role = db.query(UserRole).filter(UserRole.role_name == role_data['role_name']).first()
        if not existing_role:
            role = UserRole(**role_data)
            db.add(role)
    
    logger.info("✅ User roles đã được thêm!")

def seed_payment_methods(db):
    """Thêm các phương thức thanh toán"""
    payment_methods_data = [
        {
            'name': 'Cash on Delivery',
            'description': 'Thanh toán khi nhận hàng',
            'is_active': True
        },
        {
            'name': 'Bank Transfer',
            'description': 'Chuyển khoản ngân hàng',
            'is_active': True
        },
        {
            'name': 'Credit Card',
            'description': 'Thẻ tín dụng',
            'is_active': True
        },
        {
            'name': 'E-Wallet',
            'description': 'Ví điện tử (MoMo, ZaloPay)',
            'is_active': True
        },
        {
            'name': 'QR Code',
            'description': 'Quét mã QR',
            'is_active': True
        }
    ]
    
    for pm_data in payment_methods_data:
        existing_pm = db.query(PaymentMethod).filter(PaymentMethod.name == pm_data['name']).first()
        if not existing_pm:
            payment_method = PaymentMethod(**pm_data)
            db.add(payment_method)
    
    logger.info("✅ Payment methods đã được thêm!")

def seed_categories(db):
    """Thêm các thể loại sách"""
    categories_data = [
        {'name': 'Tiểu thuyết', 'slug': 'tieu-thuyet', 'description': 'Các tác phẩm tiểu thuyết văn học'},
        {'name': 'Khoa học', 'slug': 'khoa-hoc', 'description': 'Sách khoa học và công nghệ'},
        {'name': 'Lịch sử', 'slug': 'lich-su', 'description': 'Sách về lịch sử và văn hóa'},
        {'name': 'Kinh tế', 'slug': 'kinh-te', 'description': 'Sách về kinh tế và kinh doanh'},
        {'name': 'Nghệ thuật', 'slug': 'nghe-thuat', 'description': 'Sách về nghệ thuật và thiết kế'},
        {'name': 'Giáo dục', 'slug': 'giao-duc', 'description': 'Sách giáo dục và học tập'},
        {'name': 'Sức khỏe', 'slug': 'suc-khoe', 'description': 'Sách về sức khỏe và y tế'},
        {'name': 'Du lịch', 'slug': 'du-lich', 'description': 'Sách về du lịch và khám phá'},
        {'name': 'Thiếu nhi', 'slug': 'thieu-nhi', 'description': 'Sách dành cho trẻ em'},
        {'name': 'Tâm lý học', 'slug': 'tam-ly-hoc', 'description': 'Sách về tâm lý và phát triển bản thân'},
        {'name': 'Công nghệ', 'slug': 'cong-nghe', 'description': 'Sách về công nghệ thông tin'},
        {'name': 'Ngoại ngữ', 'slug': 'ngoai-ngu', 'description': 'Sách học ngoại ngữ'}
    ]
    
    for cat_data in categories_data:
        existing_cat = db.query(Category).filter(Category.slug == cat_data['slug']).first()
        if not existing_cat:
            category = Category(**cat_data)
            db.add(category)
    
    logger.info("✅ Categories đã được thêm!")

def seed_publishers(db):
    """Thêm các nhà xuất bản"""
    publishers_data = [
        {
            'name': 'Nhà xuất bản Trẻ',
            'contact_email': 'info@nxbtre.com.vn',
            'contact_phone': '02838229339'
        },
        {
            'name': 'Kim Đồng',
            'contact_email': 'info@nxbkimdong.com.vn',
            'contact_phone': '02438221351'
        },
        {
            'name': 'Nhã Nam',
            'contact_email': 'info@nhanam.vn',
            'contact_phone': '02437712718'
        },
        {
            'name': 'Alpha Books',
            'contact_email': 'info@alphabooks.vn',
            'contact_phone': '02437712718'
        },
        {
            'name': 'First News',
            'contact_email': 'info@firstnews.com.vn',
            'contact_phone': '02838229339'
        },
        {
            'name': 'Thái Hà Books',
            'contact_email': 'info@thaihabooks.com',
            'contact_phone': '02437712718'
        }
    ]
    
    for pub_data in publishers_data:
        existing_pub = db.query(Publisher).filter(Publisher.name == pub_data['name']).first()
        if not existing_pub:
            publisher = Publisher(**pub_data)
            db.add(publisher)
    
    logger.info("✅ Publishers đã được thêm!")

def seed_suppliers(db):
    """Thêm các nhà cung cấp"""
    suppliers_data = [
        {
            'name': 'Công ty TNHH Phát hành Sách ABC',
            'contact_person': 'Nguyễn Văn A',
            'email': 'contact@abcbooks.com',
            'phone': '0123456789',
            'address': '123 Đường ABC, Quận 1, TP.HCM'
        },
        {
            'name': 'Nhà phân phối Sách XYZ',
            'contact_person': 'Trần Thị B',
            'email': 'info@xyzbooks.com',
            'phone': '0987654321',
            'address': '456 Đường XYZ, Quận 3, TP.HCM'
        },
        {
            'name': 'Đại lý Sách DEF',
            'contact_person': 'Lê Văn C',
            'email': 'sales@defbooks.com',
            'phone': '0369258147',
            'address': '789 Đường DEF, Quận 5, TP.HCM'
        }
    ]
    
    for sup_data in suppliers_data:
        existing_sup = db.query(Supplier).filter(Supplier.name == sup_data['name']).first()
        if not existing_sup:
            supplier = Supplier(**sup_data)
            db.add(supplier)
    
    logger.info("✅ Suppliers đã được thêm!")

def seed_authors(db):
    """Thêm các tác giả"""
    authors_data = [
        {'pen_name': 'Nguyễn Nhật Ánh', 'is_active': True},
        {'pen_name': 'Paulo Coelho', 'is_active': True},
        {'pen_name': 'Dale Carnegie', 'is_active': True},
        {'pen_name': 'Stephen Covey', 'is_active': True},
        {'pen_name': 'Yuval Noah Harari', 'is_active': True}
    ]
    
    for auth_data in authors_data:
        existing_auth = db.query(Author).filter(
            Author.pen_name == auth_data['pen_name']
        ).first()
        if not existing_auth:
            author = Author(**auth_data)
            db.add(author)
    
    logger.info("✅ Authors đã được thêm!")

def seed_users(db):
    """Thêm user mẫu"""
    users_data = [
        {
            'username': 'admin',
            'email': 'admin@bookstore.com',
            'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8Kz8Kz2',  # admin123
            'first_name': 'Admin',
            'last_name': 'System',
            'role_id': 1,
            'email_verified': True,
            'is_active': True
        },
        {
            'username': 'customer1',
            'email': 'customer@example.com',
            'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8Kz8Kz2',  # customer123
            'first_name': 'Nguyễn',
            'last_name': 'Văn A',
            'role_id': 3,
            'email_verified': True,
            'is_active': True
        },
        {
            'username': 'staff1',
            'email': 'staff@bookstore.com',
            'password_hash': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8Kz8Kz2',  # staff123
            'first_name': 'Trần',
            'last_name': 'Thị B',
            'role_id': 2,
            'email_verified': True,
            'is_active': True
        }
    ]
    
    for user_data in users_data:
        existing_user = db.query(User).filter(User.username == user_data['username']).first()
        if not existing_user:
            user = User(**user_data)
            db.add(user)
    
    logger.info("✅ Users đã được thêm!")

def seed_books(db):
    """Thêm sách mẫu"""
    # Lấy các ID cần thiết
    category_tieu_thuyet = db.query(Category).filter(Category.slug == 'tieu-thuyet').first()
    category_kinh_te = db.query(Category).filter(Category.slug == 'kinh-te').first()
    category_tam_ly = db.query(Category).filter(Category.slug == 'tam-ly-hoc').first()
    
    publisher_tre = db.query(Publisher).filter(Publisher.name == 'Nhà xuất bản Trẻ').first()
    publisher_alpha = db.query(Publisher).filter(Publisher.name == 'Alpha Books').first()
    
    supplier_abc = db.query(Supplier).filter(Supplier.name.like('%ABC%')).first()
    
    books_data = [
        {
            'title': 'Tôi Thấy Hoa Vàng Trên Cỏ Xanh',
            'slug': 'toi-thay-hoa-vang-tren-co-xanh',
            'isbn': '9786041000001',
            'description': 'Câu chuyện về tuổi thơ của cậu bé Thiều và những kỷ niệm đẹp đẽ.',
            'summary': 'Một tác phẩm văn học thiếu nhi nổi tiếng của Nguyễn Nhật Ánh.',
            'publication_year': 2010,
            'pages': 300,
            'weight': 0.4,
            'dimensions': '20x15x2 cm',
            'cover_type': 'paperback',
            'language': 'Vietnamese',
            'price': 85000,
            'original_price': 100000,
            'discount_percentage': 15,
            'cost_price': 50000,
            'stock_quantity': 50,
            'min_stock_level': 5,
            'publisher_id': publisher_tre.id if publisher_tre else 1,
            'supplier_id': supplier_abc.id if supplier_abc else 1,
            'category_id': category_tieu_thuyet.id if category_tieu_thuyet else 1,
            'is_active': True,
            'is_featured': True
        },
        {
            'title': 'Nhà Giả Kim',
            'slug': 'nha-gia-kim',
            'isbn': '9786041000002',
            'description': 'Câu chuyện về Santiago, một cậu bé chăn cừu đi tìm kho báu của mình.',
            'summary': 'Tác phẩm nổi tiếng của Paulo Coelho về hành trình tìm kiếm ý nghĩa cuộc sống.',
            'publication_year': 1988,
            'pages': 200,
            'weight': 0.3,
            'dimensions': '19x13x2 cm',
            'cover_type': 'paperback',
            'language': 'Vietnamese',
            'price': 120000,
            'original_price': 150000,
            'discount_percentage': 20,
            'cost_price': 80000,
            'stock_quantity': 30,
            'min_stock_level': 5,
            'publisher_id': publisher_tre.id if publisher_tre else 1,
            'supplier_id': supplier_abc.id if supplier_abc else 1,
            'category_id': category_tieu_thuyet.id if category_tieu_thuyet else 1,
            'is_active': True,
            'is_bestseller': True
        },
        {
            'title': 'Đắc Nhân Tâm',
            'slug': 'dac-nhan-tam',
            'isbn': '9786041000003',
            'description': 'Cuốn sách kinh điển về nghệ thuật giao tiếp và ứng xử.',
            'summary': 'Tác phẩm nổi tiếng của Dale Carnegie về cách thu phục lòng người.',
            'publication_year': 1936,
            'pages': 400,
            'weight': 0.5,
            'dimensions': '21x15x3 cm',
            'cover_type': 'hardcover',
            'language': 'Vietnamese',
            'price': 150000,
            'original_price': 180000,
            'discount_percentage': 16.67,
            'cost_price': 100000,
            'stock_quantity': 25,
            'min_stock_level': 5,
            'publisher_id': publisher_alpha.id if publisher_alpha else 4,
            'supplier_id': supplier_abc.id if supplier_abc else 1,
            'category_id': category_tam_ly.id if category_tam_ly else 10,
            'is_active': True,
            'is_featured': True
        }
    ]
    
    for book_data in books_data:
        existing_book = db.query(Book).filter(Book.slug == book_data['slug']).first()
        if not existing_book:
            book = Book(**book_data)
            db.add(book)
    
    logger.info("✅ Books đã được thêm!")

def seed_vouchers(db):
    """Thêm voucher mẫu"""
    from datetime import datetime, timedelta
    
    vouchers_data = [
        {
            'code': 'WELCOME10',
            'name': 'Chào mừng khách hàng mới',
            'description': 'Giảm 10% cho đơn hàng đầu tiên',
            'discount_type': 'percentage',
            'discount_value': 10,
            'min_order_amount': 100000,
            'max_discount_amount': 50000,
            'usage_limit': 1000,
            'user_limit': 1,
            'start_date': datetime.now(),
            'end_date': datetime.now() + timedelta(days=30),
            'is_active': True,
            'created_by': 1
        },
        {
            'code': 'FREESHIP',
            'name': 'Miễn phí ship',
            'description': 'Miễn phí ship cho đơn hàng từ 500k',
            'discount_type': 'free_shipping',
            'discount_value': 0,
            'min_order_amount': 500000,
            'usage_limit': 500,
            'user_limit': 2,
            'start_date': datetime.now(),
            'end_date': datetime.now() + timedelta(days=15),
            'is_active': True,
            'created_by': 1
        },
        {
            'code': 'SAVE50K',
            'name': 'Tiết kiệm 50k',
            'description': 'Giảm 50k cho đơn hàng từ 300k',
            'discount_type': 'fixed_amount',
            'discount_value': 50000,
            'min_order_amount': 300000,
            'usage_limit': 200,
            'user_limit': 1,
            'start_date': datetime.now(),
            'end_date': datetime.now() + timedelta(days=7),
            'is_active': True,
            'created_by': 1
        }
    ]
    
    for voucher_data in vouchers_data:
        existing_voucher = db.query(Voucher).filter(Voucher.code == voucher_data['code']).first()
        if not existing_voucher:
            voucher = Voucher(**voucher_data)
            db.add(voucher)
    
    logger.info("✅ Vouchers đã được thêm!")

if __name__ == "__main__":
    # Chạy seed data khi chạy trực tiếp file
    seed_database()

