# BookStore Backend API

API backend cho ứng dụng bán sách online sử dụng FastAPI và PostgreSQL.

## 🚀 Quick Start

1. Clone repository
2. Cài đặt dependencies: `pip install -r requirements.txt`
3. Tạo database PostgreSQL: `CREATE DATABASE bookstore_online;`
4. Setup database: `python setup_database.py`
5. Chạy server: `uvicorn main:app --reload`

## 📚 API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔧 Environment Setup

Copy `env_example.txt` thành `.env` và cấu hình thông tin database.