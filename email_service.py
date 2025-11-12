import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

# Email Configuration
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
FROM_EMAIL = os.getenv('FROM_EMAIL', SMTP_USERNAME)
FROM_NAME = os.getenv('FROM_NAME', 'BookStore')

class EmailService:
    @staticmethod
    def send_email(to_email: str, subject: str, html_content: str, text_content: str = None):
        """
        Gửi email qua Gmail SMTP
        
        Args:
            to_email: Địa chỉ email người nhận
            subject: Tiêu đề email
            html_content: Nội dung HTML
            text_content: Nội dung text thuần (fallback)
        """
        if not SMTP_USERNAME or not SMTP_PASSWORD:
            print(" SMTP credentials not configured. Email not sent.")
            return False
        
        try:
            # Tạo message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f"{FROM_NAME} <{FROM_EMAIL}>"
            message['To'] = to_email
            
            # Thêm nội dung text và HTML
            if text_content:
                part1 = MIMEText(text_content, 'plain', 'utf-8')
                message.attach(part1)
            
            part2 = MIMEText(html_content, 'html', 'utf-8')
            message.attach(part2)
            
            # Kết nối và gửi email
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(message)
            
            print(f" Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            print(f" Failed to send email to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_verification_email(to_email: str, username: str, verification_link: str):
        """
        Gửi email xác thực tài khoản
        """
        subject = "Xác thực tài khoản BookStore của bạn"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; padding: 12px 30px; background-color: #2196F3; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1> Chào mừng đến với BookStore!</h1>
                </div>
                <div class="content">
                    <h2>Xin chào {username},</h2>
                    <p>Cảm ơn bạn đã đăng ký tài khoản tại BookStore!</p>
                    <p>Vui lòng click vào nút bên dưới để xác thực địa chỉ email của bạn:</p>
                    <div style="text-align: center;">
                        <a href="{verification_link}" class="button">Xác thực Email</a>
                    </div>
                    <p>Hoặc copy link sau vào trình duyệt:</p>
                    <p style="word-break: break-all; color: #2196F3;">{verification_link}</p>
                    <p><strong>Lưu ý:</strong> Link xác thực này sẽ hết hạn sau 24 giờ.</p>
                    <hr>
                    <p style="color: #666; font-size: 14px;">Nếu bạn không đăng ký tài khoản này, vui lòng bỏ qua email này.</p>
                </div>
                <div class="footer">
                    <p>© 2024 BookStore. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Chào mừng đến với BookStore!
        
        Xin chào {username},
        
        Cảm ơn bạn đã đăng ký tài khoản tại BookStore!
        Vui lòng truy cập link sau để xác thực email:
        
        {verification_link}
        
        Link này sẽ hết hạn sau 24 giờ.
        
        Nếu bạn không đăng ký tài khoản này, vui lòng bỏ qua email này.
        
        © 2024 BookStore
        """
        
        return EmailService.send_email(to_email, subject, html_content, text_content)
    
    @staticmethod
    def send_password_reset_email(to_email: str, username: str, reset_link: str):
        """
        Gửi email đặt lại mật khẩu
        """
        subject = "Đặt lại mật khẩu BookStore"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #f44336; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 5px 5px; }}
                .button {{ display: inline-block; padding: 12px 30px; background-color: #f44336; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
                .warning {{ background-color: #fff3cd; border: 1px solid #ffc107; padding: 15px; border-radius: 5px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Đặt lại mật khẩu</h1>
                </div>
                <div class="content">
                    <h2>Xin chào {username},</h2>
                    <p>Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản BookStore của bạn.</p>
                    <p>Click vào nút bên dưới để tạo mật khẩu mới:</p>
                    <div style="text-align: center;">
                        <a href="{reset_link}" class="button">Đặt lại mật khẩu</a>
                    </div>
                    <p>Hoặc copy link sau vào trình duyệt:</p>
                    <p style="word-break: break-all; color: #f44336;">{reset_link}</p>
                    <div class="warning">
                        <strong>Lưu ý quan trọng:</strong>
                        <ul>
                            <li>Link này chỉ có hiệu lực trong 1 giờ</li>
                            <li>Chỉ sử dụng được một lần duy nhất</li>
                        </ul>
                    </div>
                    <hr>
                    <p style="color: #666; font-size: 14px;">Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này. Mật khẩu của bạn sẽ không thay đổi.</p>
                </div>
                <div class="footer">
                    <p>© 2024 BookStore. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Đặt lại mật khẩu BookStore
        
        Xin chào {username},
        
        Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn.
        Vui lòng truy cập link sau để tạo mật khẩu mới:
        
        {reset_link}
        
        Lưu ý:
        - Link này chỉ có hiệu lực trong 1 giờ
        - Chỉ sử dụng được một lần duy nhất
        
        Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua email này.
        
        © 2024 BookStore
        """
        
        return EmailService.send_email(to_email, subject, html_content, text_content)
    
    @staticmethod
    def send_welcome_email(to_email: str, username: str):
        """
        Gửi email chào mừng sau khi xác thực thành công
        """
        subject = "Chào mừng bạn đến với BookStore!"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 30px; border: 1px solid #ddd; border-radius: 0 0 5px 5px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Chào mừng bạn!</h1>
                </div>
                <div class="content">
                    <h2>Xin chào {username},</h2>
                    <p>Tài khoản của bạn đã được xác thực thành công!</p>
                    <p>Bạn đã có thể:</p>
                    <ul>
                        <li> Duyệt và mua hàng ngàn đầu sách</li>
                        <li> Thanh toán an toàn và thuận tiện</li>
                        <li> Theo dõi đơn hàng của bạn</li>
                        <li> Đánh giá và bình luận sách</li>
                    </ul>
                    <p>Chúc bạn có trải nghiệm mua sắm tuyệt vời tại BookStore!</p>
                </div>
                <div class="footer">
                    <p>© 2024 BookStore. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return EmailService.send_email(to_email, subject, html_content)


