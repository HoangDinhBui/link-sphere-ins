import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_redis_dependencies():
    """Mock Celery and Channels to avoid Redis connection errors during tests."""
    with patch('apps.notifications.tasks.send_notification_task.delay') as mock_celery:
        with patch('apps.notifications.utils.async_to_sync') as mock_channels:
            yield
