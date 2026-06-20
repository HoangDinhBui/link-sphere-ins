import pytest
from unittest.mock import patch
from apps.users.tasks import send_welcome_email
from utils.resilience import email_circuit_breaker

@pytest.mark.django_db
class TestEmailTaskResilience:

    def setup_method(self):
        # Đảm bảo trước mỗi test, circuit breaker được đóng (hoạt động bình thường)
        email_circuit_breaker.close()

    @patch('apps.users.tasks._send_via_resend')
    def test_task_retries_on_failure(self, mock_resend):
        # Giả lập Resend luôn luôn báo lỗi
        mock_resend.side_effect = Exception("Resend is down!")

        # Gọi task trực tiếp (không dùng .delay() để test code bên trong)
        # Bắt exception do Celery's self.retry ném ra (Retry exception)
        with pytest.raises(Exception):
            send_welcome_email('test@gmail.com', 'testuser')

        # Đảm bảo nó đã cố gắng thử gọi Resend đúng 3 lần (Tenacity config)
        assert mock_resend.call_count == 3

    @patch('apps.users.tasks._send_via_resend')
    def test_circuit_breaker_opens_after_failures(self, mock_resend):
        # Giả lập Resend luôn lỗi
        mock_resend.side_effect = Exception("Resend is down!")

        # Gọi 3 lần để ép Circuit Breaker đứt cầu chì (fail_max = 3)
        for i in range(3):
            try:
                send_welcome_email(f'test{i}@gmail.com', 'testuser')
            except Exception:
                pass
            
        # Tới lúc này, mạch phải báo OPEN
        assert email_circuit_breaker.current_state == "open"

        # Lần gọi thứ 4, nó sẽ fail ngay lập tức, trả về status: "circuit_open"
        result = send_welcome_email('test4@gmail.com', 'testuser')
        
        assert result['status'] == 'circuit_open'
        assert result['email'] == 'test4@gmail.com'
