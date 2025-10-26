# =====================================================
# FASTAPI MAIN APPLICATION CHO BOOKSTORE BACKEND
# =====================================================

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.requests import Request
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import bcrypt
from datetime import datetime, timedelta
import re
import uuid
from typing import Optional, List
import shutil

# Load environment variables
load_dotenv()

# Get base URL from environment or use default
# To change URL, set environment variable: export BASE_URL="new_url_here"
# Or update this default value
BASE_URL = os.getenv('BASE_URL', 'https://xrjssx4r-8000.asse.devtunnels.ms')
print(f"Using BASE_URL: {BASE_URL}")

# Import database and models
from database import get_db, engine, Base
from models import *

# Create FastAPI app
app = FastAPI(
    title="BookStore API",
    description="API cho ứng dụng bán sách online",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add UTF-8 encoding middleware
@app.middleware("http")
async def add_charset_header(request: Request, call_next):
    response = await call_next(request)
    # Only add charset to JSON responses, not binary files
    if "application/json" in response.headers.get("Content-Type", ""):
        response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

# Auto-create tables if not exist
@app.on_event("startup")
async def startup_event():
    """Create tables if they don't exist and start app"""
    print("🚀 BookStore API đang khởi động...")
    
    # Create uploads directory
    upload_dir = "uploads/books"
    os.makedirs(upload_dir, exist_ok=True)
    print("✅ Upload directory created")
    
    # Auto-create tables
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables checked/created")
    except Exception as e:
        print(f"⚠️ Could not create tables: {e}")
        print("💡 Run: python setup_database.py to setup database")
    
    print("📚 API Documentation available at /docs")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên chỉ định domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for uploaded images
if os.path.exists("uploads"):
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Security
security = HTTPBearer()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# =====================================================
# PYDANTIC MODELS
# =====================================================

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None

class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    avatar_url: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: Optional[str] = None
    is_active: bool
    created_at: datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class BookCreate(BaseModel):
    title: str
    subtitle: Optional[str] = None
    isbn: Optional[str] = None
    description: Optional[str] = None
    publication_year: Optional[int] = None
    pages: Optional[int] = None
    price: float
    original_price: Optional[float] = None
    stock_quantity: int = 0
    category_id: Optional[int] = None
    publisher_id: Optional[int] = None
    language: str = "Vietnamese"
    cover_type: str = "paperback"

class BookUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    stock_quantity: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_bestseller: Optional[bool] = None

class OrderCreate(BaseModel):
    user_id: int
    shipping_address_id: int
    payment_method_id: int
    voucher_id: Optional[int] = None
    notes: Optional[str] = None

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    payment_status: Optional[str] = None
    tracking_number: Optional[str] = None
    notes: Optional[str] = None

class CartItemUpdate(BaseModel):
    quantity: int

class BookReviewCreate(BaseModel):
    book_id: int
    rating: int
    title: Optional[str] = None
    comment: Optional[str] = None

class WishlistItemCreate(BaseModel):
    book_id: int

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def verify_password(plain_password, hashed_password):
    """Verify password using bcrypt"""
    try:
        # Try with pwd_context first
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Fallback to bcrypt directly if passlib fails
        try:
            return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
        except:
            return False

def get_password_hash(password):
    """Hash password using bcrypt"""
    try:
        # Try with pwd_context first
        return pwd_context.hash(password)
    except Exception:
        # Fallback to bcrypt directly
        # Hash the password to avoid bcrypt 72-byte limit
        password_bytes = password.encode('utf-8')
        hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        return hashed.decode('utf-8')

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone):
    if not phone or phone.strip() == '':
        return True
    # Allow Vietnamese phone numbers with or without country code
    # Examples: 0123456789, 0912345678, +84912345678, 091-234-5678
    cleaned_phone = re.sub(r'[\s\-\(\)]', '', phone)  # Remove spaces, dashes, parentheses
    pattern = r'^(\+?84|0)[0-9]{9,10}$'
    return re.match(pattern, cleaned_phone) is not None

