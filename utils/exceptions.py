from rest_framework.views import exception_handler
from django.utils import timezone

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        errors = []

        if isinstance(response.data, dict):
            for field, messages in response.data.items():
                if isinstance(messages, list):
                    for msg in messages:
                        errors.append({"field": field, "message": str(msg)})
                else:
                    errors.append({"field": field, "message": str(messages)})
        elif isinstance(response.data, list):
            for msg in response.data:
                errors.append({"field": "non_field_errors", "message": str(msg)})
        response.data = {
            "success": False,
            "message": "Validation failed" if response.status_code == 400 else "Server Error",
            "errors": errors,
            "errorCode": "VALIDATION_ERROR" if response.status_code == 400 else "SERVER_ERROR",
            "timestamp": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        }

    return response