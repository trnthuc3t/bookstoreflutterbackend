
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date, 
    ForeignKey, UniqueConstraint, CheckConstraint,
    Index, Sequence, ARRAY, JSON
)
from sqlalchemy.types import DECIMAL as Decimal
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from datetime import datetime
import uuid

Base = declarative_base()

# 1. HỆ THỐNG NGƯỜI DÙNG VÀ PHÂN QUYỀN

class UserRole(Base):
    __tablename__ = 'user_roles'
    
    id = Column(Integer, primary_key=True)
    role_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    permissions = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    phone = Column(String(20))
    date_of_birth = Column(Date)
    avatar_url = Column(String(200))
    role_id = Column(Integer, ForeignKey('user_roles.id'), default=2)
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    role = relationship("UserRole", back_populates="users")
    addresses = relationship("UserAddress", back_populates="user", cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="user", cascade="all, delete-orphan")
    wishlist_items = relationship("WishlistItem", back_populates="user", cascade="all, delete-orphan")
    reviews = relationship("BookReview", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user")
    
    # Indexes and Constraints
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_role', 'role_id'),
        Index('idx_users_active', 'is_active'),
        Index('idx_users_created', 'created_at'),
    )

class UserAddress(Base):
    __tablename__ = 'user_addresses'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    recipient_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    address_line1 = Column(String(200), nullable=False)
    address_line2 = Column(String(200))
    ward = Column(String(50))
    district = Column(String(50))
    city = Column(String(50), nullable=False)
    country = Column(String(50), default='Vietnam')
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="addresses")
    orders = relationship("Order", back_populates="shipping_address")

class EmailVerificationToken(Base):
    __tablename__ = 'email_verification_tokens'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = Column(String(100), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_email_token', 'token'),
        Index('idx_email_token_user', 'user_id'),
    )

class PasswordResetToken(Base):
    __tablename__ = 'password_reset_tokens'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = Column(String(100), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_reset_token', 'token'),
        Index('idx_reset_token_user', 'user_id'),
    )

class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False)  # Hash of the token for security
    device_info = Column(String(200))  # Optional: track device/browser
    ip_address = Column(INET)  # Optional: track IP address
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    # Indexes
    __table_args__ = (
        Index('idx_refresh_token_hash', 'token_hash'),
        Index('idx_refresh_token_user', 'user_id'),
        Index('idx_refresh_token_expires', 'expires_at'),
        Index('idx_refresh_token_revoked', 'is_revoked'),
    )

# 2. QUẢN LÝ SẢN PHẨM SÁCH

class Publisher(Base):
    __tablename__ = 'publishers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    contact_email = Column(String(100))
    contact_phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    books = relationship("Book", back_populates="publisher")

class Supplier(Base):
    __tablename__ = 'suppliers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    contact_person = Column(String(100))
    email = Column(String(100))
    phone = Column(String(20))
    address = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    books = relationship("Book", back_populates="supplier")

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey('categories.id'))
    image_url = Column(String(200))
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    parent = relationship("Category", remote_side=[id], backref="children")
    books = relationship("Book", back_populates="category")

