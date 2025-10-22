# =====================================================
# HƯỚNG DẪN SETUP DATABASE POSTGRESQL
# =====================================================

## 1. CÀI ĐẶT POSTGRESQL

### Windows:
1. Tải PostgreSQL từ: https://www.postgresql.org/download/windows/
2. Cài đặt với password cho user `postgres`
3. Khởi động PostgreSQL service

### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### macOS:
```bash
brew install postgresql
brew services start postgresql
```

## 2. TẠO DATABASE

```sql
-- Kết nối PostgreSQL
psql -U postgres

-- Tạo database
CREATE DATABASE bookstore_online;

-- Tạo user (tùy chọn)
CREATE USER bookstore_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE bookstore_online TO bookstore_user;

-- Kết nối vào database
\c bookstore_online;
```

## 3. CÀI ĐẶT PYTHON ENVIRONMENT

```bash
# Tạo virtual environment
python -m venv venv

# Kích hoạt virtual environment
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt
```

## 4. CẤU HÌNH ENVIRONMENT VARIABLES

Tạo file `.env`:
```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bookstore_online
DB_USER=postgres
DB_PASSWORD=your_password

# JWT Secret
JWT_SECRET_KEY=your-super-secret-jwt-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# App Configuration
APP_NAME=BookStore API
APP_VERSION=1.0.0
DEBUG=True

# CORS Settings
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8080"]
```

## 5. KHỞI TẠO DATABASE (ĐƠN GIẢN)

```bash
# Chỉ cần chạy 1 lệnh duy nhất
python setup_database.py
```

**Hoặc cách thủ công:**
```bash
# Chạy script khởi tạo database
python database.py

# Hoặc chạy seed data
python seed_data.py
```

## 6. CHẠY ỨNG DỤNG

```bash
# Chạy FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 7. KIỂM TRA DATABASE

```bash
# Test connection
python -c "from database import test_connection; test_connection()"

# Health check
python -c "from database import health_check; print(health_check())"
```

## 8. BACKUP & RESTORE DATABASE

### Backup:
```bash
pg_dump -U postgres -h localhost bookstore_online > backup.sql
```

### Restore:
```bash
psql -U postgres -h localhost bookstore_online < backup.sql
```

## 9. TROUBLESHOOTING

### Lỗi kết nối:
- Kiểm tra PostgreSQL service đang chạy
- Kiểm tra username/password
- Kiểm tra port (mặc định 5432)
- Kiểm tra firewall settings

### Lỗi permissions:
```sql
-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE bookstore_online TO your_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_user;
```

### Reset database:
```bash
# Xóa và tạo lại database
python -c "from database import drop_tables, create_tables; drop_tables(); create_tables()"
```
