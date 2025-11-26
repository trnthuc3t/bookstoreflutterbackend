
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.requests import Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import text, func
import os
from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import bcrypt
from datetime import datetime, timedelta
import re
import uuid
import secrets
from typing import Optional, List
import shutil

load_dotenv()

BASE_URL = os.getenv('BASE_URL', 'https://xrjssx4r-7000.asse.devtunnels.ms')
print(f"Using BASE_URL: {BASE_URL}")

from database import get_db, engine, Base
from models import *
from email_service import EmailService
# Import JWT utilities
from jwt_utils import (
    create_tokens_for_user,
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    refresh_access_token
)


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
    print("BookStore API starting...")
    
    # Create uploads directory
    upload_dir = "uploads/books"
    os.makedirs(upload_dir, exist_ok=True)
    print("Upload directory created")
    
    # Auto-create tables
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables checked/created")
    except Exception as e:
        print(f"Warning: Could not create tables: {e}")
        print("Tip: Run: python setup_database.py to setup database")
    
    print("API Documentation available at /docs")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên chỉ định domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if it doesn't exist
upload_dir = os.path.join(os.getcwd(), "uploads")
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir, exist_ok=True)
    print(f"Created uploads directory: {upload_dir}")

# Mount static files for uploaded images
try:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
    print("Static files mounted at /uploads")
except Exception as e:
    print(f"Warning: Could not mount static files: {e}")

# Security
security = HTTPBearer()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# PYDANTIC MODELS

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
    discount_percentage: Optional[float] = None
    stock_quantity: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_bestseller: Optional[bool] = None
    # Additional fields for complete update
    category_id: Optional[int] = None
    publisher_id: Optional[int] = None
    supplier_id: Optional[int] = None
    language: Optional[str] = None
    cover_type: Optional[str] = None
    pages: Optional[int] = None
    publication_year: Optional[int] = None
    length: Optional[float] = None
    width: Optional[float] = None
    thickness: Optional[float] = None
    weight: Optional[int] = None

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

# HELPER FUNCTIONS

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
    cleaned_phone = re.sub(r'[\s\-\(\)]', '', phone)  
    pattern = r'^(\+?84|0)[0-9]{9,10}$'
    return re.match(pattern, cleaned_phone) is not None

def generate_order_number():
    return f"ORD-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

# Note: get_current_user is now imported from jwt_utils

# HEALTH CHECK ENDPOINTS

@app.get("/")
async def root():
    return {
        "message": "Welcome to BookStore API",
        "version": "1.0.0",
        "docs": "/docs",
        "status": "running"
    }

@app.get("/health")
async def health_check():
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

# AUTHENTICATION ENDPOINTS

