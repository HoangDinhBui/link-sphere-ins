"""
utils/resilience.py
-------------------
Tập hợp các helper để gọi external service một cách an toàn hơn.

Hai pattern chính ở đây:
- tenacity  : retry với exponential backoff khi gặp lỗi tạm thời
- pybreaker : circuit breaker để tránh tiếp tục gọi một service đang chết

Về circuit breaker — nó có 3 trạng thái:
  CLOSED    → bình thường, request đi qua hết.
  OPEN      → service đang lỗi, reject ngay không thèm thử.
  HALF-OPEN → sau một khoảng timeout, cho qua 1 request để xem service sống lại chưa.
"""

import logging
import functools

import pybreaker
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Circuit Breakers
# ---------------------------------------------------------------------------

class CircuitBreakerLogger(pybreaker.CircuitBreakerListener):
    """Ghi log mỗi khi circuit breaker đổi trạng thái, có lỗi, hoặc gọi thành công."""

    def state_change(self, cb, old_state, new_state):
        logger.warning(
            "[CircuitBreaker] '%s' thay đổi trạng thái: %s → %s",
            cb.name,
            old_state.name,
            new_state.name,
        )

    def failure(self, cb, exc):
        logger.error(
            "[CircuitBreaker] '%s' ghi nhận lỗi (%d/%d): %s",
            cb.name,
            cb.fail_counter,
            cb.fail_max,
            exc,
        )

    def success(self, cb):
        logger.info("[CircuitBreaker] '%s' gọi thành công.", cb.name)


# Circuit breaker cho Resend (email service).
# 3 lần lỗi liên tiếp là đủ để mở mạch — đợi 60s rồi mới thử lại.
email_circuit_breaker = pybreaker.CircuitBreaker(
    fail_max=3,
    reset_timeout=60,
    name="EmailService",
    listeners=[CircuitBreakerLogger()],
)

# Circuit breaker cho OpenSearch — ngưỡng cao hơn vì search thường chịu tải tốt hơn email.
opensearch_circuit_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=30,
    name="OpenSearchService",
    listeners=[CircuitBreakerLogger()],
)


# ---------------------------------------------------------------------------
# Exponential Backoff — dùng tenacity
# ---------------------------------------------------------------------------

def with_exponential_backoff(
    max_attempts: int = 3,
    wait_min: float = 1.0,
    wait_max: float = 10.0,
    retry_exceptions: tuple = (Exception,),
):
    """
    Decorator thêm retry + exponential backoff cho bất kỳ hàm nào.

    Mỗi lần retry sẽ chờ lâu hơn lần trước (tăng theo hàm mũ),
    giúp tránh spam request vào một service đang có vấn đề.

    Args:
        max_attempts     : Tổng số lần thử, kể cả lần đầu.
        wait_min         : Thời gian chờ tối thiểu giữa hai lần thử (giây).
        wait_max         : Thời gian chờ tối đa, không tăng quá con số này (giây).
        retry_exceptions : Chỉ retry khi gặp các exception trong tuple này.
                           Exception không thuộc danh sách sẽ không được retry.

    Ví dụ:
        @with_exponential_backoff(max_attempts=4, wait_min=2, wait_max=30)
        def call_external_api():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retrying = retry(
                stop=stop_after_attempt(max_attempts),
                wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
                retry=retry_if_exception_type(retry_exceptions),
                before_sleep=before_sleep_log(logger, logging.WARNING),
                reraise=True,
            )
            return retrying(func)(*args, **kwargs)
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# Kết hợp cả hai: Circuit Breaker bọc ngoài, Exponential Backoff bọc trong
# ---------------------------------------------------------------------------

def resilient_call(func, circuit_breaker: pybreaker.CircuitBreaker, *args, **kwargs):
    """
    Gọi `func` với cả exponential backoff lẫn circuit breaker.

    Cơ chế hoạt động:
    - Bên trong: retry tối đa 3 lần, mỗi lần chờ 1–10s tăng dần.
    - Bên ngoài: circuit breaker bọc toàn bộ — nếu đang OPEN thì fail ngay,
      không mất thời gian vào retry.

    Circuit breaker được đặt ngoài cùng để các lần retry bên trong
    không bị tính vào fail_counter (chỉ tính 1 lần nếu cả batch retry đều lỗi).

    Args:
        func           : Hàm cần gọi.
        circuit_breaker: Circuit breaker muốn áp dụng.
        *args, **kwargs: Tham số truyền vào func.

    Raises:
        pybreaker.CircuitBreakerError: Nếu circuit đang OPEN.
        RetryError                   : Nếu đã hết lượt retry mà vẫn lỗi.
    """
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _call_with_retry():
        return func(*args, **kwargs)

    # Circuit breaker bọc ngoài để một batch retry chỉ tính là 1 lần thất bại.
    return circuit_breaker.call(_call_with_retry)
