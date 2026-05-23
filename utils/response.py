from rest_framework.response import Response
from django.utils import timezone
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import inline_serializer
from rest_framework import serializers

def swagger_response(data_serializer=None, many=False, name_prefix=""):
    fields = {
        'success': serializers.BooleanField(default=True),
        'message': serializers.CharField(default="Request successful"),
        'timestamp': serializers.CharField(default="2026-05-23T10:00:00Z"),
    }
    if data_serializer:
        if isinstance(data_serializer, type):
            if many:
                fields['data'] = data_serializer(many=True)
            else:
                fields['data'] = data_serializer()
        else:
            fields['data'] = data_serializer
    else:
        from drf_spectacular.types import OpenApiTypes
        fields['data'] = serializers.DictField(default={})

    return inline_serializer(
        name=f"{name_prefix}StandardResponse" if name_prefix else "StandardResponse",
        fields=fields
    )

class APIResponse:
    @staticmethod
    def success(data=None, message='Request successful', status_code=200):
        return Response({
            "success": True,
            "message": message,
            "data": data,
            "timestamp": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        }, status=status_code)

    @staticmethod
    def error(message="An error occurred", errors=None, error_code="ERROR", status_code=400):
        return Response({
            "success": False,
            "message": message,
            "errors": errors or [],
            "errorCode": error_code,
            "timestamp": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        }, status=status_code)

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'pageSize'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "success": True,
            "data": data,
            "pagination": {
                "page": self.page.number,
                "pageSize": self.get_page_size(self.request),
                "totalItems": self.page.paginator.count,
                "totalPages": self.page.paginator.num_pages
            }
        })