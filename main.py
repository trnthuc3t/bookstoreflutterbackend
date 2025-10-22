# =====================================================
# FASTAPI MAIN APPLICATION CHO BOOKSTORE BACKEND
# =====================================================

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên chỉ định domain cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

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
        db.execute("SELECT 1")
        
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
                "price": float(book.price),
                "original_price": float(book.original_price) if book.original_price else None,
                "discount_percentage": float(book.discount_percentage),
                "stock_quantity": book.stock_quantity,
                "rating_average": float(book.rating_average),
                "rating_count": book.rating_count,
                "category": book.category.name if book.category else None,
                "publisher": book.publisher.name if book.publisher else None,
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
            "name": f"{ba.author.first_name} {ba.author.last_name}",
            "role": ba.role
        }
        for ba in book.book_authors
    ]
    
    # Lấy images
    images = [
        {
            "id": img.id,
            "url": img.image_url,
            "type": img.image_type,
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
        "summary": book.summary,
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
# STARTUP EVENT
# =====================================================

@app.on_event("startup")
async def startup_event():
    """Khởi tạo khi app start"""
    print("🚀 BookStore API đang khởi động...")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔍 ReDoc: http://localhost:8000/redoc")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
