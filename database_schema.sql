-- =====================================================
-- DATABASE SCHEMA CHO APP BÁN SÁCH ONLINE
-- PostgreSQL Database Design
-- =====================================================

-- Tạo database (chạy riêng)
-- CREATE DATABASE bookstore_online;
-- \c bookstore_online;

-- =====================================================
-- 1. HỆ THỐNG PHÂN QUYỀN VÀ NGƯỜI DÙNG
-- =====================================================

-- Bảng vai trò người dùng
CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng người dùng
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20),
    date_of_birth DATE,
    gender VARCHAR(10) CHECK (gender IN ('male', 'female', 'other')),
    avatar_url VARCHAR(200),
    role_id INTEGER REFERENCES user_roles(id) DEFAULT 2,
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    phone_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    login_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng địa chỉ người dùng
CREATE TABLE user_addresses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    address_type VARCHAR(20) DEFAULT 'home' CHECK (address_type IN ('home', 'work', 'other')),
    recipient_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    address_line1 VARCHAR(200) NOT NULL,
    address_line2 VARCHAR(200),
    ward VARCHAR(50),
    district VARCHAR(50),
    city VARCHAR(50) NOT NULL,
    postal_code VARCHAR(20),
    country VARCHAR(50) DEFAULT 'Vietnam',
    is_default BOOLEAN DEFAULT FALSE,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng session đăng nhập
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    device_info JSONB,
    ip_address INET,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 2. QUẢN LÝ SẢN PHẨM SÁCH
-- =====================================================

-- Bảng nhà xuất bản
CREATE TABLE publishers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    website VARCHAR(200),
    contact_email VARCHAR(100),
    contact_phone VARCHAR(20),
    address TEXT,
    logo_url VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng nhà cung cấp
CREATE TABLE suppliers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    contact_person VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    payment_terms VARCHAR(100),
    credit_limit DECIMAL(15,2) DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng thể loại sách
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    parent_id INTEGER REFERENCES categories(id),
    image_url VARCHAR(200),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng tác giả
