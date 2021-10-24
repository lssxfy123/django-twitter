from rest_framework import viewsets, status
from likes.api.serializers import (
    LikeSerializer,
    LikeSerializerForCreate,
    LikeSerializerForCancel,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from likes.models import Like
from utils.decorators import required_params
from rest_framework.decorators import action
from inbox.services import NotificationService
from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit


class LikeViewSet(viewsets.GenericViewSet):
    queryset = Like.objects.all()
    # 如果不同的api需要不同的permission，就重载get_permissions
    # 如果都一致，就可以使用perimission_classes
    permission_classes = [IsAuthenticated]
    serializer_class = LikeSerializerForCreate

    @required_params(method='POST', params=['content_type', 'object_id'])
    @method_decorator(
        ratelimit(key='user', rate='10/s', method='POST', block=True))
    def create(self, request):
        serializer = LikeSerializerForCreate(
            data=request.data,
            context={'request': request})
        if not serializer.is_valid():
            return Response({
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        like, created = serializer.get_or_create()
        if created:
            NotificationService.send_like_notification(like)
        return Response(
            LikeSerializer(like).data,
            status=status.HTTP_201_CREATED
        )

    @action(methods=['POST'], detail=False)
    @required_params(method='POST', params=['content_type', 'object_id'])
    @method_decorator(
        ratelimit(key='user', rate='10/s', method='POST', block=True))
    def cancel(self, request):
        serializer = LikeSerializerForCancel(
            data=request.data,
            context={'request': request},
        )

        if not serializer.is_valid():
            return Response({
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        deleted = serializer.cancel()
        return Response({
            'success': True,
            'deleted': deleted
        },
            status=status.HTTP_200_OK)