@app.post("/api/auth/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Đăng ký tài khoản người dùng mới"""
    
    if not validate_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email không hợp lệ")
    
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
        
        # Tạo verification token
        verification_token = secrets.token_urlsafe(32)
        token_expires = datetime.utcnow() + timedelta(hours=24)
        
        email_token = EmailVerificationToken(
            user_id=new_user.id,
            token=verification_token,
            expires_at=token_expires
        )
        db.add(email_token)
        db.commit()
        
        # Gửi email xác thực
        verification_link = f"{BASE_URL}/api/auth/verify-email/{verification_token}"
        try:
            EmailService.send_verification_email(
                to_email=new_user.email,
                username=new_user.username,
                verification_link=verification_link
            )
            print(f"📧 Verification email sent to {new_user.email}")
        except Exception as e:
            print(f"⚠️ Failed to send verification email: {str(e)}")
        
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
    """Đăng nhập người dùng với JWT authentication"""
    
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
    
    # Update last login time
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Generate JWT tokens
    tokens = create_tokens_for_user(user)
    
    # Get role name
    role_name = None
    if user.role:
        role_name = user.role.role_name
    
    return LoginResponse(
        access_token=tokens["access_token"],
        token_type=tokens["token_type"],
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

@app.post("/api/auth/refresh")
async def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    try:
        result = refresh_access_token(refresh_token, db)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

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

@app.get("/api/auth/verify-email/{token}", response_class=HTMLResponse)
async def verify_email(token: str, db: Session = Depends(get_db)):
    """Xác thực email bằng token - Trả về HTML cho browser"""
    
    # Tìm token
    email_token = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == token,
        EmailVerificationToken.is_used == False
    ).first()
    
    if not email_token:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Xác thực thất bại - BookStore</title>
            <style>
                body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
                .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); text-align: center; max-width: 500px; }
                .icon { font-size: 60px; margin-bottom: 20px; }
                h1 { color: #f44336; margin-bottom: 20px; }
                p { color: #666; line-height: 1.6; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">❌</div>
                <h1>Xác thực thất bại</h1>
                <p>Token không hợp lệ hoặc đã được sử dụng. Vui lòng thử đăng ký lại hoặc liên hệ hỗ trợ.</p>
            </div>
        </body>
        </html>
        """, status_code=400)
    
    # Kiểm tra token đã hết hạn chưa
    if datetime.utcnow() > email_token.expires_at:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Token hết hạn - BookStore</title>
            <style>
                body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
                .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); text-align: center; max-width: 500px; }
                .icon { font-size: 60px; margin-bottom: 20px; }
                h1 { color: #ff9800; margin-bottom: 20px; }
                p { color: #666; line-height: 1.6; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">⏰</div>
                <h1>Token đã hết hạn</h1>
                <p>Link xác thực đã hết hạn sau 24 giờ. Vui lòng đăng nhập và yêu cầu gửi lại email xác thực.</p>
            </div>
        </body>
        </html>
        """, status_code=400)
    
    # Lấy user
    user = db.query(User).filter(User.id == email_token.user_id).first()
    if not user:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Lỗi - BookStore</title>
            <style>
                body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
                .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); text-align: center; max-width: 500px; }
                .icon { font-size: 60px; margin-bottom: 20px; }
                h1 { color: #f44336; margin-bottom: 20px; }
                p { color: #666; line-height: 1.6; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">❌</div>
                <h1>Lỗi</h1>
                <p>Người dùng không tồn tại. Vui lòng liên hệ hỗ trợ.</p>
            </div>
        </body>
        </html>
        """, status_code=404)
    
    # Cập nhật user
    user.email_verified = True
    email_token.is_used = True
    
    try:
        db.commit()
        
        # Gửi email chào mừng
        try:
            EmailService.send_welcome_email(user.email, user.username)
        except Exception as e:
            print(f"⚠️ Failed to send welcome email: {str(e)}")
        
        # Trả về HTML thành công
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Xác thực thành công - BookStore</title>
            <style>
                body {{ font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                .container {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); text-align: center; max-width: 500px; }}
                .icon {{ font-size: 60px; margin-bottom: 20px; }}
                h1 {{ color: #4CAF50; margin-bottom: 20px; }}
                p {{ color: #666; line-height: 1.6; margin-bottom: 10px; }}
                .username {{ font-weight: bold; color: #2196F3; }}
                .info {{ background: #f0f9ff; padding: 15px; border-radius: 8px; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">✅</div>
                <h1>Xác thực email thành công!</h1>
                <p>Chào mừng <span class="username">{user.username}</span> đến với BookStore!</p>
                <p>Email <strong>{user.email}</strong> đã được xác thực.</p>
                <div class="info">
                    <p>🎉 Bạn đã có thể đăng nhập và sử dụng đầy đủ tính năng của BookStore.</p>
                    <p>📧 Chúng tôi đã gửi email chào mừng đến bạn.</p>
                </div>
            </div>
        </body>
        </html>
        """)
    except Exception as e:
        db.rollback()
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Lỗi - BookStore</title>
            <style>
                body {{ font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
                .container {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); text-align: center; max-width: 500px; }}
                .icon {{ font-size: 60px; margin-bottom: 20px; }}
                h1 {{ color: #f44336; margin-bottom: 20px; }}
                p {{ color: #666; line-height: 1.6; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">❌</div>
                <h1>Lỗi xác thực</h1>
                <p>Đã xảy ra lỗi khi xác thực email: {str(e)}</p>
                <p>Vui lòng thử lại sau hoặc liên hệ hỗ trợ.</p>
            </div>
        </body>
        </html>
        """, status_code=500)

@app.post("/api/auth/resend-verification")
async def resend_verification(email: str, db: Session = Depends(get_db)):
    """Gửi lại email xác thực"""
    
    # Tìm user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Email không tồn tại trong hệ thống")
    
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email đã được xác thực")
    
    # Xóa các token cũ chưa sử dụng
    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.is_used == False
    ).delete()
    
    # Tạo token mới
    verification_token = secrets.token_urlsafe(32)
    token_expires = datetime.utcnow() + timedelta(hours=24)
    
    email_token = EmailVerificationToken(
        user_id=user.id,
        token=verification_token,
        expires_at=token_expires
    )
    db.add(email_token)
    db.commit()
    
    # Gửi email
    verification_link = f"{BASE_URL}/api/auth/verify-email/{verification_token}"
    try:
        EmailService.send_verification_email(
            to_email=user.email,
            username=user.username,
            verification_link=verification_link
        )
        return {"message": "Email xác thực đã được gửi lại"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi gửi email: {str(e)}")

@app.post("/api/auth/forgot-password")
async def forgot_password(email: str, db: Session = Depends(get_db)):
    """Gửi email đặt lại mật khẩu"""
    
    # Tìm user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # Không tiết lộ email có tồn tại hay không vì lý do bảo mật
        return {"message": "Nếu email tồn tại trong hệ thống, bạn sẽ nhận được email hướng dẫn đặt lại mật khẩu"}
    
    # Xóa các token reset cũ chưa sử dụng
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.is_used == False
    ).delete()
    
    # Tạo token mới
    reset_token = secrets.token_urlsafe(32)
    token_expires = datetime.utcnow() + timedelta(hours=1)  # Token hết hạn sau 1 giờ
    
    password_token = PasswordResetToken(
        user_id=user.id,
        token=reset_token,
        expires_at=token_expires
    )
    db.add(password_token)
    db.commit()
    
    # Gửi email
    reset_link = f"{BASE_URL}/api/auth/reset-password-page?token={reset_token}"
    try:
        EmailService.send_password_reset_email(
            to_email=user.email,
            username=user.username,
            reset_link=reset_link
        )
        print(f" Password reset email sent to {user.email}")
    except Exception as e:
        print(f" Failed to send password reset email: {str(e)}")
    
    return {"message": "Nếu email tồn tại trong hệ thống, bạn sẽ nhận được email hướng dẫn đặt lại mật khẩu"}

@app.get("/api/auth/reset-password-page", response_class=HTMLResponse)
async def reset_password_page(token: str, db: Session = Depends(get_db)):
    """Hiển thị form reset password - Trả về HTML cho browser"""
    
    # Tìm token
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.is_used == False
    ).first()
    
    if not reset_token:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Token không hợp lệ - BookStore</title>
            <style>
                body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
                .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); text-align: center; max-width: 500px; }
                .icon { font-size: 60px; margin-bottom: 20px; }
                h1 { color: #f44336; margin-bottom: 20px; }
                p { color: #666; line-height: 1.6; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon"></div>
                <h1>Token không hợp lệ</h1>
                <p>Token không hợp lệ hoặc đã được sử dụng. Vui lòng yêu cầu đặt lại mật khẩu lại.</p>
            </div>
        </body>
        </html>
        """, status_code=400)
    
    # Kiểm tra token đã hết hạn chưa
    if datetime.utcnow() > reset_token.expires_at:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Token hết hạn - BookStore</title>
            <style>
                body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
                .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); text-align: center; max-width: 500px; }
                .icon { font-size: 60px; margin-bottom: 20px; }
                h1 { color: #ff9800; margin-bottom: 20px; }
                p { color: #666; line-height: 1.6; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">⏰</div>
                <h1>Token đã hết hạn</h1>
                <p>Link đặt lại mật khẩu đã hết hạn sau 1 giờ. Vui lòng yêu cầu đặt lại mật khẩu lại.</p>
            </div>
        </body>
        </html>
        """, status_code=400)
    
    # Lấy user
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Lỗi - BookStore</title>
            <style>
                body { font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
                .container { background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); text-align: center; max-width: 500px; }
                .icon { font-size: 60px; margin-bottom: 20px; }
                h1 { color: #f44336; margin-bottom: 20px; }
                p { color: #666; line-height: 1.6; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon"></div>
                <h1>Lỗi</h1>
                <p>Người dùng không tồn tại.</p>
            </div>
        </body>
        </html>
        """, status_code=404)
    
    # Hiển thị form đặt lại mật khẩu
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Đặt lại mật khẩu - BookStore</title>
        <style>
            body {{ font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
            .container {{ background: white; padding: 40px; border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); max-width: 500px; width: 100%; }}
            .icon {{ font-size: 60px; margin-bottom: 20px; text-align: center; }}
            h1 {{ color: #333; margin-bottom: 10px; text-align: center; }}
            p {{ color: #666; text-align: center; margin-bottom: 30px; }}
            .form-group {{ margin-bottom: 20px; }}
            label {{ display: block; margin-bottom: 5px; color: #333; font-weight: bold; }}
            input {{ width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 5px; font-size: 16px; box-sizing: border-box; }}
            button {{ width: 100%; padding: 12px; background: #2196F3; color: white; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; font-weight: bold; }}
            button:hover {{ background: #1976D2; }}
            .error {{ color: #f44336; margin-top: 10px; text-align: center; }}
            .success {{ color: #4CAF50; margin-top: 10px; text-align: center; }}
            .info {{ background: #fff3cd; padding: 10px; border-radius: 5px; margin-bottom: 20px; border: 1px solid #ffc107; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon"></div>
            <h1>Đặt lại mật khẩu</h1>
            <p>Xin chào <strong>{user.username}</strong>, vui lòng nhập mật khẩu mới</p>
            <div class="info">
                <small> Mật khẩu phải có ít nhất 6 ký tự</small>
            </div>
            <form id="resetForm">
                <div class="form-group">
                    <label for="password">Mật khẩu mới:</label>
                    <input type="password" id="password" name="password" required minlength="6">
                </div>
                <div class="form-group">
                    <label for="confirmPassword">Xác nhận mật khẩu:</label>
                    <input type="password" id="confirmPassword" name="confirmPassword" required minlength="6">
                </div>
                <button type="submit">Đặt lại mật khẩu</button>
                <div id="message"></div>
            </form>
        </div>
        <script>
            document.getElementById('resetForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                const password = document.getElementById('password').value;
                const confirmPassword = document.getElementById('confirmPassword').value;
                const messageDiv = document.getElementById('message');
                
                if (password !== confirmPassword) {{
                    messageDiv.innerHTML = '<p class="error">Mật khẩu xác nhận không khớp!</p>';
                    return;
                }}
                
                if (password.length < 6) {{
                    messageDiv.innerHTML = '<p class="error">Mật khẩu phải có ít nhất 6 ký tự!</p>';
                    return;
                }}
                
                try {{
                    const response = await fetch('{BASE_URL}/api/auth/reset-password', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            token: '{token}',
                            new_password: password
                        }})
                    }});
                    
                    const data = await response.json();
                    
                    if (response.ok) {{
                        messageDiv.innerHTML = '<p class="success">' + data.message + '</p>';
                        document.getElementById('resetForm').innerHTML = '<p class="success">Đặt lại mật khẩu thành công! Bạn có thể đăng nhập ngay bây giờ.</p>';
                    }} else {{
                        messageDiv.innerHTML = '<p class="error"> ' + data.detail + '</p>';
                    }}
                }} catch (error) {{
                    messageDiv.innerHTML = '<p class="error"> Lỗi kết nối server</p>';
                }}
            }});
        </script>
    </body>
    </html>
    """)

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@app.post("/api/auth/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Đặt lại mật khẩu bằng token"""
    
    # Tìm token
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == request.token,
        PasswordResetToken.is_used == False
    ).first()
    
    if not reset_token:
        raise HTTPException(status_code=400, detail="Token không hợp lệ hoặc đã được sử dụng")
    
    # Kiểm tra token đã hết hạn chưa
    if datetime.utcnow() > reset_token.expires_at:
        raise HTTPException(status_code=400, detail="Token đã hết hạn")
    
    # Lấy user
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Người dùng không tồn tại")
    
    # Validate mật khẩu mới
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 6 ký tự")
    
    # Cập nhật mật khẩu
    user.password_hash = get_password_hash(request.new_password)
    reset_token.is_used = True
    
    try:
        db.commit()
        return {
            "message": "Mật khẩu đã được đặt lại thành công",
            "username": user.username
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi đặt lại mật khẩu: {str(e)}")

# =====================================================
# USER ENDPOINTS
# =====================================================

@app.get("/api/users")
async def get_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách người dùng (Admin only)"""
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
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy thông tin người dùng theo ID"""
    # Users can only view their own profile unless they're admin
    if current_user.id != user_id and current_user.role.role_name != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this user")
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
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cập nhật thông tin người dùng"""
    # Users can only update their own profile unless they're admin
    if current_user.id != user_id and current_user.role.role_name != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update this user")
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
async def change_password(
    user_id: int,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Users can only change their own password
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to change this password")
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
async def get_user_addresses(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Users can only view their own addresses unless they're admin
    if current_user.id != user_id and current_user.role.role_name != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view these addresses")
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
async def create_user_address(
    user_id: int,
    address_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Tạo địa chỉ mới cho người dùng"""
    # Users can only create addresses for themselves
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to create address for this user")
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

@app.put("/api/users/{user_id}/addresses/{address_id}")
async def update_user_address(
    user_id: int,
    address_id: int,
    address_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cập nhật địa chỉ của người dùng"""
    # Users can only update their own addresses
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this address")
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get the address
    address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == user_id
    ).first()
    
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    # If this is set as default, unset other default addresses
    if address_data.get("is_default", False):
        db.query(UserAddress).filter(
            UserAddress.user_id == user_id,
            UserAddress.id != address_id
        ).update({"is_default": False})
    
    # Update address fields
    address.recipient_name = address_data.get("recipient_name", address.recipient_name)
    address.phone = address_data.get("phone", address.phone)
    address.address_line1 = address_data.get("address_line1", address.address_line1)
    address.address_line2 = address_data.get("address_line2", address.address_line2)
    address.ward = address_data.get("ward", address.ward)
    address.district = address_data.get("district", address.district)
    address.city = address_data.get("city", address.city)
    address.country = address_data.get("country", address.country)
    address.is_default = address_data.get("is_default", address.is_default)
    address.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(address)
        
        return {
            "id": address.id,
            "message": "Địa chỉ đã được cập nhật thành công"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật địa chỉ: {str(e)}")

@app.delete("/api/users/{user_id}/addresses/{address_id}")
async def delete_user_address(
    user_id: int,
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xóa địa chỉ của người dùng"""
    # Users can only delete their own addresses
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this address")
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get the address
    address = db.query(UserAddress).filter(
        UserAddress.id == address_id,
        UserAddress.user_id == user_id
    ).first()
    
    if not address:
        raise HTTPException(status_code=404, detail="Address not found")
    
    # Check if there are any orders using this address
    orders_using_address = db.query(Order).filter(
        Order.shipping_address_id == address_id
    ).count()
    
    if orders_using_address > 0:
        raise HTTPException(
            status_code=400, 
            detail="Không thể xóa địa chỉ này vì đang được sử dụng trong đơn hàng"
        )
    
    try:
        db.delete(address)
        db.commit()
        
        return {
            "message": "Địa chỉ đã được xóa thành công"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa địa chỉ: {str(e)}")

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
                "sold_quantity": book.sold_quantity,
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
@app.get("/api/books/featured")
async def get_featured_books(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """Lấy danh sách sách nổi bật"""
    books = db.query(Book).filter(
        Book.is_active == True,
        Book.is_featured == True
    ).order_by(Book.rating_average.desc(), Book.sold_quantity.desc()).offset(skip).limit(limit).all()
    
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
                "sold_quantity": book.sold_quantity,
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

@app.get("/api/books/bestsellers")
async def get_bestseller_books(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """Lấy danh sách sách bán chạy"""
    books = db.query(Book).filter(
        Book.is_active == True,
        Book.is_bestseller == True
    ).order_by(Book.sold_quantity.desc(), Book.rating_average.desc()).offset(skip).limit(limit).all()
    
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
                "sold_quantity": book.sold_quantity,
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
    
    # Lấy images - sắp xếp theo sort_order và is_primary
    images = sorted(
        [
            {
                "id": img.id,
                "url": img.image_url,
                "is_primary": img.is_primary,
                "sort_order": img.sort_order
            }
            for img in book.book_images
        ],
        key=lambda x: (x['is_primary'], x['sort_order'])
    )
    
    # Lấy ảnh chính (primary image)
    primary_image = None
    if images:
        primary_image = next((img for img in images if img['is_primary']), images[0])
    
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
        "sold_quantity": book.sold_quantity,
        "rating_average": float(book.rating_average),
        "rating_count": book.rating_count,
        "pages": book.pages,
        "publication_year": book.publication_year,
        "cover_type": book.cover_type,
        "language": book.language,
        # Dimensions and weight
        "length": float(book.length) if book.length else None,
        "width": float(book.width) if book.width else None,
        "thickness": float(book.thickness) if book.thickness else None,
        "weight": book.weight,
        "category": {
            "id": book.category.id,
            "name": book.category.name,
            "slug": book.category.slug
        } if book.category else None,
        "category_id": book.category_id,
        "category_name": book.category.name if book.category else None,
        "publisher": {
            "id": book.publisher.id,
            "name": book.publisher.name
        } if book.publisher else None,
        "publisher_name": book.publisher.name if book.publisher else None,
        "supplier": {
            "id": book.supplier.id,
            "name": book.supplier.name
        } if book.supplier else None,
        "supplier_name": book.supplier.name if book.supplier else None,
        "authors": authors,
        "images": images,
        "primary_image": primary_image,
        "is_active": book.is_active,
        "is_featured": book.is_featured,
        "is_bestseller": book.is_bestseller,
        "created_at": book.created_at
    }

@app.get("/api/books/{book_id}/images")
async def get_book_images(book_id: int, db: Session = Depends(get_db)):
    """Lấy danh sách ảnh của sách theo ID"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Lấy images - sắp xếp theo sort_order và is_primary
    images = sorted(
        [
            {
                "id": img.id,
                "url": img.image_url,
                "is_primary": img.is_primary,
                "sort_order": img.sort_order,
                "created_at": img.created_at
            }
            for img in book.book_images
        ],
        key=lambda x: (x['is_primary'], x['sort_order'])
    )
    
    # Lấy ảnh chính
    primary_image = next((img for img in images if img['is_primary']), images[0] if images else None)
    
    return {
        "book_id": book_id,
        "book_title": book.title,
        "images": images,
        "primary_image": primary_image,
        "total_images": len(images)
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
        
        # Convert Windows path to URL path (relative path only)
        url_path = file_path.replace("\\", "/")
        # Store relative path instead of absolute URL
        image_url = f"/{url_path}"  # /uploads/books/xxx.jpg

        print(f"Image saved with relative path: {image_url}")  # Debug log
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

@app.post("/api/books/{book_id}/upload-multiple-images")
async def upload_multiple_book_images(
    book_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload nhiều ảnh cho sách đã tồn tại"""
    # Kiểm tra sách tồn tại
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # Tạo thư mục upload nếu chưa có
    upload_dir = "uploads/books"
    os.makedirs(upload_dir, exist_ok=True)
    
    uploaded_images = []
    
    try:
        # Get current max sort_order
        existing_images = db.query(BookImage).filter(BookImage.book_id == book_id).all()
        max_sort_order = max([img.sort_order for img in existing_images], default=-1)
        
        # Upload each image
        for index, file in enumerate(files):
            file_extension = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
            unique_filename = f"{book_id}_{uuid.uuid4().hex[:8]}.{file_extension}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Convert Windows path to URL path (relative path only)
            url_path = file_path.replace("\\", "/")
            # Store relative path instead of absolute URL
            image_url = f"/{url_path}"  # /uploads/books/xxx.jpg

            print(f"Saving image {index+1} with relative path: {image_url}")
            
            # Add image to database
            new_image = BookImage(
                book_id=book_id,
                image_url=image_url,
                sort_order=max_sort_order + index + 1,
                is_primary=False  # New images are not primary by default
            )
            db.add(new_image)
            
            uploaded_images.append({
                "url": image_url,
                "sort_order": max_sort_order + index + 1
            })
        
        db.commit()
        
        print(f"Uploaded {len(uploaded_images)} images for book #{book_id}")
        
        return {
            "book_id": book_id,
            "uploaded_count": len(uploaded_images),
            "images": uploaded_images,
            "message": f"Đã upload {len(uploaded_images)} ảnh thành công"
        }
    except Exception as e:
        db.rollback()
        print(f"Error uploading images: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi upload ảnh: {str(e)}")

@app.post("/api/books")
async def create_book(
    book_data: BookCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
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
    length: str = Form(None),
    width: str = Form(None),
    thickness: str = Form(None),
    weight: str = Form(None),
    author_ids: str = Form(None),  # Comma-separated author IDs
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
        # Parse dimensions and weight
        length_float = float(length) if length and length != "None" and length != "" else None
        width_float = float(width) if width and width != "None" and width != "" else None
        thickness_float = float(thickness) if thickness and thickness != "None" and thickness != "" else None
        weight_int = int(weight) if weight and weight != "None" and weight != "" else None
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
        length=length_float,
        width=width_float,
        thickness=thickness_float,
        weight=weight_int,
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
            
            # Convert Windows path to URL path (relative path only)
            url_path = file_path.replace("\\", "/")
            # Store relative path instead of absolute URL
            image_url = f"/{url_path}"  # /uploads/books/xxx.jpg

            print(f"Saving image with relative path: {image_url}")  # Debug log
            
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
                "url": image_url,  # Changed from "image_url" to "url" to match API response
                "is_primary": (index == 0)
            })
        
        # Add authors if provided
        if author_ids and author_ids.strip():
            author_id_list = [int(aid.strip()) for aid in author_ids.split(',') if aid.strip()]
            print(f"👤 Adding {len(author_id_list)} authors to book")
            
            for author_id in author_id_list:
                # Check if author exists
                author = db.query(Author).filter(Author.id == author_id).first()
                if author:
                    book_author = BookAuthor(
                        book_id=new_book.id,
                        author_id=author_id,
                        role='author'
                    )
                    db.add(book_author)
                    print(f" Added author: {author.pen_name}")
        
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
async def update_book(
    book_id: int,
    book_data: BookUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
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
    
    # Handle price and discount logic
    # First, update original_price if provided
    if book_data.original_price is not None:
        book.original_price = book_data.original_price
    
    # Then handle discount or price update
    if book_data.discount_percentage is not None:
        # If discount_percentage is provided, calculate price from original_price
        book.discount_percentage = book_data.discount_percentage
        if book.original_price and book.original_price > 0:
            # Convert to float to avoid Decimal * float TypeError
            book.price = float(book.original_price) * (1 - float(book.discount_percentage) / 100)
            print(f"💰 Calculated price from discount: {book.original_price} * (1 - {book.discount_percentage}/100) = {book.price}")
        else:
            print(f"⚠️ Cannot calculate price: original_price is {book.original_price}")
    elif book_data.price is not None:
        # If price is provided directly
        old_price = book.price
        book.price = book_data.price
        print(f"💰 Price updated: {old_price} -> {book.price}")
        
        # Recalculate discount percentage if we have original_price
        if book.original_price and book.original_price > 0:
            if book.price < book.original_price:
                # Convert to float to avoid Decimal arithmetic issues
                book.discount_percentage = ((float(book.original_price) - float(book.price)) / float(book.original_price)) * 100
                print(f"📊 Calculated discount: {book.discount_percentage}%")
            else:
                book.discount_percentage = 0
                print(f"📊 No discount (price >= original_price)")
    
    if book_data.stock_quantity is not None:
        book.stock_quantity = book_data.stock_quantity
    if book_data.is_active is not None:
        book.is_active = book_data.is_active
    if book_data.is_featured is not None:
        book.is_featured = book_data.is_featured
    if book_data.is_bestseller is not None:
        book.is_bestseller = book_data.is_bestseller
    
    # Update additional fields
    if book_data.category_id is not None:
        book.category_id = book_data.category_id
    if book_data.publisher_id is not None:
        book.publisher_id = book_data.publisher_id
    if book_data.supplier_id is not None:
        book.supplier_id = book_data.supplier_id
    if book_data.language is not None:
        book.language = book_data.language
    if book_data.cover_type is not None:
        book.cover_type = book_data.cover_type
    if book_data.pages is not None:
        book.pages = book_data.pages
    if book_data.publication_year is not None:
        book.publication_year = book_data.publication_year
    if book_data.length is not None:
        book.length = book_data.length
    if book_data.width is not None:
        book.width = book_data.width
    if book_data.thickness is not None:
        book.thickness = book_data.thickness
    if book_data.weight is not None:
        book.weight = book_data.weight
    
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
async def delete_book(
    book_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
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


@app.patch("/api/admin/books/{book_id}/toggle-featured")
async def toggle_book_featured(
    book_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Toggle trạng thái nổi bật của sách"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    book.is_featured = not book.is_featured
    book.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(book)
        return {
            "message": f"Sách {'đã được đánh dấu' if book.is_featured else 'đã bỏ đánh dấu'} nổi bật",
            "is_featured": book.is_featured
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/admin/books/{book_id}/toggle-bestseller")
async def toggle_book_bestseller(
    book_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Toggle trạng thái bestseller của sách"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    book.is_bestseller = not book.is_bestseller
    book.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(book)
        return {
            "message": f"Sách {'đã được đánh dấu' if book.is_bestseller else 'đã bỏ đánh dấu'} bestseller",
            "is_bestseller": book.is_bestseller
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/books/{book_id}/reviews")
async def get_book_reviews(book_id: int, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    """Lấy danh sách đánh giá của sách"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    reviews = db.query(BookReview).filter(
        BookReview.book_id == book_id,
        BookReview.is_approved == True
    ).order_by(BookReview.created_at.desc()).offset(skip).limit(limit).all()
    
    # Return list directly for frontend compatibility
    return [
        {
            "id": review.id,
            "user_name": f"{review.user.first_name} {review.user.last_name}",
            "rating": review.rating,
            "title": review.title,
            "comment": review.comment,
            "created_at": review.created_at.isoformat() if review.created_at else None
        }
        for review in reviews
    ]

@app.get("/api/reviews/check")
async def check_single_order_review(order_id: int, user_id: int, db: Session = Depends(get_db)):
    """Check if user has reviewed all products in a specific order"""
    try:
        # Get all items in the order
        order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
        
        if not order_items:
            return {"has_reviewed": False}
        
        # Check if ALL products in the order have been reviewed
        for item in order_items:
            review = db.query(BookReview).filter(
                BookReview.book_id == item.book_id,
                BookReview.user_id == user_id,
                BookReview.order_id == order_id
            ).first()
            
            if not review:
                # If any product is not reviewed, return False
                return {"has_reviewed": False}
        
        # All products have been reviewed
        return {"has_reviewed": True}
    except Exception as e:
        print(f"Check review error: {str(e)}")
        return {"has_reviewed": False}

@app.post("/api/reviews/check-batch")
async def check_batch_order_reviews(request_data: dict, db: Session = Depends(get_db)):
    """Check review status for multiple orders at once (batch operation)"""
    try:
        order_ids = request_data.get('order_ids', [])
        user_id = request_data.get('user_id')
        
        if not order_ids or not user_id:
            return {}
        
        print(f"⭐ Checking reviews for {len(order_ids)} orders by user #{user_id}")
        
        results = {}
        
        for order_id in order_ids:
            # Get all items in this order
            order_items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
            
            if not order_items:
                results[str(order_id)] = False
                continue
            
            # Check if ALL products in the order have been reviewed
            all_reviewed = True
            for item in order_items:
                review = db.query(BookReview).filter(
                    BookReview.book_id == item.book_id,
                    BookReview.user_id == user_id,
                    BookReview.order_id == order_id
                ).first()
                
                if not review:
                    all_reviewed = False
                    break
            
            results[str(order_id)] = all_reviewed
        
        print(f" Batch check completed: {results}")
        return results
        
    except Exception as e:
        print(f" Batch check review error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}

@app.post("/api/reviews")
async def submit_review(review_data: dict, db: Session = Depends(get_db)):
    """Submit review for a book in an order"""
    try:
        book_id = review_data.get('book_id')
        order_id = review_data.get('order_id')
        rating = review_data.get('rating')
        comment = review_data.get('comment')
        
        if not book_id or not order_id or not rating:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Get user_id from order
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        user_id = order.user_id
        
        # Check if book exists
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Book not found")
        
        # Check if user already reviewed this book in this order
        existing_review = db.query(BookReview).filter(
            BookReview.book_id == book_id,
            BookReview.user_id == user_id,
            BookReview.order_id == order_id
        ).first()
        
        if existing_review:
            return {
                "success": False,
                "message": "Bạn đã đánh giá sản phẩm này trong đơn hàng này rồi"
            }
        
        # Create review
        new_review = BookReview(
            book_id=book_id,
            user_id=user_id,
            order_id=order_id,
            rating=rating,
            comment=comment,
            is_approved=True
        )
        
        db.add(new_review)
        db.flush()
        
        # Update book rating
        rating_stats = db.query(
            func.avg(BookReview.rating).label('avg_rating'),
            func.count(BookReview.id).label('count')
        ).filter(BookReview.book_id == book_id).first()
        
        if rating_stats and rating_stats.count > 0:
            book.rating_average = float(rating_stats.avg_rating)
            book.rating_count = rating_stats.count
            print(f"📊 Updated book #{book_id} rating: {book.rating_average:.2f} ({book.rating_count} reviews)")
        
        db.commit()
        
        return {
            "success": True,
            "message": "Đánh giá đã được thêm thành công"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error submitting review: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Lỗi khi gửi đánh giá: {str(e)}")

@app.post("/api/books/{book_id}/reviews")
async def create_book_review(
    book_id: int, 
    review_data: BookReviewCreate, 
    user_id: int, 
    order_id: int = None,  # Added order_id parameter
    db: Session = Depends(get_db)
):
    """Tạo đánh giá cho sách"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user already reviewed this book in this order
    query = db.query(BookReview).filter(
        BookReview.book_id == book_id,
        BookReview.user_id == user_id
    )
    
    if order_id:
        # If order_id provided, check for this specific order
        query = query.filter(BookReview.order_id == order_id)
    else:
        # If no order_id, check for reviews without order_id
        query = query.filter(BookReview.order_id == None)
    
    existing_review = query.first()
    
    if existing_review:
        raise HTTPException(status_code=400, detail="Bạn đã đánh giá sản phẩm này trong đơn hàng này rồi")
    
    new_review = BookReview(
        book_id=book_id,
        user_id=user_id,
        order_id=order_id,  # Added order_id
        rating=review_data.rating,
        title=review_data.title,
        comment=review_data.comment,
        is_approved=True
    )
    
    try:
        db.add(new_review)
        db.flush()  # Flush to get the new review ID without committing
        
        # Update book rating using SQL aggregate (much faster)
        rating_stats = db.query(
            func.avg(BookReview.rating).label('avg_rating'),
            func.count(BookReview.id).label('count')
        ).filter(BookReview.book_id == book_id).first()
        
        if rating_stats and rating_stats.count > 0:
            book.rating_average = float(rating_stats.avg_rating)
            book.rating_count = rating_stats.count
            print(f"📊 Updated book #{book_id} rating: {book.rating_average:.2f} ({book.rating_count} reviews)")
        
        db.commit()
        db.refresh(new_review)
        
        return {
            "id": new_review.id,
            "message": "Đánh giá đã được thêm thành công"
        }
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating review: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo đánh giá: {str(e)}")

# CATEGORY ENDPOINTS

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

# AUTHOR ENDPOINTS

@app.get("/api/authors")
async def get_authors(db: Session = Depends(get_db)):
    """Lấy danh sách tác giả"""
    authors = db.query(Author).filter(Author.is_active == True).all()
    
    return {
        "authors": [
            {
                "id": author.id,
                "pen_name": author.pen_name,
                "created_at": author.created_at.isoformat() if author.created_at else None
            }
            for author in authors
        ]
    }

@app.post("/api/authors")
async def create_author(pen_name: str, db: Session = Depends(get_db)):
    # Tạo tác giả mới
    existing = db.query(Author).filter(Author.pen_name == pen_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tác giả đã tồn tại")
    
    new_author = Author(pen_name=pen_name, is_active=True)
    
    try:
        db.add(new_author)
        db.commit()
        db.refresh(new_author)
        
        return {
            "id": new_author.id,
            "pen_name": new_author.pen_name,
            "message": "Tác giả đã được tạo thành công"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo tác giả: {str(e)}")

@app.put("/api/books/{book_id}/authors")
async def update_book_authors(
    book_id: int,
    author_ids: List[int],
    db: Session = Depends(get_db)
):
    """Cập nhật danh sách tác giả cho sách (Admin only)"""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    try:
        # Xóa tất cả liên kết tác giả cũ
        db.query(BookAuthor).filter(BookAuthor.book_id == book_id).delete()
        
        # Thêm liên kết tác giả mới
        for author_id in author_ids:
            # Kiểm tra tác giả tồn tại
            author = db.query(Author).filter(Author.id == author_id).first()
            if not author:
                raise HTTPException(status_code=404, detail=f"Author with id {author_id} not found")
            
            book_author = BookAuthor(
                book_id=book_id,
                author_id=author_id,
                role='author'
            )
            db.add(book_author)
        
        db.commit()
        
        return {
            "message": "Đã cập nhật danh sách tác giả thành công",
            "book_id": book_id,
            "author_count": len(author_ids)
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật tác giả: {str(e)}")

@app.get("/api/books/by-author/{author_id}")
async def get_books_by_author(
    author_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Lấy danh sách sách theo tác giả"""
    # Kiểm tra tác giả tồn tại
    author = db.query(Author).filter(Author.id == author_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")
    
    # Lấy danh sách book_id từ BookAuthor
    book_ids = db.query(BookAuthor.book_id).filter(
        BookAuthor.author_id == author_id
    ).all()
    book_ids = [bid[0] for bid in book_ids]
    
    # Lấy thông tin sách
    books = db.query(Book).filter(
        Book.id.in_(book_ids),
        Book.is_active == True
    ).offset(skip).limit(limit).all()
    
    return {
        "author": {
            "id": author.id,
            "pen_name": author.pen_name
        },
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
                "sold_quantity": book.sold_quantity,
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

# =====================================================
# PUBLISHER ENDPOINTS
# =====================================================

@app.get("/api/publishers")
async def get_publishers(db: Session = Depends(get_db)):
    """Lấy danh sách nhà xuất bản"""
    publishers = db.query(Publisher).filter(Publisher.is_active == True).all()
    
    return {
        "publishers": [
            {
                "id": pub.id,
                "name": pub.name,
                "contact_email": pub.contact_email,
                "contact_phone": pub.contact_phone,
                "created_at": pub.created_at.isoformat() if pub.created_at else None
            }
            for pub in publishers
        ]
    }

@app.post("/api/publishers")
async def create_publisher(
    name: str = Form(...),
    contact_email: str = Form(None),
    contact_phone: str = Form(None),
    db: Session = Depends(get_db)
):
    """Tạo nhà xuất bản mới"""
    # Check if publisher exists
    existing = db.query(Publisher).filter(Publisher.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nhà xuất bản đã tồn tại")
    
    new_publisher = Publisher(
        name=name,
        contact_email=contact_email,
        contact_phone=contact_phone,
        is_active=True
    )
    
    try:
        db.add(new_publisher)
        db.commit()
        db.refresh(new_publisher)
        
        return {
            "id": new_publisher.id,
            "name": new_publisher.name,
            "message": "Nhà xuất bản đã được tạo thành công"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo nhà xuất bản: {str(e)}")

# =====================================================
# SUPPLIER ENDPOINTS
# =====================================================

@app.get("/api/suppliers")
async def get_suppliers(db: Session = Depends(get_db)):
    """Lấy danh sách nhà cung cấp"""
    suppliers = db.query(Supplier).filter(Supplier.is_active == True).all()
    
    return {
        "suppliers": [
            {
                "id": sup.id,
                "name": sup.name,
                "contact_person": sup.contact_person,
                "email": sup.email,
                "phone": sup.phone,
                "address": sup.address,
                "created_at": sup.created_at.isoformat() if sup.created_at else None
            }
            for sup in suppliers
        ]
    }

@app.post("/api/suppliers")
async def create_supplier(
    name: str = Form(...),
    contact_person: str = Form(None),
    email: str = Form(None),
    phone: str = Form(None),
    address: str = Form(None),
    db: Session = Depends(get_db)
):
    """Tạo nhà cung cấp mới"""
    # Check if supplier exists
    existing = db.query(Supplier).filter(Supplier.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Nhà cung cấp đã tồn tại")
    
    new_supplier = Supplier(
        name=name,
        contact_person=contact_person,
        email=email,
        phone=phone,
        address=address,
        is_active=True
    )
    
    try:
        db.add(new_supplier)
        db.commit()
        db.refresh(new_supplier)
        
        return {
            "id": new_supplier.id,
            "name": new_supplier.name,
            "message": "Nhà cung cấp đã được tạo thành công"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo nhà cung cấp: {str(e)}")

# =====================================================
# CART ENDPOINTS
# =====================================================

@app.get("/api/cart/{user_id}")
async def get_cart(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy giỏ hàng của người dùng"""
    # Users can only view their own cart unless they're admin
    if current_user.id != user_id and current_user.role.role_name != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this cart")
    cart_items = db.query(CartItem).options(
        joinedload(CartItem.book).joinedload(Book.book_images)
    ).filter(CartItem.user_id == user_id).all()
    
    return {
        "cart_items": [
            {
                "id": item.id,
                "book_id": item.book_id,
                "book_title": item.book.title,
                "book_price": float(item.book.price),
                "book_original_price": float(item.book.original_price) if item.book.original_price else float(item.book.price),
                "discount_percentage": float(item.book.discount_percentage) if item.book.discount_percentage else 0,
                "book_image": item.book.book_images[0].image_url if item.book.book_images else None,
                "quantity": item.quantity,
                "total_price": float(item.book.price * item.quantity),
                "added_at": item.added_at.isoformat() if item.added_at else None
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Users can only add to their own cart
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this cart")
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
async def update_cart_item(
    cart_item_id: int,
    cart_data: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cập nhật số lượng sản phẩm trong giỏ hàng"""
    cart_item = db.query(CartItem).filter(CartItem.id == cart_item_id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    # Check if user owns this cart item
    if cart_item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this cart item")
    
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
async def remove_cart_item(
    cart_item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xóa sản phẩm khỏi giỏ hàng"""
    cart_item = db.query(CartItem).filter(CartItem.id == cart_item_id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    # Check if user owns this cart item
    if cart_item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to remove this cart item")
    
    try:
        db.delete(cart_item)
        db.commit()
        return {"message": "Item removed from cart successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error removing cart item: {str(e)}")

@app.delete("/api/cart/user/{user_id}")
async def clear_cart(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xóa toàn bộ giỏ hàng của người dùng"""
    # Users can only clear their own cart
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to clear this cart")
    cart_items = db.query(CartItem).filter(CartItem.user_id == user_id).all()
    
    try:
        for item in cart_items:
            db.delete(item)
        db.commit()
        return {"message": "Cart cleared successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error clearing cart: {str(e)}")

# VOUCHER ENDPOINTS

class CartItemInput(BaseModel):
    book_id: int
    quantity: int

class VoucherValidateRequest(BaseModel):
    user_id: int
    code: str
    items: Optional[List[CartItemInput]] = None
    subtotal: Optional[float] = None
    shipping_fee: Optional[float] = 0


def _compute_voucher_for_cart(voucher: Voucher, user_id: int, cart_items: List[CartItem], subtotal: float, shipping_fee: float, db: Session):
    now = datetime.utcnow()
    if not voucher.is_active:
        return False, "Voucher không hoạt động", 0.0, 0.0
    if now < voucher.start_date or now > voucher.end_date:
        return False, "Voucher không nằm trong thời gian áp dụng", 0.0, 0.0

    # Global usage limit
    if voucher.usage_limit is not None and voucher.used_count is not None and voucher.used_count >= voucher.usage_limit:
        return False, "Voucher đã hết lượt sử dụng", 0.0, 0.0

    # Per-user usage limit
    if voucher.user_limit is not None and voucher.user_limit > 0:
        user_used = db.query(func.count(VoucherUsage.id)).filter(
            VoucherUsage.voucher_id == voucher.id,
            VoucherUsage.user_id == user_id
        ).scalar() or 0
        if user_used >= voucher.user_limit:
            return False, "Bạn đã dùng hết số lần cho voucher này", 0.0, 0.0

    # Min order amount
    if voucher.min_order_amount and float(subtotal) < float(voucher.min_order_amount):
        return False, "Chưa đạt giá trị đơn tối thiểu", 0.0, 0.0

    # Determine eligible amount (respect include/exclude rules)
    include_cat = set(voucher.applicable_categories or [])
    include_books = set(voucher.applicable_books or [])
    exclude_cat = set(voucher.excluded_categories or [])
    exclude_books = set(voucher.excluded_books or [])

    eligible_amount = 0.0
    for ci in cart_items:
        book = ci.book
        # Exclusions first
        if book.id in exclude_books or (book.category_id in exclude_cat if book.category_id else False):
            continue
        # Inclusions (if any defined)
        if include_books or include_cat:
            allowed = (book.id in include_books) or (book.category_id in include_cat if book.category_id else False)
            if not allowed:
                continue
        eligible_amount += float(book.price) * ci.quantity

    # If inclusion filters set but nothing eligible, treat as not applicable
    if (include_books or include_cat) and eligible_amount <= 0:
        return False, "Không có sản phẩm phù hợp điều kiện voucher", 0.0, 0.0

    discount_amount = 0.0
    shipping_discount = 0.0

    if voucher.discount_type == 'percentage':
        discount_amount = eligible_amount * float(voucher.discount_value) / 100.0
        if voucher.max_discount_amount:
            discount_amount = min(discount_amount, float(voucher.max_discount_amount))
    elif voucher.discount_type == 'fixed_amount':
        discount_amount = min(float(voucher.discount_value), eligible_amount)
        if voucher.max_discount_amount:
            discount_amount = min(discount_amount, float(voucher.max_discount_amount))
    elif voucher.discount_type == 'free_shipping':
        # Discount on shipping fee up to max_discount_amount (if any)
        shipping_discount = float(shipping_fee or 0)
        if voucher.max_discount_amount:
            shipping_discount = min(shipping_discount, float(voucher.max_discount_amount))
    else:
        return False, "Loại voucher không hợp lệ", 0.0, 0.0

    return True, "OK", round(discount_amount, 2), round(shipping_discount, 2)


@app.get("/api/vouchers")
async def list_vouchers(user_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Danh sách voucher đang hoạt động (trong thời gian hiệu lực)"""
    print(f" PUBLIC /api/vouchers endpoint called (no auth required)")
    now = datetime.utcnow()
    vouchers = db.query(Voucher).filter(
        Voucher.is_active == True,
        Voucher.start_date <= now,
        Voucher.end_date >= now
    ).order_by(Voucher.created_at.desc()).all()

    result = []
    for v in vouchers:
        remaining_uses = None
        if v.usage_limit is not None and v.used_count is not None:
            remaining_uses = max(int(v.usage_limit - v.used_count), 0)
        # Map to simple structure compatible with mobile app
        result.append({
            "id": v.id,
            "code": v.code,
            "name": v.name,
            "description": v.description,
            "discount": int(float(v.discount_value)) if v.discount_type == 'percentage' else 0,
            "discount_type": v.discount_type,
            "discount_value": float(v.discount_value),
            "minPrice": int(float(v.min_order_amount or 0)),
            "maxDiscount": int(float(v.max_discount_amount or 0)) if v.max_discount_amount else 0,
            "startDate": v.start_date.isoformat() if v.start_date else None,
            "endDate": v.end_date.isoformat() if v.end_date else None,
            "expiryDate": v.end_date.isoformat() if v.end_date else None,
            "maxUses": int(v.usage_limit) if v.usage_limit is not None else None,
            "remainingUses": remaining_uses if remaining_uses is not None else None,
            "isActive": v.is_active,
        })
    return {"vouchers": result, "total": len(result)}


@app.post("/api/vouchers/validate")
async def validate_voucher(req: VoucherValidateRequest, db: Session = Depends(get_db)):
    """Kiểm tra và tính toán mức giảm cho mã voucher với giỏ hàng hiện tại"""
    code = req.code.strip().upper()
    voucher = db.query(Voucher).filter(Voucher.code == code).first()
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher không tồn tại")

    # Get cart items: from request or from DB
    cart_items: List[CartItem] = []
    if req.items and len(req.items) > 0:
        # Build transient CartItem-like objects by querying books
        # For accurate pricing, fetch from DB using book ids
        items_map = {item.book_id: item.quantity for item in req.items}
        books = db.query(Book).filter(Book.id.in_(list(items_map.keys()))).all()
        for b in books:
            ci = CartItem(user_id=req.user_id, book_id=b.id, quantity=items_map.get(b.id, 1))
            ci.book = b
            cart_items.append(ci)
        subtotal = sum(float(ci.book.price) * ci.quantity for ci in cart_items)
    else:
        cart_items = db.query(CartItem).options(joinedload(CartItem.book)).filter(CartItem.user_id == req.user_id).all()
        subtotal = sum(float(ci.book.price) * ci.quantity for ci in cart_items)

    shipping_fee = float(req.shipping_fee or 0)

    ok, reason, discount_amount, shipping_discount = _compute_voucher_for_cart(
        voucher, req.user_id, cart_items, subtotal, shipping_fee, db
    )

    total = subtotal + shipping_fee - discount_amount - shipping_discount
    total = round(total, 2)

    return {
        "valid": ok,
        "reason": None if ok else reason,
        "voucher": {
            "id": voucher.id,
            "code": voucher.code,
            "name": voucher.name,
            "discount_type": voucher.discount_type,
            "discount_value": float(voucher.discount_value),
            "min_order_amount": float(voucher.min_order_amount or 0),
            "max_discount_amount": float(voucher.max_discount_amount or 0) if voucher.max_discount_amount else 0,
            "end_date": voucher.end_date.isoformat() if voucher.end_date else None,
        },
        "subtotal": round(subtotal, 2),
        "shipping_fee": round(shipping_fee, 2),
        "discount_amount": discount_amount,
        "shipping_discount": shipping_discount,
        "total": total
    }


# =====================================================
# ADMIN VOUCHER MANAGEMENT ENDPOINTS
# =====================================================

class VoucherCreateRequest(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    discount_type: str  # 'percentage', 'fixed_amount', 'free_shipping'
    discount_value: float
    min_order_amount: Optional[float] = 0
    max_discount_amount: Optional[float] = None
    usage_limit: Optional[int] = None
    user_limit: int = 1
    start_date: str  # ISO format
    end_date: str    # ISO format
    is_active: bool = True
    applicable_categories: Optional[List[int]] = None
    applicable_books: Optional[List[int]] = None
    excluded_categories: Optional[List[int]] = None
    excluded_books: Optional[List[int]] = None

class VoucherUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    min_order_amount: Optional[float] = None
    max_discount_amount: Optional[float] = None
    usage_limit: Optional[int] = None
    user_limit: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_active: Optional[bool] = None
    applicable_categories: Optional[List[int]] = None
    applicable_books: Optional[List[int]] = None
    excluded_categories: Optional[List[int]] = None
    excluded_books: Optional[List[int]] = None

@app.post("/api/admin/vouchers")
async def create_voucher(
    voucher_data: VoucherCreateRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Tạo voucher mới (Admin only)"""
    print(f"➕ Create voucher endpoint called by user: {current_admin.username} (ID: {current_admin.id})")
    try:
        # Check if code exists
        existing = db.query(Voucher).filter(Voucher.code == voucher_data.code.upper()).first()
        if existing:
            raise HTTPException(status_code=400, detail="Mã voucher đã tồn tại")
        
        # Parse dates
        start_date = datetime.fromisoformat(voucher_data.start_date.replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(voucher_data.end_date.replace('Z', '+00:00'))
        
        new_voucher = Voucher(
            code=voucher_data.code.upper(),
            name=voucher_data.name,
            description=voucher_data.description,
            discount_type=voucher_data.discount_type,
            discount_value=voucher_data.discount_value,
            min_order_amount=voucher_data.min_order_amount,
            max_discount_amount=voucher_data.max_discount_amount,
            usage_limit=voucher_data.usage_limit,
            used_count=0,
            user_limit=voucher_data.user_limit,
            start_date=start_date,
            end_date=end_date,
            is_active=voucher_data.is_active,
            applicable_categories=voucher_data.applicable_categories,
            applicable_books=voucher_data.applicable_books,
            excluded_categories=voucher_data.excluded_categories,
            excluded_books=voucher_data.excluded_books,
        )
        
        db.add(new_voucher)
        db.commit()
        db.refresh(new_voucher)
        
        return {
            "id": new_voucher.id,
            "code": new_voucher.code,
            "message": "Voucher đã được tạo thành công"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Ngày tháng không hợp lệ: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi tạo voucher: {str(e)}")

@app.put("/api/admin/vouchers/{voucher_id}")
async def update_voucher(
    voucher_id: int,
    voucher_data: VoucherUpdateRequest,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Cập nhật voucher (Admin only)"""
    voucher = db.query(Voucher).filter(Voucher.id == voucher_id).first()
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher không tồn tại")
    
    try:
        # Update fields
        if voucher_data.name is not None:
            voucher.name = voucher_data.name
        if voucher_data.description is not None:
            voucher.description = voucher_data.description
        if voucher_data.discount_type is not None:
            voucher.discount_type = voucher_data.discount_type
        if voucher_data.discount_value is not None:
            voucher.discount_value = voucher_data.discount_value
        if voucher_data.min_order_amount is not None:
            voucher.min_order_amount = voucher_data.min_order_amount
        if voucher_data.max_discount_amount is not None:
            voucher.max_discount_amount = voucher_data.max_discount_amount
        if voucher_data.usage_limit is not None:
            voucher.usage_limit = voucher_data.usage_limit
        if voucher_data.user_limit is not None:
            voucher.user_limit = voucher_data.user_limit
        if voucher_data.start_date is not None:
            voucher.start_date = datetime.fromisoformat(voucher_data.start_date.replace('Z', '+00:00'))
        if voucher_data.end_date is not None:
            voucher.end_date = datetime.fromisoformat(voucher_data.end_date.replace('Z', '+00:00'))
        if voucher_data.is_active is not None:
            voucher.is_active = voucher_data.is_active
        if voucher_data.applicable_categories is not None:
            voucher.applicable_categories = voucher_data.applicable_categories
        if voucher_data.applicable_books is not None:
            voucher.applicable_books = voucher_data.applicable_books
        if voucher_data.excluded_categories is not None:
            voucher.excluded_categories = voucher_data.excluded_categories
        if voucher_data.excluded_books is not None:
            voucher.excluded_books = voucher_data.excluded_books
        
        db.commit()
        db.refresh(voucher)
        
        return {
            "id": voucher.id,
            "code": voucher.code,
            "message": "Voucher đã được cập nhật"
        }
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Ngày tháng không hợp lệ: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi cập nhật voucher: {str(e)}")

@app.delete("/api/admin/vouchers/{voucher_id}")
async def delete_voucher(
    voucher_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Xóa voucher (Admin only)"""
    voucher = db.query(Voucher).filter(Voucher.id == voucher_id).first()
    if not voucher:
        raise HTTPException(status_code=404, detail="Voucher không tồn tại")
    
    # Check if voucher has been used
    usage_count = db.query(VoucherUsage).filter(VoucherUsage.voucher_id == voucher_id).count()
    if usage_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể xóa voucher đã được sử dụng {usage_count} lần. Hãy vô hiệu hóa thay vì xóa."
        )
    
    try:
        db.delete(voucher)
        db.commit()
        return {"message": "Voucher đã được xóa thành công"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi khi xóa voucher: {str(e)}")

# Add a special handler for debugging authentication issues
from fastapi import Request

@app.get("/api/admin/vouchers")
async def list_all_vouchers(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    # Lấy toàn bộ voucher (Admin only)
    print(f"Admin vouchers endpoint called by user: {current_admin.username} (ID: {current_admin.id})")
    
    auth_header = request.headers.get("Authorization", "No header")
    print(f"Authorization header present: {'Yes' if auth_header != 'No header' else 'No'}")
    
    vouchers = db.query(Voucher).order_by(Voucher.created_at.desc()).offset(skip).limit(limit).all()
    
    result = []
    for v in vouchers:
        remaining_uses = None
        if v.usage_limit is not None and v.used_count is not None:
            remaining_uses = max(int(v.usage_limit - v.used_count), 0)
        
        result.append({
            "id": v.id,
            "code": v.code,
            "name": v.name,
            "description": v.description,
            "discount_type": v.discount_type,
            "discount_value": float(v.discount_value),
            "min_order_amount": float(v.min_order_amount or 0),
            "max_discount_amount": float(v.max_discount_amount or 0) if v.max_discount_amount else None,
            "usage_limit": int(v.usage_limit) if v.usage_limit is not None else None,
            "used_count": int(v.used_count or 0),
            "remaining_uses": remaining_uses,
            "user_limit": int(v.user_limit),
            "start_date": v.start_date.isoformat() if v.start_date else None,
            "end_date": v.end_date.isoformat() if v.end_date else None,
            "is_active": v.is_active,
            "applicable_categories": v.applicable_categories or [],
            "applicable_books": v.applicable_books or [],
            "excluded_categories": v.excluded_categories or [],
            "excluded_books": v.excluded_books or [],
            "created_at": v.created_at.isoformat() if v.created_at else None,
        })
    
    return {"vouchers": result, "total": len(result)}

@app.get("/api/wishlist/{user_id}")
async def get_wishlist(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy danh sách yêu thích của người dùng"""
    # Users can only view their own wishlist unless they're admin
    if current_user.id != user_id and current_user.role.role_name != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this wishlist")
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
async def add_to_wishlist(
    wishlist_data: WishlistItemCreate,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Thêm sách vào danh sách yêu thích"""
    # Users can only add to their own wishlist
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this wishlist")
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
async def remove_from_wishlist(
    wishlist_item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Xóa sách khỏi danh sách yêu thích"""
    wishlist_item = db.query(WishlistItem).filter(WishlistItem.id == wishlist_item_id).first()
    if not wishlist_item:
        raise HTTPException(status_code=404, detail="Wishlist item not found")
    
    # Check if user owns this wishlist item
    if wishlist_item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to remove this item")
    
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
async def get_user_orders(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy đơn hàng của người dùng"""
    # Users can only view their own orders unless they're admin
    if current_user.id != user_id and current_user.role.role_name != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view these orders")
    try:
        orders = db.query(Order).options(
            joinedload(Order.order_items)
        ).filter(Order.user_id == user_id).order_by(Order.created_at.desc()).all()
        
        return {
            "orders": [
                {
                    "id": order.id,
                    "order_number": order.order_number,
                    "status": order.status,
                    "total_amount": float(order.total_amount),
                    "payment_status": order.payment_status,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                    "items_count": len(order.order_items) if order.order_items else 0
                }
                for order in orders
            ]
        }
    except Exception as e:
        print(f"❌ Get user orders error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Get orders error: {str(e)}")

@app.post("/api/orders")
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Tạo đơn hàng mới"""
    # Users can only create orders for themselves
    if current_user.id != order_data.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to create order for another user")
    # Get user's cart items
    cart_items = db.query(CartItem).options(joinedload(CartItem.book)).filter(CartItem.user_id == order_data.user_id).all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Calculate totals
    subtotal = sum(float(item.book.price) * item.quantity for item in cart_items)
    shipping_fee = 0.0  # TODO: Calculate based on address
    discount_amount = 0.0
    shipping_discount = 0.0

    # Apply voucher if provided
    applied_voucher = None
    if order_data.voucher_id is not None:
        applied_voucher = db.query(Voucher).filter(Voucher.id == order_data.voucher_id).first()
        if not applied_voucher:
            raise HTTPException(status_code=400, detail="Voucher không tồn tại")
        ok, reason, disc, ship_disc = _compute_voucher_for_cart(applied_voucher, order_data.user_id, cart_items, subtotal, shipping_fee, db)
        if not ok:
            raise HTTPException(status_code=400, detail=f"Không áp dụng được voucher: {reason}")
        discount_amount = disc
        shipping_discount = ship_disc
    
    total_amount = subtotal + shipping_fee - discount_amount - shipping_discount
    
    # Generate order number
    order_number = generate_order_number()
    
    # Create order
    new_order = Order(
        order_number=order_number,
        user_id=order_data.user_id,
        status="pending",
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        discount_amount=discount_amount + shipping_discount,
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
            cart_item.book.sold_quantity = (cart_item.book.sold_quantity or 0) + cart_item.quantity
        
        # Clear cart
        for cart_item in cart_items:
            db.delete(cart_item)

        # Record voucher usage
        if applied_voucher is not None:
            vu = VoucherUsage(
                voucher_id=applied_voucher.id,
                user_id=order_data.user_id,
                order_id=new_order.id,
                discount_amount=discount_amount + shipping_discount,
            )
            db.add(vu)
            # Increase used count
            applied_voucher.used_count = (applied_voucher.used_count or 0) + 1
        
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

@app.post("/api/orders/simple")
async def create_simple_order(
    user_id: int,
    payment_method: str = "COD",
    notes: str = None,
    voucher_code: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Tạo đơn hàng đơn giản từ giỏ hàng (không cần address_id, payment_method_id)"""
    # Users can only create orders for themselves
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to create order for another user")
    try:
        # Get user's cart items
        cart_items = db.query(CartItem).options(joinedload(CartItem.book)).filter(CartItem.user_id == user_id).all()
        if not cart_items:
            raise HTTPException(status_code=400, detail="Cart is empty")
        
        # Calculate totals
        subtotal = sum(float(item.book.price) * item.quantity for item in cart_items)
        shipping_fee = 0.0
        discount_amount = 0.0
        shipping_discount = 0.0

        applied_voucher = None
        if voucher_code:
            code = voucher_code.strip().upper()
            applied_voucher = db.query(Voucher).filter(Voucher.code == code).first()
            if not applied_voucher:
                raise HTTPException(status_code=400, detail="Voucher không tồn tại")
            ok, reason, disc, ship_disc = _compute_voucher_for_cart(applied_voucher, user_id, cart_items, subtotal, shipping_fee, db)
            if not ok:
                raise HTTPException(status_code=400, detail=f"Không áp dụng được voucher: {reason}")
            discount_amount = disc
            shipping_discount = ship_disc
        
        total_amount = subtotal + shipping_fee - discount_amount - shipping_discount
        
        # Generate order number
        order_number = generate_order_number()
        
        # Create order without requiring address_id and payment_method_id
        new_order = Order(
            order_number=order_number,
            user_id=user_id,
            status="pending",
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            discount_amount=discount_amount + shipping_discount,
            total_amount=total_amount,
            payment_method_id=None,  # Optional
            payment_status="pending",
            voucher_id=applied_voucher.id if applied_voucher else None,
            shipping_address_id=None,  # Optional
            notes=notes or f"Payment: {payment_method}"
        )
        
        db.add(new_order)
        db.flush()
        
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
            if cart_item.book.stock_quantity >= cart_item.quantity:
                cart_item.book.stock_quantity -= cart_item.quantity
                cart_item.book.sold_quantity = (cart_item.book.sold_quantity or 0) + cart_item.quantity
        
        # Clear cart
        for cart_item in cart_items:
            db.delete(cart_item)

        # Record voucher usage
        if applied_voucher is not None:
            vu = VoucherUsage(
                voucher_id=applied_voucher.id,
                user_id=user_id,
                order_id=new_order.id,
                discount_amount=discount_amount + shipping_discount,
            )
            db.add(vu)
            applied_voucher.used_count = (applied_voucher.used_count or 0) + 1
        
        db.commit()
        db.refresh(new_order)
        
        return {
            "id": new_order.id,
            "order_number": new_order.order_number,
            "total_amount": float(new_order.total_amount),
            "status": new_order.status,
            "payment_status": new_order.payment_status,
            "created_at": new_order.created_at.isoformat() if new_order.created_at else None,
            "message": "Order created successfully"
        }
    except Exception as e:
        db.rollback()
        print(f"❌ Create simple order error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error creating order: {str(e)}")

@app.get("/api/orders/{order_id}/details")
async def get_order_details(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lấy chi tiết đơn hàng"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if user owns this order or is admin
    if order.user_id != current_user.id and current_user.role.role_name != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this order")
    
    # Get order items with book information
    order_items = db.query(OrderItem).options(
        joinedload(OrderItem.book).joinedload(Book.book_images)
    ).filter(OrderItem.order_id == order_id).all()
    
    return {
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
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "items": [
            {
                "id": item.id,
                "book_id": item.book_id,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "discount_amount": float(item.discount_amount),
                "total_price": float(item.total_price),
                "book": {
                    "id": item.book.id,
                    "title": item.book.title,
                    "images": [
                        {
                            "id": img.id,
                            "image_url": img.image_url,
                            "is_primary": img.is_primary,
                            "sort_order": img.sort_order
                        }
                        for img in sorted(item.book.book_images, key=lambda x: (not x.is_primary, x.sort_order))
                    ] if item.book.book_images else []
                } if item.book else None
            }
            for item in order_items
        ]
    }

@app.put("/api/orders/{order_id}")
async def update_order(
    order_id: int,
    order_data: OrderUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Cập nhật trạng thái đơn hàng (Admin only)"""
    try:
        print(f"🔄 Backend: Updating order #{order_id}")
        print(f"📝 Request data: {order_data.dict()}")
        
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            print(f"❌ Order #{order_id} not found")
            raise HTTPException(status_code=404, detail="Order not found")
        
        print(f"📊 Current order status: {order.status}")
        
        # Update fields
        if order_data.status is not None:
            old_status = order.status
            order.status = order_data.status
            print(f"🔄 Updating status: {old_status} → {order_data.status}")
            
            # Set timestamps based on status
            if order_data.status == "shipped":
                order.shipped_at = datetime.utcnow()
            elif order_data.status == "delivered":
                order.delivered_at = datetime.utcnow()
                # Automatically mark as paid when delivered
                if order.payment_status != "paid":
                    old_payment_status = order.payment_status
                    order.payment_status = "paid"
                    print(f"💳 Auto-updating payment status: {old_payment_status} → paid (order delivered)")
            elif order_data.status == "cancelled":
                order.cancelled_at = datetime.utcnow()
        
        if order_data.payment_status is not None:
            order.payment_status = order_data.payment_status
        
        if order_data.tracking_number is not None:
            order.tracking_number = order_data.tracking_number
        
        if order_data.notes is not None:
            order.notes = order_data.notes
        
        order.updated_at = datetime.utcnow()
        
        db.commit()
        print(f" Order #{order_id} updated successfully to: {order.status}")
        return {"message": "Order updated successfully", "order_id": order_id, "new_status": order.status}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f" Error updating order #{order_id}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error updating order: {str(e)}")

@app.post("/api/orders/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    reason: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Hủy đơn hàng"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if user owns this order or is admin
    if order.user_id != current_user.id and current_user.role.role_name != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to cancel this order")
    
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
async def get_all_orders(
    skip: int = 0,
    limit: int = 50,
    status: str = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Lấy tất cả đơn hàng (Admin only)"""
    try:
        query = db.query(Order).options(
            joinedload(Order.user),
            joinedload(Order.order_items)
        )
        
        if status:
            query = query.filter(Order.status == status)
        
        orders = query.offset(skip).limit(limit).all()
        
        return {
            "orders": [
                {
                    "id": order.id,
                    "order_number": order.order_number,
                    "user_name": f"{order.user.first_name or ''} {order.user.last_name or ''}".strip() if order.user else "Unknown",
                    "user_email": order.user.email if order.user else "unknown@email.com",
                    "status": order.status,
                    "total_amount": float(order.total_amount),
                    "payment_status": order.payment_status,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                    "items_count": len(order.order_items) if order.order_items else 0
                }
                for order in orders
            ],
            "total": len(orders)
        }
    except Exception as e:
        print(f"❌ Get orders error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Get orders error: {str(e)}")

@app.get("/api/admin/users")
async def get_all_users(
    skip: int = 0,
    limit: int = 50,
    role: str = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
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
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in users
        ],
        "total": len(users)
    }

@app.put("/api/admin/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
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
async def get_all_books_admin(
    skip: int = 0,
    limit: int = 50,
    is_active: bool = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
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
                "created_at": book.created_at.isoformat() if book.created_at else None
            }
            for book in books
        ],
        "total": len(books)
    }

@app.get("/api/admin/dashboard")
async def get_admin_dashboard(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Lấy thống kê dashboard admin"""
    try:
        # Basic stats
        total_users = db.query(User).count()
        total_books = db.query(Book).count()
        total_orders = db.query(Order).count()
        total_revenue = db.query(Order).filter(Order.payment_status == "paid").with_entities(
            func.sum(Order.total_amount)
        ).scalar() or 0
        
        # Recent orders with eager loading
        recent_orders = db.query(Order).options(
            joinedload(Order.user)
        ).order_by(Order.created_at.desc()).limit(5).all()
        
        # Top selling books
        top_books = db.query(Book).order_by(Book.sold_quantity.desc()).limit(5).all()
        
        # Order status distribution
        order_statuses = db.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
        
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
                    "user_name": f"{order.user.first_name or ''} {order.user.last_name or ''}".strip() if order.user else "Unknown",
                    "user_email": order.user.email if order.user else "unknown@email.com",
                    "total_amount": float(order.total_amount),
                    "status": order.status,
                    "payment_status": order.payment_status,
                    "created_at": order.created_at.isoformat() if order.created_at else None
                }
                for order in recent_orders
            ],
            "top_books": [
                {
                    "id": book.id,
                    "title": book.title,
                    "sold_quantity": book.sold_quantity or 0,
                    "price": float(book.price)
                }
                for book in top_books
            ],
            "order_statuses": [
                {"status": status or "unknown", "count": count}
                for status, count in order_statuses
            ]
        }
    except Exception as e:
        print(f" Dashboard error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")

# STATISTICS ENDPOINTS (ADMIN)

@app.get("/api/admin/statistics/revenue")
async def get_revenue_statistics(
    period: str = "day",  # day, month, year
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Thống kê doanh thu theo ngày/tháng/năm"""
    try:
        # Parse dates
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start = datetime.now() - timedelta(days=30)
        
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end = datetime.now()
        
        # Query paid orders only
        query = db.query(Order).filter(
            Order.payment_status == "paid",
            Order.created_at >= start,
            Order.created_at <= end
        )
        
        orders = query.all()
        
        # Calculate statistics
        total_orders = len(orders)
        total_books_sold = sum(
            sum(item.quantity for item in order.order_items)
            for order in orders
        )
        
        # Calculate revenue components
        total_revenue = sum(float(order.total_amount) for order in orders)  # Actual revenue after discount
        total_discount = sum(float(order.discount_amount or 0) for order in orders)  # Total voucher discounts
        total_revenue_before_discount = total_revenue + total_discount  # Revenue before voucher
        
        # Profit = revenue - cost (assuming original_price is cost)
        total_profit = 0
        for order in orders:
            for item in order.order_items:
                book = item.book
                if book:
                    # Profit per item = (selling price - original price) * quantity
                    original_price = float(book.original_price) if book.original_price else float(book.price)
                    selling_price = float(item.unit_price)
                    profit_per_item = (selling_price - original_price) * item.quantity
                    total_profit += profit_per_item
        
        # Adjust profit by subtracting voucher discounts (we gave away this money)
        total_profit_after_discount = total_profit - total_discount
        
        return {
            "period": period,
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "total_orders": total_orders,
            "total_books_sold": total_books_sold,
            "total_revenue": round(total_revenue, 2),  # Revenue after discount (actual money received)
            "total_revenue_before_discount": round(total_revenue_before_discount, 2),  # Revenue before voucher
            "total_discount": round(total_discount, 2),  # Total voucher discounts given
            "total_profit": round(total_profit, 2),  # Profit before discount
            "total_profit_after_discount": round(total_profit_after_discount, 2)  # Actual profit after voucher
        }
    except Exception as e:
        print(f" Revenue statistics error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting revenue statistics: {str(e)}")

@app.get("/api/admin/statistics/books")
async def get_book_statistics(
    period: str = "day",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Thống kê doanh thu theo sách"""
    try:
        # Parse dates
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start = datetime.now() - timedelta(days=30)
        
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end = datetime.now()
        
        # Get all order items in the period
        order_items = db.query(OrderItem).join(Order).filter(
            Order.payment_status == "paid",
            Order.created_at >= start,
            Order.created_at <= end
        ).all()
        
        # Group by book
        book_stats = {}
        for item in order_items:
            book = item.book
            if not book:
                continue
            
            book_id = book.id
            if book_id not in book_stats:
                original_price = float(book.original_price) if book.original_price else float(book.price)
                book_stats[book_id] = {
                    "book_id": book_id,
                    "book_name": book.title,
                    "category": book.category.name if book.category else "Unknown",
                    "sold_quantity": 0,
                    "revenue": 0.0,
                    "profit": 0.0,
                    "stock_remaining": book.stock_quantity
                }
            
            # Update statistics
            book_stats[book_id]["sold_quantity"] += item.quantity
            book_stats[book_id]["revenue"] += float(item.unit_price) * item.quantity
            
            # Calculate profit
            original_price = float(book.original_price) if book.original_price else float(book.price)
            selling_price = float(item.unit_price)
            profit = (selling_price - original_price) * item.quantity
            book_stats[book_id]["profit"] += profit
        
        # Convert to list and sort by sold quantity
        result = list(book_stats.values())
        result.sort(key=lambda x: x["sold_quantity"], reverse=True)
        
        # Round numbers
        for item in result:
            item["revenue"] = round(item["revenue"], 2)
            item["profit"] = round(item["profit"], 2)
        
        return {
            "period": period,
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "books": result
        }
    except Exception as e:
        print(f" Book statistics error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting book statistics: {str(e)}")

@app.get("/api/admin/statistics/categories")
async def get_category_statistics(
    period: str = "day",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Thống kê doanh thu theo thể loại"""
    try:
        # Parse dates
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start = datetime.now() - timedelta(days=30)
        
        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end = datetime.now()
        
        # Get all order items in the period
        order_items = db.query(OrderItem).join(Order).filter(
            Order.payment_status == "paid",
            Order.created_at >= start,
            Order.created_at <= end
        ).all()
        
        # Group by category and book
        category_stats = {}
        for item in order_items:
            book = item.book
            if not book or not book.category:
                continue
            
            category_id = book.category.id
            category_name = book.category.name
            
            if category_id not in category_stats:
                category_stats[category_id] = {
                    "category_id": category_id,
                    "category_name": category_name,
                    "books": {},
                    "total_sold": 0,
                    "total_profit": 0.0,
                    "total_stock": 0
                }
            
            book_id = book.id
            if book_id not in category_stats[category_id]["books"]:
                category_stats[category_id]["books"][book_id] = {
                    "book_id": book_id,
                    "book_name": book.title,
                    "sold_quantity": 0,
                    "profit": 0.0,
                    "stock_remaining": book.stock_quantity
                }
            
            # Update book stats
            category_stats[category_id]["books"][book_id]["sold_quantity"] += item.quantity
            
            # Calculate profit
            original_price = float(book.original_price) if book.original_price else float(book.price)
            selling_price = float(item.unit_price)
            profit = (selling_price - original_price) * item.quantity
            category_stats[category_id]["books"][book_id]["profit"] += profit
            
            # Update category totals
            category_stats[category_id]["total_sold"] += item.quantity
            category_stats[category_id]["total_profit"] += profit
        
        # Calculate total stock for each category
        for cat_id in category_stats:
            total_stock = sum(
                book_data["stock_remaining"]
                for book_data in category_stats[cat_id]["books"].values()
            )
            category_stats[cat_id]["total_stock"] = total_stock
            
            # Convert books dict to list
            category_stats[cat_id]["books"] = list(category_stats[cat_id]["books"].values())
            
            # Round numbers
            category_stats[cat_id]["total_profit"] = round(category_stats[cat_id]["total_profit"], 2)
            for book in category_stats[cat_id]["books"]:
                book["profit"] = round(book["profit"], 2)
        
        # Convert to list and sort by total sold
        result = list(category_stats.values())
        result.sort(key=lambda x: x["total_sold"], reverse=True)
        
        return {
            "period": period,
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "categories": result
        }
    except Exception as e:
        print(f"❌ Category statistics error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error getting category statistics: {str(e)}")

# SEARCH ENDPOINTS

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
    #  Tìm kiếm sách
    query = db.query(Book).filter(Book.is_active == True)

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
                "stock_quantity": book.stock_quantity,
                "sold_quantity": book.sold_quantity,
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)


