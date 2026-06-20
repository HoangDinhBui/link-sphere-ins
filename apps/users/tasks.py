"""
apps/users/tasks.py
--------------------
Các Celery task liên quan đến users.

Email được gửi qua background task thay vì gửi thẳng trong request vì:
- API trả về ngay, không bị block chờ SMTP
- Tự động retry nếu Resend đang gặp sực
- Circuit breaker ngăn việc cứ gọi vào một service đang chết
"""

import logging
import resend

from celery import shared_task
from django.conf import settings
import pybreaker

from utils.resilience import email_circuit_breaker, resilient_call

logger = logging.getLogger(__name__)


def _build_welcome_email_html(username: str) -> str:
    """Tạo nội dung HTML cho email chào mừng."""
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px; background-color: #f9f9f9;">
        <div style="text-align: center; padding-bottom: 20px;">
            <h2 style="color: #4A90E2; margin: 0; font-size: 28px;">LinkSphere 🌐</h2>
        </div>
        <div style="background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <h3 style="color: #333333; margin-top: 0;">Xin chào {username},</h3>
            <p style="color: #555555; line-height: 1.6; font-size: 16px;">Cảm ơn bạn đã gia nhập mạng xã hội <strong>LinkSphere</strong>. Chúng tôi rất vui mừng được chào đón bạn đến với cộng đồng của chúng tôi!</p>
            <p style="color: #555555; line-height: 1.6; font-size: 16px;">Hãy bắt đầu khám phá, kết nối với bạn bè và chia sẻ những khoảnh khắc tuyệt vời của bạn ngay hôm nay.</p>
            <div style="text-align: center; margin: 35px 0;">
                <a href="https://github.com/HoangDinhBui/link-sphere-ins" style="background-color: #4A90E2; color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 6px; font-weight: bold; font-size: 16px; display: inline-block;">Khám phá ngay</a>
            </div>
            <p style="color: #555555; line-height: 1.6; font-size: 16px;">Thân mến,<br/><strong>LinkSphere Team</strong></p>
        </div>
        <div style="text-align: center; margin-top: 25px; font-size: 13px; color: #999999;">
            <p style="margin: 5px 0;">Bạn nhận được email này vì đã đăng ký tài khoản tại LinkSphere.</p>
            <p style="margin: 5px 0;">
                <a href="https://github.com/HoangDinhBui/link-sphere-ins/blob/main/README.md" style="color: #4A90E2; text-decoration: none;">Điều khoản dịch vụ</a> &nbsp;|&nbsp;
                <a href="https://github.com/HoangDinhBui/link-sphere-ins/blob/main/README.md" style="color: #4A90E2; text-decoration: none;">Chính sách bảo mật</a>
            </p>
        </div>
    </div>
    """


def _send_via_resend(email: str, username: str) -> None:
    """Gọi Resend API để gửi email. Hàm này được wrap bởi resilient_call."""
    resend.api_key = settings.RESEND_API_KEY
    resend.Emails.send({
        "from": "LinkSphere <onboarding@resend.dev>",
        "to": email,
        "subject": "Chào mừng bạn đến với LinkSphere!",
        "html": _build_welcome_email_html(username),
    })


@shared_task(
    bind=True,
    name="users.send_welcome_email",
    max_retries=3,
    default_retry_delay=5,
    acks_late=True,
)
def send_welcome_email(self, email: str, username: str) -> dict:
    """
    Gửi email chào mừng với cả circuit breaker lẫn exponential backoff.

    Luồng xử lý:
    1. `resilient_call` gọi `_send_via_resend` với retry tự động bên trong.
    2. Nếu cả 3 lần retry đều thất bại, exception được đẩy ra ngoài.
    3. Celery bắt được exception đó và sẽ retry lại task sau 1s → 2s → 4s.
    4. Nếu circuit đang OPEN, fail ngay không tốn thêm retry.

    Args:
        email   : Địa chỉ email người nhận.
        username: Tên user để điền vào nội dung email.
    """
    logger.info("[EmailTask] Đang gửi email chào mừng tới '%s' cho user '%s'.", email, username)

    try:
        resilient_call(_send_via_resend, email_circuit_breaker, email, username)
        logger.info("[EmailTask] Gửi email thành công tới '%s'.", email)
        return {"status": "sent", "email": email}

    except pybreaker.CircuitBreakerError as exc:
        # Circuit đang OPEN — không retry thêm, tránh dồn load vào service đang có vấn đề.
        logger.error(
            "[EmailTask] Circuit Breaker OPEN — bỏ qua gửi email tới '%s'. Lý do: %s",
            email, exc,
        )
        # Trả về thay vì raise để task kết thúc đầy đủ, không để Celery dại mà retry tiếp.
        return {"status": "circuit_open", "email": email}

    except Exception as exc:
        logger.warning(
            "[EmailTask] Lỗi gửi email tới '%s' (lần thử %d/%d): %s",
            email,
            self.request.retries + 1,
            self.max_retries + 1,
            exc,
        )
        # Exponential backoff ở tầng Celery: lần 1 chờ 1s, lần 2 chờ 2s, lần 3 chờ 4s.
        retry_countdown = 2 ** self.request.retries
        raise self.retry(exc=exc, countdown=retry_countdown)
