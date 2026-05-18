from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.posts.models import Post
from apps.posts.serializers import PostSerializer

# Create your views here.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_posts(request):
    query = request.query_params.get('q', '').strip()

    if not query:
        return Response({'error': 'Query parameter "q" is required.'}, status=400)

    posts = Post.objects.filter(content__icontains=query).select_related('author').order_by('-created_at')

    serializer = PostSerializer(posts, many=True, context={'request': request})
    return Response({
        'query': query,
        'count': posts.count(),
        'results': serializer.data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    from apps.users.models import User
    from apps.users.serializers import UserSerializer

    query = request.query_params.get('q', '').strip()

    if not query:
        return Response({'error': 'Query parameter "q" is required.'}, status=400)

    users = User.objects.filter(username__icontains=query).order_by('username')

    serializer = UserSerializer(users, many=True)
    return Response({
        'query': query,
        'count': users.count(),
        'results': serializer.data
    })