def generate_order_number():
    return f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Get current user from JWT token (placeholder - implement JWT later)"""
    # For now, return a mock user - implement JWT authentication later
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return user

# =====================================================
# HEALTH CHECK ENDPOINTS
# =====================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to BookStore API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db = next(get_db())
        db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "database": "connected",
            "message": "All systems operational"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {str(e)}"
        )

@app.get("/api/health")
async def api_health():
    """API health check"""
    return {
        "status": "ok",
        "service": "BookStore API",
        "version": "1.0.0"
    }

# =====================================================
# AUTHENTICATION ENDPOINTS
# =====================================================

@app.post("/api/auth/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Đăng ký tài khoản người dùng mới"""
    
    # Validate email format
    if not validate_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email không hợp lệ")
    
    # Validate phone format
    if user_data.phone and not validate_phone(user_data.phone):
        raise HTTPException(status_code=400, detail="Số điện thoại không hợp lệ")
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại")
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email đã được sử dụng")
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Parse date of birth
    date_of_birth = None
    if user_data.date_of_birth:
        try:
            date_of_birth = datetime.strptime(user_data.date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Ngày sinh phải có định dạng YYYY-MM-DD")
    
    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        date_of_birth=date_of_birth,
        role_id=2,  # Default role: customer
        is_active=True,
        email_verified=False,
        phone_verified=False
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Get role name
        role_name = None
        if new_user.role:
            role_name = new_user.role.role_name
        
        return UserResponse(
            id=new_user.id,
            username=new_user.username,
            email=new_user.email,
            first_name=new_user.first_name,
            last_name=new_user.last_name,
            phone=new_user.phone,
            role=role_name,
            is_active=new_user.is_active,
            created_at=new_user.created_at
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo tài khoản: {str(e)}")

@app.post("/api/auth/login", response_model=LoginResponse)
async def login_user(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Đăng nhập người dùng"""
    
    # Find user by username or email
    user = db.query(User).filter(
        (User.username == login_data.username) | (User.email == login_data.username)
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng")
    
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Tên đăng nhập hoặc mật khẩu không đúng")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Tài khoản đã bị khóa")
    
    db.commit()
    
    # Generate token (placeholder - implement JWT later)
    access_token = f"mock_token_{user.id}_{datetime.now().timestamp()}"
    
    # Get role name
    role_name = None
    if user.role:
        role_name = user.role.role_name
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone=user.phone,
            role=role_name,
            is_active=user.is_active,
            created_at=user.created_at
        )
    )

@app.get("/api/auth/check-username/{username}")
async def check_username(username: str, db: Session = Depends(get_db)):
    """Kiểm tra tên đăng nhập có tồn tại không"""
    user = db.query(User).filter(User.username == username).first()
    return {
        "username": username,
        "available": user is None,
        "message": "Tên đăng nhập có sẵn" if user is None else "Tên đăng nhập đã tồn tại"
    }

@app.get("/api/auth/check-email/{email}")
async def check_email(email: str, db: Session = Depends(get_db)):
    """Kiểm tra email có tồn tại không"""
    user = db.query(User).filter(User.email == email).first()
    return {
        "email": email,
        "available": user is None,
        "message": "Email có sẵn" if user is None else "Email đã được sử dụng"
    }

# =====================================================
# USER ENDPOINTS
# =====================================================

@app.get("/api/users")
async def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Lấy danh sách người dùng"""
    users = db.query(User).offset(skip).limit(limit).all()
    return {
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role.role_name if user.role else None,
                "is_active": user.is_active,
                "created_at": user.created_at
            }
            for user in users
        ],
        "total": len(users)
    }

@app.get("/api/users/{user_id}")
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Lấy thông tin người dùng theo ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "role": user.role.role_name if user.role else None,
        "is_active": user.is_active,
        "created_at": user.created_at
    }

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db)):
    """Cập nhật thông tin người dùng"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate phone if provided
    if user_data.phone and not validate_phone(user_data.phone):
        raise HTTPException(status_code=400, detail="Số điện thoại không hợp lệ")
    
    # Parse date of birth if provided
    if user_data.date_of_birth:
        try:
            user.date_of_birth = datetime.strptime(user_data.date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Ngày sinh phải có định dạng YYYY-MM-DD")
    
    # Update fields
    if user_data.first_name is not None:
        user.first_name = user_data.first_name
    if user_data.last_name is not None:
        user.last_name = user_data.last_name
    if user_data.phone is not None:
        user.phone = user_data.phone
    if user_data.avatar_url is not None:
        user.avatar_url = user_data.avatar_url
    
    user.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(user)
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "role": user.role.role_name if user.role else None,
            "is_active": user.is_active,
            "updated_at": user.updated_at
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật thông tin: {str(e)}")

@app.post("/api/users/{user_id}/change-password")
async def change_password(user_id: int, password_data: PasswordChange, db: Session = Depends(get_db)):
    """Đổi mật khẩu người dùng"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not verify_password(password_data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng")
    
    # Hash new password
    user.password_hash = get_password_hash(password_data.new_password)
    user.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        return {"message": "Mật khẩu đã được thay đổi thành công"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi đổi mật khẩu: {str(e)}")

@app.get("/api/users/{user_id}/addresses")
async def get_user_addresses(user_id: int, db: Session = Depends(get_db)):
    """Lấy danh sách địa chỉ của người dùng"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    addresses = db.query(UserAddress).filter(UserAddress.user_id == user_id).all()
    
    return {
        "addresses": [
            {
                "id": addr.id,
                "recipient_name": addr.recipient_name,
                "phone": addr.phone,
                "address_line1": addr.address_line1,
                "address_line2": addr.address_line2,
                "ward": addr.ward,
                "district": addr.district,
                "city": addr.city,
                "country": addr.country,
                "is_default": addr.is_default,
                "created_at": addr.created_at
            }
            for addr in addresses
        ]
    }

@app.post("/api/users/{user_id}/addresses")
async def create_user_address(user_id: int, address_data: dict, db: Session = Depends(get_db)):
    """Tạo địa chỉ mới cho người dùng"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # If this is set as default, unset other default addresses
    if address_data.get("is_default", False):
        db.query(UserAddress).filter(UserAddress.user_id == user_id).update({"is_default": False})
    
    new_address = UserAddress(
        user_id=user_id,
        recipient_name=address_data["recipient_name"],
        phone=address_data.get("phone"),
        address_line1=address_data["address_line1"],
        address_line2=address_data.get("address_line2"),
        ward=address_data.get("ward"),
        district=address_data.get("district"),
        city=address_data["city"],
        country=address_data.get("country", "Vietnam"),
        is_default=address_data.get("is_default", False)
    )
    
    try:
        db.add(new_address)
        db.commit()
        db.refresh(new_address)
        
        return {
            "id": new_address.id,
            "message": "Địa chỉ đã được thêm thành công"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo địa chỉ: {str(e)}")

# =====================================================
# BOOK ENDPOINTS
# =====================================================

@app.get("/api/books")
async def get_books(
    skip: int = 0, 
    limit: int = 20, 
    category_id: int = None,
    search: str = None,
    db: Session = Depends(get_db)
):
    """Lấy danh sách sách"""
    query = db.query(Book).filter(Book.is_active == True)
    
    if category_id:
        query = query.filter(Book.category_id == category_id)
    
    if search:
        query = query.filter(Book.title.ilike(f"%{search}%"))
    
    books = query.offset(skip).limit(limit).all()
    
    return {
        "books": [
            {
                "id": book.id,
                "title": book.title,
                "slug": book.slug,
                "description": book.description,
                "price": float(book.price),
                "original_price": float(book.original_price) if book.original_price else None,
                "discount_percentage": float(book.discount_percentage),
                "stock_quantity": book.stock_quantity,
                "rating_average": float(book.rating_average),
                "rating_count": book.rating_count,
                "category": {
                    "id": book.category.id if book.category else None,
                    "name": book.category.name if book.category else None
                },
                "publisher": book.publisher.name if book.publisher else None,
                "images": [
                    {
                        "id": img.id,
                        "url": img.image_url,
                        "is_primary": img.is_primary
                    }
                    for img in book.book_images
                ],
                "is_featured": book.is_featured,
                "is_bestseller": book.is_bestseller,
                "created_at": book.created_at
            }
            for book in books
        ],
        "total": len(books)
    }

@app.get("/api/books/{book_id}")
async def get_book(book_id: int, db: Session = Depends(get_db)):
    """Lấy thông tin chi tiết sách"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Lấy authors
    authors = [
        {
            "id": ba.author.id,
            "name": ba.author.pen_name,
            "role": ba.role
        }
        for ba in book.book_authors
    ]
    
    # Lấy images
    images = [
        {
            "id": img.id,
            "url": img.image_url,
            "is_primary": img.is_primary
        }
        for img in book.book_images
    ]
    
    return {
        "id": book.id,
        "title": book.title,
        "subtitle": book.subtitle,
        "slug": book.slug,
        "isbn": book.isbn,
        "description": book.description,
        "price": float(book.price),
        "original_price": float(book.original_price) if book.original_price else None,
        "discount_percentage": float(book.discount_percentage),
        "stock_quantity": book.stock_quantity,
        "rating_average": float(book.rating_average),
        "rating_count": book.rating_count,
        "pages": book.pages,
        "publication_year": book.publication_year,
        "cover_type": book.cover_type,
        "language": book.language,
        "category": {
            "id": book.category.id,
            "name": book.category.name,
            "slug": book.category.slug
        } if book.category else None,
        "publisher": {
            "id": book.publisher.id,
            "name": book.publisher.name
        } if book.publisher else None,
        "authors": authors,
        "images": images,
        "is_featured": book.is_featured,
        "is_bestseller": book.is_bestseller,
        "created_at": book.created_at
    }

@app.post("/api/books/{book_id}/images")
async def add_book_image(
    book_id: int,
    image_data: dict,
    db: Session = Depends(get_db)
):
    """Thêm ảnh cho sách bằng URL"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    new_image = BookImage(
        book_id=book_id,
        image_url=image_data.get('image_url'),
        sort_order=image_data.get('sort_order', 0),
        is_primary=image_data.get('is_primary', False)
    )
    
    try:
        db.add(new_image)
        db.commit()
        db.refresh(new_image)
        
        return {
            "id": new_image.id,
            "book_id": new_image.book_id,
            "image_url": new_image.image_url,
            "message": "Ảnh đã được thêm thành công"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi thêm ảnh: {str(e)}")

@app.post("/api/books/{book_id}/upload-image")
async def upload_book_image(
    book_id: int,
    file: UploadFile = File(...),
    sort_order: int = 0,
    is_primary: bool = False,
    db: Session = Depends(get_db)
):
    """Upload ảnh từ file local"""
    # Kiểm tra sách tồn tại
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Tạo thư mục upload nếu chưa có
    upload_dir = "uploads/books"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Tạo tên file unique
    file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
    unique_filename = f"{book_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    # Lưu file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Lưu URL vào database
        image_url = f"{BASE_URL}/{file_path}"
        new_image = BookImage(
            book_id=book_id,
            image_url=image_url,
            sort_order=sort_order,
            is_primary=is_primary
        )
        
        db.add(new_image)
        db.commit()
        db.refresh(new_image)
        
        return {
            "id": new_image.id,
            "book_id": new_image.book_id,
            "image_url": image_url,
            "message": "Ảnh đã được upload thành công"
        }
    except Exception as e:
        db.rollback()
        # Xóa file nếu có lỗi
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Lỗi khi upload ảnh: {str(e)}")

@app.post("/api/books")
async def create_book(book_data: BookCreate, db: Session = Depends(get_db)):
    """Tạo sách mới (Admin only)"""
    # Generate slug from title
    slug = book_data.title.lower().replace(" ", "-").replace("_", "-")
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    
    # Check if slug exists
    existing_book = db.query(Book).filter(Book.slug == slug).first()
    if existing_book:
        slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Calculate discount percentage
    discount_percentage = 0
    if book_data.original_price and book_data.original_price > book_data.price:
        discount_percentage = ((book_data.original_price - book_data.price) / book_data.original_price) * 100
    
    new_book = Book(
        title=book_data.title,
        subtitle=book_data.subtitle,
        slug=slug,
        isbn=book_data.isbn,
        description=book_data.description,
        publication_year=book_data.publication_year,
        pages=book_data.pages,
        price=book_data.price,
        original_price=book_data.original_price,
        discount_percentage=discount_percentage,
        stock_quantity=book_data.stock_quantity,
        category_id=book_data.category_id,
        publisher_id=book_data.publisher_id,
        language=book_data.language,
        cover_type=book_data.cover_type,
        is_active=True
    )
    
    try:
        db.add(new_book)
        db.commit()
        db.refresh(new_book)
        
        return {
            "id": new_book.id,
            "title": new_book.title,
            "slug": new_book.slug,
            "price": float(new_book.price),
            "message": "Sách đã được tạo thành công"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo sách: {str(e)}")

@app.post("/api/books/create-with-image")
async def create_book_with_image(
    title: str = Form(...),
    description: str = Form(None),
    isbn: str = Form(None),
    publication_year: str = Form(None),
    pages: str = Form(None),
    price: str = Form("0"),
    original_price: str = Form(None),
    stock_quantity: str = Form("0"),
    category_id: str = Form(None),
    publisher_id: str = Form(None),
    supplier_id: str = Form(None),
    language: str = Form("Vietnamese"),
    cover_type: str = Form("paperback"),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Tạo sách mới và upload ảnh cùng lúc"""
    
    # Parse fields
    try:
        publication_year_int = int(publication_year) if publication_year and publication_year != "None" and publication_year != "" else None
        pages_int = int(pages) if pages and pages != "None" and pages != "" else None
        price_float = float(price) if price and price != "None" and price != "" else 0.0
        original_price_float = float(original_price) if original_price and original_price != "None" and original_price != "" else None
        stock_quantity_int = int(stock_quantity) if stock_quantity and stock_quantity != "None" and stock_quantity != "" else 0
        category_id_int = int(category_id) if category_id and category_id != "None" and category_id != "" else None
        publisher_id_int = int(publisher_id) if publisher_id and publisher_id != "None" and publisher_id != "" else None
        supplier_id_int = int(supplier_id) if supplier_id and supplier_id != "None" and supplier_id != "" else None
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid numeric values: {str(e)}")
    
    # Generate slug from title
    slug = title.lower().replace(" ", "-").replace("_", "-")
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    
    # Check if slug exists
    existing_book = db.query(Book).filter(Book.slug == slug).first()
    if existing_book:
        slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Calculate discount percentage
    discount_percentage = 0
    if original_price_float and original_price_float > price_float:
        discount_percentage = ((original_price_float - price_float) / original_price_float) * 100
    
    # Create book
    new_book = Book(
        title=title,
        slug=slug,
        isbn=isbn if isbn and isbn != "None" and isbn != "" else None,
        description=description if description and description != "None" and description != "" else None,
        publication_year=publication_year_int,
        pages=pages_int,
        price=price_float,
        original_price=original_price_float,
        discount_percentage=discount_percentage,
        stock_quantity=stock_quantity_int,
        category_id=category_id_int,
        publisher_id=publisher_id_int,
        supplier_id=supplier_id_int,
        language=language,
        cover_type=cover_type,
        is_active=True
    )
    
    try:
        db.add(new_book)
        db.flush()  # Get the book ID
        
        # Create upload directory
        upload_dir = "uploads/books"
        os.makedirs(upload_dir, exist_ok=True)
        
        uploaded_images = []
        
        # Upload each image
        for index, file in enumerate(files):
            file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
            unique_filename = f"{new_book.id}_{uuid.uuid4().hex[:8]}.{file_extension}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            image_url = f"{BASE_URL}/{file_path}"
            
            # Add image to database
            new_image = BookImage(
                book_id=new_book.id,
                image_url=image_url,
                sort_order=index,
                is_primary=(index == 0)  # First image is primary
            )
            db.add(new_image)
            
            uploaded_images.append({
                "id": new_image.id,
                "image_url": image_url
            })
        
        db.commit()
        db.refresh(new_book)
        
        return {
            "id": new_book.id,
            "title": new_book.title,
            "slug": new_book.slug,
            "price": float(new_book.price),
            "images": uploaded_images,
            "message": "Sách và ảnh đã được tạo thành công"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo sách: {str(e)}")

@app.put("/api/books/{book_id}")
async def update_book(book_id: int, book_data: BookUpdate, db: Session = Depends(get_db)):
    """Cập nhật thông tin sách (Admin only)"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Update fields
    if book_data.title is not None:
        book.title = book_data.title
        # Update slug if title changed
        slug = book_data.title.lower().replace(" ", "-").replace("_", "-")
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        book.slug = slug
    
    if book_data.subtitle is not None:
        book.subtitle = book_data.subtitle
    if book_data.description is not None:
        book.description = book_data.description
    if book_data.price is not None:
        book.price = book_data.price
    if book_data.original_price is not None:
        book.original_price = book_data.original_price
        # Recalculate discount
        if book_data.original_price > book_data.price:
            book.discount_percentage = ((book_data.original_price - book_data.price) / book_data.original_price) * 100
    if book_data.stock_quantity is not None:
        book.stock_quantity = book_data.stock_quantity
    if book_data.is_active is not None:
        book.is_active = book_data.is_active
    if book_data.is_featured is not None:
        book.is_featured = book_data.is_featured
    if book_data.is_bestseller is not None:
        book.is_bestseller = book_data.is_bestseller
    
    book.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(book)
        
        return {
            "id": book.id,
            "title": book.title,
            "price": float(book.price),
            "message": "Sách đã được cập nhật thành công"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật sách: {str(e)}")

@app.delete("/api/books/{book_id}")
async def delete_book(book_id: int, db: Session = Depends(get_db)):
    """Xóa sách (Admin only)"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Soft delete - set is_active to False
    book.is_active = False
    book.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        return {"message": "Sách đã được xóa thành công"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa sách: {str(e)}")

@app.get("/api/books/{book_id}/reviews")
async def get_book_reviews(book_id: int, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """Lấy danh sách đánh giá của sách"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    reviews = db.query(BookReview).filter(
        BookReview.book_id == book_id,
        BookReview.is_approved == True
    ).offset(skip).limit(limit).all()
    
    return {
        "reviews": [
            {
                "id": review.id,
                "user_name": f"{review.user.first_name} {review.user.last_name}",
                "rating": review.rating,
                "title": review.title,
                "comment": review.comment,
                "created_at": review.created_at
            }
            for review in reviews
        ],
        "total": len(reviews),
        "average_rating": float(book.rating_average),
        "rating_count": book.rating_count
    }

@app.post("/api/books/{book_id}/reviews")
async def create_book_review(book_id: int, review_data: BookReviewCreate, user_id: int, db: Session = Depends(get_db)):
    """Tạo đánh giá cho sách"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user already reviewed this book
    existing_review = db.query(BookReview).filter(
        BookReview.book_id == book_id,
        BookReview.user_id == user_id
    ).first()
    
    if existing_review:
        raise HTTPException(status_code=400, detail="Bạn đã đánh giá sách này rồi")
    
    new_review = BookReview(
        book_id=book_id,
        user_id=user_id,
        rating=review_data.rating,
        title=review_data.title,
        comment=review_data.comment,
        is_approved=True
    )
    
    try:
        db.add(new_review)
        
        # Update book rating
        all_reviews = db.query(BookReview).filter(BookReview.book_id == book_id).all()
        if all_reviews:
            total_rating = sum(r.rating for r in all_reviews)
            book.rating_average = total_rating / len(all_reviews)
            book.rating_count = len(all_reviews)
        
        db.commit()
        db.refresh(new_review)
        
        return {
            "id": new_review.id,
            "message": "Đánh giá đã được thêm thành công"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo đánh giá: {str(e)}")

# =====================================================
# CATEGORY ENDPOINTS
# =====================================================

@app.get("/api/categories")
async def get_categories(db: Session = Depends(get_db)):
    """Lấy danh sách thể loại"""
    categories = db.query(Category).filter(Category.is_active == True).all()
    
    return {
        "categories": [
            {
                "id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
                "description": cat.description,
                "parent_id": cat.parent_id,
                "image_url": cat.image_url
            }
            for cat in categories
        ]
    }

# =====================================================
# CART ENDPOINTS
# =====================================================

@app.get("/api/cart/{user_id}")
async def get_cart(user_id: int, db: Session = Depends(get_db)):
    """Lấy giỏ hàng của người dùng"""
    cart_items = db.query(CartItem).filter(CartItem.user_id == user_id).all()
    
    return {
        "cart_items": [
            {
                "id": item.id,
                "book_id": item.book_id,
                "book_title": item.book.title,
                "book_price": float(item.book.price),
                "quantity": item.quantity,
                "total_price": float(item.book.price * item.quantity),
                "added_at": item.added_at
            }
            for item in cart_items
        ],
        "total_items": len(cart_items),
        "total_amount": sum(float(item.book.price * item.quantity) for item in cart_items)
    }

@app.post("/api/cart")
async def add_to_cart(
    user_id: int,
    book_id: int,
    quantity: int = 1,
    db: Session = Depends(get_db)
):
    """Thêm sách vào giỏ hàng"""
    # Kiểm tra sách tồn tại
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Kiểm tra số lượng tồn kho
    if book.stock_quantity < quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")
    
    # Kiểm tra item đã có trong giỏ chưa
    existing_item = db.query(CartItem).filter(
        CartItem.user_id == user_id,
        CartItem.book_id == book_id
    ).first()
    
    if existing_item:
        existing_item.quantity += quantity
    else:
        new_item = CartItem(
            user_id=user_id,
            book_id=book_id,
            quantity=quantity
        )
        db.add(new_item)
    
    db.commit()
    return {"message": "Added to cart successfully"}

@app.put("/api/cart/{cart_item_id}")
async def update_cart_item(cart_item_id: int, cart_data: CartItemUpdate, db: Session = Depends(get_db)):
    """Cập nhật số lượng sản phẩm trong giỏ hàng"""
    cart_item = db.query(CartItem).filter(CartItem.id == cart_item_id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    # Check stock availability
    if cart_data.quantity > cart_item.book.stock_quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")
    
    cart_item.quantity = cart_data.quantity
    cart_item.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        return {"message": "Cart item updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating cart item: {str(e)}")

@app.delete("/api/cart/{cart_item_id}")
async def remove_cart_item(cart_item_id: int, db: Session = Depends(get_db)):
    """Xóa sản phẩm khỏi giỏ hàng"""
    cart_item = db.query(CartItem).filter(CartItem.id == cart_item_id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    try:
        db.delete(cart_item)
        db.commit()
        return {"message": "Item removed from cart successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error removing cart item: {str(e)}")

@app.delete("/api/cart/user/{user_id}")
async def clear_cart(user_id: int, db: Session = Depends(get_db)):
    """Xóa toàn bộ giỏ hàng của người dùng"""
    cart_items = db.query(CartItem).filter(CartItem.user_id == user_id).all()
    
    try:
        for item in cart_items:
            db.delete(item)
        db.commit()
        return {"message": "Cart cleared successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error clearing cart: {str(e)}")

# =====================================================
# WISHLIST ENDPOINTS
# =====================================================

@app.get("/api/wishlist/{user_id}")
async def get_wishlist(user_id: int, db: Session = Depends(get_db)):
    """Lấy danh sách yêu thích của người dùng"""
    wishlist_items = db.query(WishlistItem).filter(WishlistItem.user_id == user_id).all()
    
    return {
        "wishlist_items": [
            {
                "id": item.id,
                "book_id": item.book_id,
                "book_title": item.book.title,
                "book_price": float(item.book.price),
                "book_image": item.book.book_images[0].image_url if item.book.book_images else None,
                "added_at": item.created_at
            }
            for item in wishlist_items
        ],
        "total_items": len(wishlist_items)
    }

@app.post("/api/wishlist")
async def add_to_wishlist(wishlist_data: WishlistItemCreate, user_id: int, db: Session = Depends(get_db)):
    """Thêm sách vào danh sách yêu thích"""
    # Check if book exists
    book = db.query(Book).filter(Book.id == wishlist_data.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Check if already in wishlist
    existing_item = db.query(WishlistItem).filter(
        WishlistItem.user_id == user_id,
        WishlistItem.book_id == wishlist_data.book_id
    ).first()
    
    if existing_item:
        raise HTTPException(status_code=400, detail="Book already in wishlist")
    
    new_item = WishlistItem(
        user_id=user_id,
        book_id=wishlist_data.book_id
    )
    
    try:
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        return {
            "id": new_item.id,
            "message": "Added to wishlist successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding to wishlist: {str(e)}")

@app.delete("/api/wishlist/{wishlist_item_id}")
async def remove_from_wishlist(wishlist_item_id: int, db: Session = Depends(get_db)):
    """Xóa sách khỏi danh sách yêu thích"""
    wishlist_item = db.query(WishlistItem).filter(WishlistItem.id == wishlist_item_id).first()
    if not wishlist_item:
        raise HTTPException(status_code=404, detail="Wishlist item not found")
    
    try:
        db.delete(wishlist_item)
        db.commit()
        return {"message": "Removed from wishlist successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error removing from wishlist: {str(e)}")

# =====================================================
# ORDER ENDPOINTS
# =====================================================

@app.get("/api/orders/{user_id}")
async def get_user_orders(user_id: int, db: Session = Depends(get_db)):
    """Lấy đơn hàng của người dùng"""
    orders = db.query(Order).filter(Order.user_id == user_id).all()
    
    return {
        "orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "status": order.status,
                "total_amount": float(order.total_amount),
                "payment_status": order.payment_status,
                "created_at": order.created_at,
                "items_count": len(order.order_items)
            }
            for order in orders
        ]
    }

@app.post("/api/orders")
async def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    """Tạo đơn hàng mới"""
    # Get user's cart items
    cart_items = db.query(CartItem).filter(CartItem.user_id == order_data.user_id).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Calculate totals
    subtotal = sum(float(item.book.price * item.quantity) for item in cart_items)
    shipping_fee = 0  # TODO: Calculate based on address
    discount_amount = 0  # TODO: Apply voucher discount
    
    total_amount = subtotal + shipping_fee - discount_amount
    
    # Generate order number
    order_number = generate_order_number()
    
    # Create order
    new_order = Order(
        order_number=order_number,
        user_id=order_data.user_id,
        status="pending",
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        discount_amount=discount_amount,
        total_amount=total_amount,
        payment_method_id=order_data.payment_method_id,
        payment_status="pending",
        voucher_id=order_data.voucher_id,
        shipping_address_id=order_data.shipping_address_id,
        notes=order_data.notes
    )
    
    try:
        db.add(new_order)
        db.flush()  # Get the order ID
        
        # Create order items
        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=new_order.id,
                book_id=cart_item.book_id,
                quantity=cart_item.quantity,
                unit_price=cart_item.book.price,
                total_price=cart_item.book.price * cart_item.quantity
            )
            db.add(order_item)
            
            # Update book stock
            cart_item.book.stock_quantity -= cart_item.quantity
            cart_item.book.sold_quantity += cart_item.quantity
        
        # Clear cart
        for cart_item in cart_items:
            db.delete(cart_item)
        
        db.commit()
        db.refresh(new_order)
        
        return {
            "id": new_order.id,
            "order_number": new_order.order_number,
            "total_amount": float(new_order.total_amount),
            "status": new_order.status,
            "message": "Order created successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating order: {str(e)}")

@app.get("/api/orders/{order_id}/details")
async def get_order_details(order_id: int, db: Session = Depends(get_db)):
    """Lấy chi tiết đơn hàng"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get order items
    order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    
    return {
        "order": {
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "subtotal": float(order.subtotal),
            "shipping_fee": float(order.shipping_fee),
            "discount_amount": float(order.discount_amount),
            "total_amount": float(order.total_amount),
            "payment_status": order.payment_status,
            "payment_method": order.payment_method.name if order.payment_method else None,
            "shipping_address": {
                "recipient_name": order.shipping_address.recipient_name,
                "phone": order.shipping_address.phone,
                "address_line1": order.shipping_address.address_line1,
                "address_line2": order.shipping_address.address_line2,
                "city": order.shipping_address.city,
                "district": order.shipping_address.district,
                "ward": order.shipping_address.ward
            } if order.shipping_address else None,
            "tracking_number": order.tracking_number,
            "notes": order.notes,
            "created_at": order.created_at,
            "shipped_at": order.shipped_at,
            "delivered_at": order.delivered_at
        },
        "items": [
            {
                "id": item.id,
                "book_id": item.book_id,
                "book_title": item.book.title,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "total_price": float(item.total_price)
            }
            for item in order_items
        ]
    }

@app.put("/api/orders/{order_id}")
async def update_order(order_id: int, order_data: OrderUpdate, db: Session = Depends(get_db)):
    """Cập nhật trạng thái đơn hàng (Admin only)"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update fields
    if order_data.status is not None:
        order.status = order_data.status
        
        # Set timestamps based on status
        if order_data.status == "shipped":
            order.shipped_at = datetime.utcnow()
        elif order_data.status == "delivered":
            order.delivered_at = datetime.utcnow()
    
    if order_data.payment_status is not None:
        order.payment_status = order_data.payment_status
    
    if order_data.tracking_number is not None:
        order.tracking_number = order_data.tracking_number
    
    if order_data.notes is not None:
        order.notes = order_data.notes
    
    order.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        return {"message": "Order updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating order: {str(e)}")

@app.post("/api/orders/{order_id}/cancel")
async def cancel_order(order_id: int, reason: str = None, db: Session = Depends(get_db)):
    """Hủy đơn hàng"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if order can be cancelled
    if order.status in ["delivered", "cancelled"]:
        raise HTTPException(status_code=400, detail="Order cannot be cancelled")
    
    # Update order status
    order.status = "cancelled"
    order.cancelled_at = datetime.utcnow()
    order.cancellation_reason = reason
    
    # Restore stock
    for item in order.order_items:
        item.book.stock_quantity += item.quantity
        item.book.sold_quantity -= item.quantity
    
    try:
        db.commit()
        return {"message": "Order cancelled successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error cancelling order: {str(e)}")

# =====================================================
# STATISTICS ENDPOINTS
# =====================================================

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Lấy thống kê tổng quan"""
    total_users = db.query(User).count()
    total_books = db.query(Book).filter(Book.is_active == True).count()
    total_orders = db.query(Order).count()
    total_categories = db.query(Category).filter(Category.is_active == True).count()
    
    return {
        "total_users": total_users,
        "total_books": total_books,
        "total_orders": total_orders,
        "total_categories": total_categories
    }

# =====================================================
# ADMIN ENDPOINTS
# =====================================================

@app.get("/api/admin/orders")
async def get_all_orders(skip: int = 0, limit: int = 50, status: str = None, db: Session = Depends(get_db)):
    """Lấy tất cả đơn hàng (Admin only)"""
    query = db.query(Order)
    
    if status:
        query = query.filter(Order.status == status)
    
    orders = query.offset(skip).limit(limit).all()
    
    return {
        "orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "user_name": f"{order.user.first_name} {order.user.last_name}",
                "user_email": order.user.email,
                "status": order.status,
                "total_amount": float(order.total_amount),
                "payment_status": order.payment_status,
                "created_at": order.created_at,
                "items_count": len(order.order_items)
            }
            for order in orders
        ],
        "total": len(orders)
    }

@app.get("/api/admin/users")
async def get_all_users(skip: int = 0, limit: int = 50, role: str = None, db: Session = Depends(get_db)):
    """Lấy tất cả người dùng (Admin only)"""
    query = db.query(User)
    
    if role:
        query = query.join(UserRole).filter(UserRole.role_name == role)
    
    users = query.offset(skip).limit(limit).all()
    
    return {
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role.role_name if user.role else None,
                "is_active": user.is_active,
                "created_at": user.created_at
            }
            for user in users
        ],
        "total": len(users)
    }

@app.put("/api/admin/users/{user_id}/status")
async def update_user_status(user_id: int, is_active: bool, db: Session = Depends(get_db)):
    """Cập nhật trạng thái người dùng (Admin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = is_active
    user.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        return {"message": f"User {'activated' if is_active else 'deactivated'} successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating user status: {str(e)}")

@app.get("/api/admin/books")
async def get_all_books_admin(skip: int = 0, limit: int = 50, is_active: bool = None, db: Session = Depends(get_db)):
    """Lấy tất cả sách (Admin only)"""
    query = db.query(Book)
    
    if is_active is not None:
        query = query.filter(Book.is_active == is_active)
    
    books = query.offset(skip).limit(limit).all()
    
    return {
        "books": [
            {
                "id": book.id,
                "title": book.title,
                "price": float(book.price),
                "stock_quantity": book.stock_quantity,
                "sold_quantity": book.sold_quantity,
                "is_active": book.is_active,
                "is_featured": book.is_featured,
                "is_bestseller": book.is_bestseller,
                "rating_average": float(book.rating_average),
                "rating_count": book.rating_count,
                "created_at": book.created_at
            }
            for book in books
        ],
        "total": len(books)
    }

@app.get("/api/admin/dashboard")
async def get_admin_dashboard(db: Session = Depends(get_db)):
    """Lấy thống kê dashboard admin"""
    # Basic stats
    total_users = db.query(User).count()
    total_books = db.query(Book).count()
    total_orders = db.query(Order).count()
    total_revenue = db.query(Order).filter(Order.payment_status == "paid").with_entities(
        db.func.sum(Order.total_amount)
    ).scalar() or 0
    
    # Recent orders
    recent_orders = db.query(Order).order_by(Order.created_at.desc()).limit(5).all()
    
    # Top selling books
    top_books = db.query(Book).order_by(Book.sold_quantity.desc()).limit(5).all()
    
    # Order status distribution
    order_statuses = db.query(Order.status, db.func.count(Order.id)).group_by(Order.status).all()
    
    return {
        "stats": {
            "total_users": total_users,
            "total_books": total_books,
            "total_orders": total_orders,
            "total_revenue": float(total_revenue)
        },
        "recent_orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "user_name": f"{order.user.first_name} {order.user.last_name}",
                "total_amount": float(order.total_amount),
                "status": order.status,
                "created_at": order.created_at
            }
            for order in recent_orders
        ],
        "top_books": [
            {
                "id": book.id,
                "title": book.title,
                "sold_quantity": book.sold_quantity,
                "price": float(book.price)
            }
            for book in top_books
        ],
        "order_statuses": [
            {"status": status, "count": count}
            for status, count in order_statuses
        ]
    }

# =====================================================
# SEARCH ENDPOINTS
# =====================================================

@app.get("/api/search/books")
async def search_books(
    q: str,
    category_id: int = None,
    min_price: float = None,
    max_price: float = None,
    sort_by: str = "relevance",
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Tìm kiếm sách"""
    query = db.query(Book).filter(Book.is_active == True)
    
    # Text search
    if q:
        query = query.filter(
            db.or_(
                Book.title.ilike(f"%{q}%"),
                Book.description.ilike(f"%{q}%"),
            )
        )
    
    # Category filter
    if category_id:
        query = query.filter(Book.category_id == category_id)
    
    # Price filter
    if min_price is not None:
        query = query.filter(Book.price >= min_price)
    if max_price is not None:
        query = query.filter(Book.price <= max_price)
    
    # Sorting
    if sort_by == "price_asc":
        query = query.order_by(Book.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(Book.price.desc())
    elif sort_by == "rating":
        query = query.order_by(Book.rating_average.desc())
    elif sort_by == "newest":
        query = query.order_by(Book.created_at.desc())
    else:  # relevance
        query = query.order_by(Book.rating_average.desc(), Book.sold_quantity.desc())
    
    books = query.offset(skip).limit(limit).all()
    
    return {
        "books": [
            {
                "id": book.id,
                "title": book.title,
                "slug": book.slug,
                "price": float(book.price),
                "original_price": float(book.original_price) if book.original_price else None,
                "discount_percentage": float(book.discount_percentage),
                "rating_average": float(book.rating_average),
                "rating_count": book.rating_count,
                "category": book.category.name if book.category else None,
                "publisher": book.publisher.name if book.publisher else None,
                "is_featured": book.is_featured,
                "is_bestseller": book.is_bestseller
            }
            for book in books
        ],
        "total": len(books),
        "query": q,
        "filters": {
            "category_id": category_id,
            "min_price": min_price,
            "max_price": max_price
        }
    }

# =====================================================
# STARTUP EVENT
# =====================================================
# (Moved to top of file)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