class Author(Base):
    __tablename__ = 'authors'
    
    id = Column(Integer, primary_key=True)
    pen_name = Column(String(100), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    book_authors = relationship("BookAuthor", back_populates="author")

class Book(Base):
    __tablename__ = 'books'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    subtitle = Column(String(200))
    slug = Column(String(200), unique=True, nullable=False)
    isbn = Column(String(20), unique=True)
    description = Column(Text)
    publication_year = Column(Integer)
    pages = Column(Integer)
    cover_type = Column(String(20))
    language = Column(String(20), default='Vietnamese')
    
    # Dimensions (cm) and Weight (grams)
    length = Column(Decimal(5, 2))  # Length in cm
    width = Column(Decimal(5, 2))   # Width in cm
    thickness = Column(Decimal(5, 2))  # Thickness in cm
    weight = Column(Integer)  # Weight in grams
    
    price = Column(Decimal(10, 2), nullable=False)
    cost_price = Column(Decimal(10, 2))
    original_price = Column(Decimal(10, 2))
    discount_percentage = Column(Decimal(5, 2), default=0)
    stock_quantity = Column(Integer, default=0)
    sold_quantity = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    rating_average = Column(Decimal(3, 2), default=0)
    rating_count = Column(Integer, default=0)
    publisher_id = Column(Integer, ForeignKey('publishers.id'))
    supplier_id = Column(Integer, ForeignKey('suppliers.id'))
    category_id = Column(Integer, ForeignKey('categories.id'))
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    is_bestseller = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    publisher = relationship("Publisher", back_populates="books")
    supplier = relationship("Supplier", back_populates="books")
    category = relationship("Category", back_populates="books")
    book_authors = relationship("BookAuthor", back_populates="book", cascade="all, delete-orphan")
    book_images = relationship("BookImage", back_populates="book", cascade="all, delete-orphan")
    reviews = relationship("BookReview", back_populates="book", cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="book", cascade="all, delete-orphan")
    wishlist_items = relationship("WishlistItem", back_populates="book", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="book")
    
    # Indexes and Constraints
    __table_args__ = (
        Index('idx_books_category', 'category_id'),
        Index('idx_books_publisher', 'publisher_id'),
        Index('idx_books_supplier', 'supplier_id'),
        Index('idx_books_price', 'price'),
        Index('idx_books_rating', 'rating_average'),
        Index('idx_books_stock', 'stock_quantity'),
        Index('idx_books_active', 'is_active'),
        Index('idx_books_featured', 'is_featured'),
        Index('idx_books_slug', 'slug'),
        Index('idx_books_title', 'title'),
        CheckConstraint("cover_type IN ('hardcover', 'paperback', 'ebook', 'audiobook')"),
    )

class BookAuthor(Base):
    __tablename__ = 'book_authors'
    
    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    author_id = Column(Integer, ForeignKey('authors.id', ondelete='CASCADE'), nullable=False)
    role = Column(String(50), default='author')
    sort_order = Column(Integer, default=0)
    
    # Relationships
    book = relationship("Book", back_populates="book_authors")
    author = relationship("Author", back_populates="book_authors")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('book_id', 'author_id', 'role'),
        CheckConstraint("role IN ('author', 'co-author', 'editor', 'translator', 'illustrator')"),
    )

class BookImage(Base):
    __tablename__ = 'book_images'
    
    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    image_url = Column(String(200), nullable=False)
    sort_order = Column(Integer, default=0)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    book = relationship("Book", back_populates="book_images")

# 3. HỆ THỐNG ĐÁNH GIÁ VÀ REVIEW

class BookReview(Base):
    __tablename__ = 'book_reviews'
    
    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='SET NULL'), nullable=True)  # Added order_id
    rating = Column(Integer)
    title = Column(String(200))
    comment = Column(Text)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    book = relationship("Book", back_populates="reviews")
    user = relationship("User", back_populates="reviews")
    order = relationship("Order")  # Added order relationship
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('book_id', 'user_id', 'order_id'),  # Changed: allow multiple reviews per book if different orders
        Index('idx_reviews_book', 'book_id'),
        Index('idx_reviews_user', 'user_id'),
        Index('idx_reviews_order', 'order_id'),  # Added order index
        Index('idx_reviews_rating', 'rating'),
        CheckConstraint("rating >= 1 AND rating <= 5"),
    )

class ReviewRating(Base):
    __tablename__ = 'review_ratings'
    
    id = Column(Integer, primary_key=True)
    review_id = Column(Integer, ForeignKey('book_reviews.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    is_helpful = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    review = relationship("BookReview")
    user = relationship("User")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('review_id', 'user_id'),
    )

# 4. HỆ THỐNG GIỎ HÀNG VÀ WISHLIST

class CartItem(Base):
    __tablename__ = 'cart_items'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    book_id = Column(Integer, ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    quantity = Column(Integer, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="cart_items")
    book = relationship("Book", back_populates="cart_items")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'book_id'),
        Index('idx_cart_user', 'user_id'),
        CheckConstraint("quantity > 0"),
    )

class WishlistItem(Base):
    __tablename__ = 'wishlist_items'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    book_id = Column(Integer, ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="wishlist_items")
    book = relationship("Book", back_populates="wishlist_items")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'book_id'),
        Index('idx_wishlist_user', 'user_id'),
    )

