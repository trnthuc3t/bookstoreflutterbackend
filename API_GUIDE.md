# =====================================================
# HƯỚNG DẪN CHẠY FASTAPI SERVER
# =====================================================

## 🎉 CHÚC MỪNG! Database đã được tạo thành công!

Bây giờ bạn cần chạy FastAPI server. Vì PowerShell có vấn đề, hãy làm theo các bước sau:

## 🔧 BƯỚC 1: MỞ COMMAND PROMPT

1. Nhấn `Win + R`
2. Gõ `cmd` và nhấn Enter
3. Navigate đến thư mục:
   ```cmd
   cd E:\ProjectAndroid\BookStoreFlutter\BookStoreBackend
   ```

## 📦 BƯỚC 2: CÀI ĐẶT DEPENDENCIES

```cmd
pip install fastapi uvicorn python-dotenv
```

## 🚀 BƯỚC 3: CHẠY SERVER

```cmd
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## ✅ KẾT QUẢ MONG ĐỢI

Bạn sẽ thấy:
```
INFO:     Will watch for changes in these directories: ['E:\\ProjectAndroid\\BookStoreFlutter\\BookStoreBackend']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

## 🌐 TRUY CẬP API

Sau khi server chạy thành công, bạn có thể truy cập:

- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **API Root**: http://localhost:8000/

## 📋 CÁC ENDPOINT CÓ SẴN

### Users:
- `GET /api/users` - Lấy danh sách người dùng
- `GET /api/users/{user_id}` - Lấy thông tin người dùng

### Books:
- `GET /api/books` - Lấy danh sách sách
- `GET /api/books/{book_id}` - Lấy chi tiết sách

### Categories:
- `GET /api/categories` - Lấy danh sách thể loại

### Cart:
- `GET /api/cart/{user_id}` - Lấy giỏ hàng
- `POST /api/cart` - Thêm vào giỏ hàng

### Orders:
- `GET /api/orders/{user_id}` - Lấy đơn hàng

### Stats:
- `GET /api/stats` - Thống kê tổng quan

## 🔍 TEST API

Bạn có thể test API bằng cách:

1. Mở browser và truy cập: http://localhost:8000/docs
2. Hoặc dùng curl:
   ```cmd
   curl http://localhost:8000/health
   curl http://localhost:8000/api/books
   ```

## 🎯 TIẾP THEO

Sau khi API chạy thành công, bạn có thể:

1. **Kết nối Flutter app** với API này
2. **Thêm authentication** (JWT tokens)
3. **Thêm file upload** cho hình ảnh sách
4. **Implement payment** integration
5. **Deploy lên production**

## 📞 HỖ TRỢ

Nếu gặp lỗi:
1. Kiểm tra PostgreSQL đang chạy
2. Kiểm tra database connection
3. Kiểm tra dependencies đã cài đặt
4. Sử dụng Command Prompt thay vì PowerShell

---
**🚀 Chúc bạn thành công với BookStore API!**