CREATE TABLE authors (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    pen_name VARCHAR(100),
    biography TEXT,
    birth_date DATE,
    death_date DATE,
    nationality VARCHAR(50),
    website VARCHAR(200),
    image_url VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng sách
CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    subtitle VARCHAR(200),
    slug VARCHAR(200) UNIQUE NOT NULL,
    isbn VARCHAR(20) UNIQUE,
    description TEXT,
    summary TEXT,
    table_of_contents TEXT,
    publication_year INTEGER,
    pages INTEGER,
    weight DECIMAL(8,2), -- kg
    dimensions VARCHAR(50), -- "20x15x3 cm"
    cover_type VARCHAR(20) CHECK (cover_type IN ('hardcover', 'paperback', 'ebook', 'audiobook')),
    language VARCHAR(20) DEFAULT 'Vietnamese',
    price DECIMAL(10,2) NOT NULL,
    original_price DECIMAL(10,2),
    discount_percentage DECIMAL(5,2) DEFAULT 0,
    cost_price DECIMAL(10,2), -- Giá nhập
    stock_quantity INTEGER DEFAULT 0,
    min_stock_level INTEGER DEFAULT 5,
    sold_quantity INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    rating_average DECIMAL(3,2) DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    publisher_id INTEGER REFERENCES publishers(id),
    supplier_id INTEGER REFERENCES suppliers(id),
    category_id INTEGER REFERENCES categories(id),
    is_active BOOLEAN DEFAULT TRUE,
    is_featured BOOLEAN DEFAULT FALSE,
    is_bestseller BOOLEAN DEFAULT FALSE,
    is_new_release BOOLEAN DEFAULT FALSE,
    meta_title VARCHAR(200),
    meta_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng quan hệ nhiều-nhiều giữa sách và tác giả
CREATE TABLE book_authors (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES authors(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'author' CHECK (role IN ('author', 'co-author', 'editor', 'translator', 'illustrator')),
    sort_order INTEGER DEFAULT 0,
    UNIQUE(book_id, author_id, role)
);

-- Bảng hình ảnh sách
CREATE TABLE book_images (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
    image_url VARCHAR(200) NOT NULL,
    image_type VARCHAR(20) DEFAULT 'cover' CHECK (image_type IN ('cover', 'back', 'spine', 'sample', 'gallery', 'other')),
    alt_text VARCHAR(200),
    sort_order INTEGER DEFAULT 0,
    is_primary BOOLEAN DEFAULT FALSE,
    file_size INTEGER, -- bytes
    width INTEGER,
    height INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng tags/keywords
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    slug VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng quan hệ sách và tags
CREATE TABLE book_tags (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    UNIQUE(book_id, tag_id)
);

-- =====================================================
-- 3. HỆ THỐNG ĐÁNH GIÁ VÀ REVIEW
-- =====================================================

-- Bảng đánh giá sách
CREATE TABLE book_reviews (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    title VARCHAR(200),
    comment TEXT,
    pros TEXT, -- Ưu điểm
    cons TEXT, -- Nhược điểm
    is_verified_purchase BOOLEAN DEFAULT FALSE,
    helpful_count INTEGER DEFAULT 0,
    is_approved BOOLEAN DEFAULT TRUE,
    admin_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(book_id, user_id)
);

-- Bảng đánh giá review (like/dislike)
CREATE TABLE review_ratings (
    id SERIAL PRIMARY KEY,
    review_id INTEGER REFERENCES book_reviews(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    is_helpful BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(review_id, user_id)
);

-- =====================================================
-- 4. HỆ THỐNG GIỎ HÀNG VÀ WISHLIST
-- =====================================================

-- Bảng giỏ hàng
CREATE TABLE cart_items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, book_id)
);

-- Bảng danh sách yêu thích
CREATE TABLE wishlist_items (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, book_id)
);

-- Bảng giỏ hàng cho guest users
CREATE TABLE guest_carts (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(100) UNIQUE NOT NULL,
    device_id VARCHAR(100),
    cart_data JSONB NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 5. HỆ THỐNG VOUCHER VÀ KHUYẾN MÃI
-- =====================================================

-- Bảng voucher/khuyến mãi
CREATE TABLE vouchers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    discount_type VARCHAR(20) CHECK (discount_type IN ('percentage', 'fixed_amount', 'free_shipping')),
    discount_value DECIMAL(10,2) NOT NULL,
    min_order_amount DECIMAL(10,2) DEFAULT 0,
    max_discount_amount DECIMAL(10,2),
    usage_limit INTEGER,
    used_count INTEGER DEFAULT 0,
    user_limit INTEGER DEFAULT 1,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    applicable_categories INTEGER[], -- Array of category IDs
    applicable_books INTEGER[], -- Array of book IDs
    excluded_categories INTEGER[],
    excluded_books INTEGER[],
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng lịch sử sử dụng voucher
CREATE TABLE voucher_usage (
    id SERIAL PRIMARY KEY,
    voucher_id INTEGER REFERENCES vouchers(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    discount_amount DECIMAL(10,2) NOT NULL,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 6. HỆ THỐNG THANH TOÁN VÀ ĐƠN HÀNG
-- =====================================================

-- Bảng phương thức thanh toán
CREATE TABLE payment_methods (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    icon_url VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    processing_fee_percentage DECIMAL(5,2) DEFAULT 0,
    min_amount DECIMAL(10,2) DEFAULT 0,
    max_amount DECIMAL(10,2),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng đơn hàng
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    order_number VARCHAR(50) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded')),
    subtotal DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    shipping_fee DECIMAL(10,2) DEFAULT 0,
    tax_amount DECIMAL(10,2) DEFAULT 0,
    total_amount DECIMAL(10,2) NOT NULL,
    payment_method_id INTEGER REFERENCES payment_methods(id),
    payment_status VARCHAR(20) DEFAULT 'pending' CHECK (payment_status IN ('pending', 'paid', 'failed', 'refunded', 'partially_refunded')),
    payment_reference VARCHAR(100),
    voucher_id INTEGER REFERENCES vouchers(id),
    shipping_address_id INTEGER REFERENCES user_addresses(id),
    notes TEXT,
    tracking_number VARCHAR(100),
    estimated_delivery_date DATE,
    shipped_at TIMESTAMP,
    delivered_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    cancellation_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng chi tiết đơn hàng
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    book_id INTEGER REFERENCES books(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    total_price DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng lịch sử đơn hàng
CREATE TABLE order_history (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,
    notes TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 7. HỆ THỐNG THÔNG BÁO VÀ LOGS
-- =====================================================

-- Bảng thông báo
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) DEFAULT 'info' CHECK (type IN ('info', 'success', 'warning', 'error', 'promotion')),
    is_read BOOLEAN DEFAULT FALSE,
    related_entity_type VARCHAR(50), -- 'order', 'book', 'review', etc.
    related_entity_id INTEGER,
    action_url VARCHAR(200),
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng logs hoạt động
CREATE TABLE activity_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id INTEGER,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bảng cấu hình hệ thống
CREATE TABLE system_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT,
    description TEXT,
    data_type VARCHAR(20) DEFAULT 'string' CHECK (data_type IN ('string', 'number', 'boolean', 'json')),
    is_public BOOLEAN DEFAULT FALSE,
    updated_by INTEGER REFERENCES users(id),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 8. TẠO INDEXES ĐỂ TỐI ƯU HIỆU SUẤT
-- =====================================================

-- Indexes cho users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role_id);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_users_created ON users(created_at);

-- Indexes cho books
CREATE INDEX idx_books_category ON books(category_id);
CREATE INDEX idx_books_publisher ON books(publisher_id);
CREATE INDEX idx_books_price ON books(price);
CREATE INDEX idx_books_rating ON books(rating_average);
CREATE INDEX idx_books_stock ON books(stock_quantity);
CREATE INDEX idx_books_active ON books(is_active);
CREATE INDEX idx_books_featured ON books(is_featured);
CREATE INDEX idx_books_slug ON books(slug);
CREATE INDEX idx_books_title ON books(title);

-- Indexes cho orders
CREATE INDEX idx_orders_user ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at);
CREATE INDEX idx_orders_number ON orders(order_number);

-- Indexes cho order_items
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_book ON order_items(book_id);

-- Indexes cho reviews
CREATE INDEX idx_reviews_book ON book_reviews(book_id);
CREATE INDEX idx_reviews_user ON book_reviews(user_id);
CREATE INDEX idx_reviews_rating ON book_reviews(rating);

-- Indexes cho cart và wishlist
CREATE INDEX idx_cart_user ON cart_items(user_id);
CREATE INDEX idx_wishlist_user ON wishlist_items(user_id);

-- Indexes cho notifications
CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(is_read);
CREATE INDEX idx_notifications_created ON notifications(created_at);

-- =====================================================
-- 9. TẠO TRIGGERS VÀ FUNCTIONS
-- =====================================================

-- Function để tự động cập nhật updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers cho updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_user_addresses_updated_at BEFORE UPDATE ON user_addresses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_books_updated_at BEFORE UPDATE ON books FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_cart_items_updated_at BEFORE UPDATE ON cart_items FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_guest_carts_updated_at BEFORE UPDATE ON guest_carts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function để tự động cập nhật rating của sách
CREATE OR REPLACE FUNCTION update_book_rating()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE books 
    SET rating_average = (
        SELECT COALESCE(AVG(rating)::DECIMAL(3,2), 0) 
        FROM book_reviews 
        WHERE book_id = COALESCE(NEW.book_id, OLD.book_id) 
        AND is_approved = TRUE
    ),
    rating_count = (
        SELECT COUNT(*) 
        FROM book_reviews 
        WHERE book_id = COALESCE(NEW.book_id, OLD.book_id) 
        AND is_approved = TRUE
    )
    WHERE id = COALESCE(NEW.book_id, OLD.book_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ language 'plpgsql';

CREATE TRIGGER update_book_rating_trigger 
    AFTER INSERT OR UPDATE OR DELETE ON book_reviews 
    FOR EACH ROW EXECUTE FUNCTION update_book_rating();

-- Function để tự động cập nhật số lượng bán và tồn kho
CREATE OR REPLACE FUNCTION update_book_inventory()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE books 
        SET sold_quantity = sold_quantity + NEW.quantity,
            stock_quantity = stock_quantity - NEW.quantity
        WHERE id = NEW.book_id;
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        UPDATE books 
        SET sold_quantity = sold_quantity - OLD.quantity + NEW.quantity,
            stock_quantity = stock_quantity + OLD.quantity - NEW.quantity
        WHERE id = NEW.book_id;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE books 
        SET sold_quantity = sold_quantity - OLD.quantity,
            stock_quantity = stock_quantity + OLD.quantity
        WHERE id = OLD.book_id;
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_book_inventory_trigger 
    AFTER INSERT OR UPDATE OR DELETE ON order_items 
    FOR EACH ROW EXECUTE FUNCTION update_book_inventory();

-- Function để tự động tạo order_number
CREATE OR REPLACE FUNCTION generate_order_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.order_number IS NULL OR NEW.order_number = '' THEN
        NEW.order_number := 'ORD-' || TO_CHAR(CURRENT_TIMESTAMP, 'YYYYMMDD') || '-' || LPAD(NEXTVAL('order_number_seq')::TEXT, 6, '0');
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Tạo sequence cho order number
CREATE SEQUENCE order_number_seq START 1;

CREATE TRIGGER generate_order_number_trigger 
    BEFORE INSERT ON orders 
    FOR EACH ROW EXECUTE FUNCTION generate_order_number();

-- =====================================================
-- 10. INSERT DỮ LIỆU MẪU
-- =====================================================

-- Insert user roles
INSERT INTO user_roles (role_name, description, permissions) VALUES
('admin', 'Quản trị viên hệ thống', '{"all": true, "manage_users": true, "manage_products": true, "manage_orders": true, "manage_settings": true}'),
('staff', 'Nhân viên', '{"manage_products": true, "manage_orders": true, "view_reports": true}'),
('customer', 'Khách hàng', '{"place_orders": true, "write_reviews": true, "manage_profile": true}');

-- Insert payment methods
INSERT INTO payment_methods (name, description, processing_fee_percentage, sort_order) VALUES
('Cash on Delivery', 'Thanh toán khi nhận hàng', 0, 1),
('Bank Transfer', 'Chuyển khoản ngân hàng', 0, 2),
('Credit Card', 'Thẻ tín dụng', 2.5, 3),
('E-Wallet', 'Ví điện tử (MoMo, ZaloPay)', 1.5, 4),
('QR Code', 'Quét mã QR', 0, 5);

-- Insert categories
INSERT INTO categories (name, slug, description) VALUES
('Tiểu thuyết', 'tieu-thuyet', 'Các tác phẩm tiểu thuyết văn học'),
('Khoa học', 'khoa-hoc', 'Sách khoa học và công nghệ'),
('Lịch sử', 'lich-su', 'Sách về lịch sử và văn hóa'),
('Kinh tế', 'kinh-te', 'Sách về kinh tế và kinh doanh'),
('Nghệ thuật', 'nghe-thuat', 'Sách về nghệ thuật và thiết kế'),
('Giáo dục', 'giao-duc', 'Sách giáo dục và học tập'),
('Sức khỏe', 'suc-khoe', 'Sách về sức khỏe và y tế'),
('Du lịch', 'du-lich', 'Sách về du lịch và khám phá'),
('Thiếu nhi', 'thieu-nhi', 'Sách dành cho trẻ em'),
('Tâm lý học', 'tam-ly-hoc', 'Sách về tâm lý và phát triển bản thân');

-- Insert publishers
INSERT INTO publishers (name, description, website) VALUES
('Nhà xuất bản Trẻ', 'Nhà xuất bản hàng đầu Việt Nam', 'https://nxbtre.com.vn'),
('Kim Đồng', 'Nhà xuất bản sách thiếu nhi', 'https://nxbkimdong.com.vn'),
('Nhã Nam', 'Nhà xuất bản sách văn học', 'https://nhanam.vn'),
('Alpha Books', 'Nhà xuất bản sách kinh tế', 'https://alphabooks.vn'),
('First News', 'Nhà xuất bản sách phát triển bản thân', 'https://firstnews.com.vn'),
('Thái Hà Books', 'Nhà xuất bản sách tâm lý', 'https://thaihabooks.com');

-- Insert suppliers
INSERT INTO suppliers (name, contact_person, email, phone) VALUES
('Công ty TNHH Phát hành Sách ABC', 'Nguyễn Văn A', 'contact@abcbooks.com', '0123456789'),
('Nhà phân phối Sách XYZ', 'Trần Thị B', 'info@xyzbooks.com', '0987654321'),
('Đại lý Sách DEF', 'Lê Văn C', 'sales@defbooks.com', '0369258147');

-- Insert system settings
INSERT INTO system_settings (setting_key, setting_value, description, data_type, is_public) VALUES
('site_name', 'Cửa hàng Sách Online', 'Tên website', 'string', true),
('currency', 'VND', 'Đơn vị tiền tệ', 'string', true),
('free_shipping_threshold', '500000', 'Ngưỡng miễn phí ship (VND)', 'number', true),
('max_cart_items', '50', 'Số lượng tối đa trong giỏ hàng', 'number', false),
('review_approval_required', 'true', 'Yêu cầu duyệt review', 'boolean', false),
('min_order_amount', '50000', 'Đơn hàng tối thiểu (VND)', 'number', true),
('shipping_fee', '30000', 'Phí ship cơ bản (VND)', 'number', true),
('tax_rate', '10', 'Thuế VAT (%)', 'number', true);

-- Insert sample admin user (password: admin123)
INSERT INTO users (username, email, password_hash, first_name, last_name, role_id, email_verified) VALUES
('admin', 'admin@bookstore.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8Kz8Kz2', 'Admin', 'System', 1, true);

-- Insert sample customer user (password: customer123)
INSERT INTO users (username, email, password_hash, first_name, last_name, role_id, email_verified) VALUES
('customer1', 'customer@example.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8Kz8Kz2', 'Nguyễn', 'Văn A', 3, true);

-- =====================================================
-- 11. TẠO VIEWS HỮU ÍCH
-- =====================================================

-- View để lấy thông tin sách đầy đủ
CREATE VIEW book_details AS
SELECT 
    b.*,
    p.name as publisher_name,
    s.name as supplier_name,
    c.name as category_name,
    c.slug as category_slug,
    STRING_AGG(DISTINCT CONCAT(a.first_name, ' ', a.last_name), ', ') as authors,
    STRING_AGG(DISTINCT t.name, ', ') as tags,
    (SELECT image_url FROM book_images WHERE book_id = b.id AND is_primary = TRUE LIMIT 1) as primary_image
FROM books b
LEFT JOIN publishers p ON b.publisher_id = p.id
LEFT JOIN suppliers s ON b.supplier_id = s.id
LEFT JOIN categories c ON b.category_id = c.id
LEFT JOIN book_authors ba ON b.id = ba.book_id
LEFT JOIN authors a ON ba.author_id = a.id
LEFT JOIN book_tags bt ON b.id = bt.book_id
LEFT JOIN tags t ON bt.tag_id = t.id
GROUP BY b.id, p.name, s.name, c.name, c.slug;

-- View để lấy thông tin đơn hàng đầy đủ
CREATE VIEW order_details AS
SELECT 
    o.*,
    u.first_name || ' ' || u.last_name as customer_name,
    u.email as customer_email,
    u.phone as customer_phone,
    pm.name as payment_method_name,
    va.recipient_name as shipping_recipient,
    va.address_line1 || ', ' || va.city as shipping_address,
    v.code as voucher_code,
    v.name as voucher_name
FROM orders o
LEFT JOIN users u ON o.user_id = u.id
LEFT JOIN payment_methods pm ON o.payment_method_id = pm.id
LEFT JOIN user_addresses va ON o.shipping_address_id = va.id
LEFT JOIN vouchers v ON o.voucher_id = v.id;

-- View để lấy thống kê sách
CREATE VIEW book_statistics AS
SELECT 
    b.id,
    b.title,
    b.price,
    b.stock_quantity,
    b.sold_quantity,
    b.rating_average,
    b.rating_count,
    b.view_count,
    (b.sold_quantity * b.price) as total_revenue,
    CASE 
        WHEN b.stock_quantity = 0 THEN 'out_of_stock'
        WHEN b.stock_quantity <= b.min_stock_level THEN 'low_stock'
        ELSE 'in_stock'
    END as stock_status
FROM books b
WHERE b.is_active = TRUE;

-- =====================================================
-- HOÀN THÀNH DATABASE SCHEMA
-- =====================================================

-- Tạo comment cho database
COMMENT ON DATABASE bookstore_online IS 'Database cho ứng dụng bán sách online - PostgreSQL Schema';

-- Thông báo hoàn thành
DO $$
BEGIN
    RAISE NOTICE 'Database schema đã được tạo thành công!';
    RAISE NOTICE 'Bao gồm: 25+ bảng, indexes, triggers, functions, views và dữ liệu mẫu';
    RAISE NOTICE 'Sẵn sàng để sử dụng cho ứng dụng Flutter!';
END $$;
