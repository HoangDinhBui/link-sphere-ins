from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.posts.models import Post
from apps.posts.serializers import PostSerializer
from utils.response import APIResponse, swagger_response
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from django.contrib.postgres.search import SearchQuery, SearchRank
from apps.users.serializers import UserSerializer
from apps.users.models import User

# Create your views here.
SearchPostSchema = inline_serializer(
    name='SearchPostData',
    fields={
        'query': serializers.CharField(),
        'count': serializers.IntegerField(),
        'results': PostSerializer(many=True)
    }
)

@extend_schema(
    parameters=[
        OpenApiParameter(name='q', description='Từ khóa tìm kiếm', required=True, type=str),
    ],
    responses={200: swagger_response(SearchPostSchema, name_prefix='SearchPost')},
    description="Tìm kiếm bài viết theo nội dung"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_posts(request):
    query = request.query_params.get('q', '').strip()

    if not query:
        # return Response({'error': 'Query parameter "q" is required.'}, status=400)
        return APIResponse.error(
            message='Query parameter "q" is required.',
            error_code='QUERY_PARAM_REQUIRED',
            status_code=400
        )

    search_query = SearchQuery(query)
    posts = Post.objects.annotate(
        rank=SearchRank('search_vector', search_query)
    ).filter(search_vector=search_query).select_related('author').order_by('-rank', '-created_at')

    serializer = PostSerializer(posts, many=True, context={'request': request})
    # return Response({
    #     'query': query,
    #     'count': posts.count(),
    #     'results': serializer.data
    # })
    return APIResponse.success(
        data={
            'query': query,
            'count': posts.count(),
            'results': serializer.data
        }
    )

SearchUserSchema = inline_serializer(
    name='SearchUserData',
    fields={
        'query': serializers.CharField(),
        'count': serializers.IntegerField(),
        'results': UserSerializer(many=True)
    }
)

@extend_schema(
    parameters=[
        OpenApiParameter(name='q', description='Tên username cần tìm kiếm', required=True, type=str),
    ],
    responses={200: swagger_response(SearchUserSchema, name_prefix='SearchUser')},
    description="Tìm kiếm người dùng theo username"
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    query = request.query_params.get('q', '').strip()

    if not query:
        # return Response({'error': 'Query parameter "q" is required.'}, status=400)
        return APIResponse.error(
            message='Query parameter "q" is required.',
            error_code='QUERY_PARAM_REQUIRED',
            status_code=400
        )

    users = User.objects.filter(username__icontains=query).order_by('username')

    serializer = UserSerializer(users, many=True)
    # return Response({
    #     'query': query,
    #     'count': users.count(),
    #     'results': serializer.data
    # })
    return APIResponse.success(
        data={
            'query': query,
            'count': users.count(),
            'results': serializer.data
        }
    )