# 5. HỆ THỐNG VOUCHER VÀ KHUYẾN MÃI

class Voucher(Base):
    __tablename__ = 'vouchers'
    
    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    discount_type = Column(String(20))
    discount_value = Column(Decimal(10, 2), nullable=False)
    min_order_amount = Column(Decimal(10, 2), default=0)
    max_discount_amount = Column(Decimal(10, 2))
    usage_limit = Column(Integer)
    used_count = Column(Integer, default=0)
    user_limit = Column(Integer, default=1)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    applicable_categories = Column(ARRAY(Integer))
    applicable_books = Column(ARRAY(Integer))
    excluded_categories = Column(ARRAY(Integer))
    excluded_books = Column(ARRAY(Integer))
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    creator = relationship("User")
    voucher_usages = relationship("VoucherUsage", back_populates="voucher", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="voucher")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("discount_type IN ('percentage', 'fixed_amount', 'free_shipping')"),
    )

class VoucherUsage(Base):
    __tablename__ = 'voucher_usage'
    
    id = Column(Integer, primary_key=True)
    voucher_id = Column(Integer, ForeignKey('vouchers.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    discount_amount = Column(Decimal(10, 2), nullable=False)
    used_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    voucher = relationship("Voucher", back_populates="voucher_usages")
    user = relationship("User")
    order = relationship("Order")

# 6. HỆ THỐNG THANH TOÁN VÀ ĐƠN HÀNG

class PaymentMethod(Base):
    __tablename__ = 'payment_methods'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    icon_url = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    orders = relationship("Order", back_populates="payment_method")

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    order_number = Column(String(50), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String(20), default='pending')
    subtotal = Column(Decimal(10, 2), nullable=False)
    discount_amount = Column(Decimal(10, 2), default=0)
    shipping_fee = Column(Decimal(10, 2), default=0)
    total_amount = Column(Decimal(10, 2), nullable=False)
    payment_method_id = Column(Integer, ForeignKey('payment_methods.id'))
    payment_status = Column(String(20), default='pending')
    payment_reference = Column(String(100))
    voucher_id = Column(Integer, ForeignKey('vouchers.id'))
    shipping_address_id = Column(Integer, ForeignKey('user_addresses.id'))
    notes = Column(Text)
    tracking_number = Column(String(100))
    estimated_delivery_date = Column(Date)
    shipped_at = Column(DateTime)
    delivered_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    cancellation_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    payment_method = relationship("PaymentMethod", back_populates="orders")
    voucher = relationship("Voucher", back_populates="orders")
    shipping_address = relationship("UserAddress", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    order_history = relationship("OrderHistory", back_populates="order", cascade="all, delete-orphan")
    voucher_usages = relationship("VoucherUsage", back_populates="order")
    
    # Indexes and Constraints
    __table_args__ = (
        Index('idx_orders_user', 'user_id'),
        Index('idx_orders_status', 'status'),
        Index('idx_orders_created', 'created_at'),
        Index('idx_orders_number', 'order_number'),
        CheckConstraint("status IN ('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded')"),
        CheckConstraint("payment_status IN ('pending', 'paid', 'failed', 'refunded', 'partially_refunded')"),
    )

class OrderItem(Base):
    __tablename__ = 'order_items'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    book_id = Column(Integer, ForeignKey('books.id'))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Decimal(10, 2), nullable=False)
    discount_amount = Column(Decimal(10, 2), default=0)
    total_price = Column(Decimal(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    book = relationship("Book", back_populates="order_items")
    
    # Indexes and Constraints
    __table_args__ = (
        Index('idx_order_items_order', 'order_id'),
        Index('idx_order_items_book', 'book_id'),
        CheckConstraint("quantity > 0"),
    )

class OrderHistory(Base):
    __tablename__ = 'order_history'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    status = Column(String(20), nullable=False)
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    order = relationship("Order", back_populates="order_history")
    creator = relationship("User")

# HOÀN THÀNH CÁC MODELS

# Tạo sequence cho order number
order_number_seq = Sequence('order_number_seq', start=1)