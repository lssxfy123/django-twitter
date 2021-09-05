from rest_framework import viewsets, status
from likes.api.serializers import (
    LikeSerializer,
    LikeSerializerForCreate,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from likes.models import Like
from util.decorators import required_params


class LikeViewSet(viewsets.GenericViewSet):
    queryset = Like.objects.all()
    # 如果不同的api需要不同的permission，就重载get_permissions
    # 如果都一致，就可以使用perimission_classes
    permission_classes = [IsAuthenticated]
    serializer_class = LikeSerializerForCreate

    @required_params(request_attr='data', params=['content_type', 'object_id'])
    def create(self, request):
        serializer = LikeSerializerForCreate(
            data=request.data,
            context={'request': request})
        if not serializer.is_valid():
            return Response({
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        like = serializer.save()
        return Response(
            LikeSerializer(like).data,
            status=status.HTTP_201_CREATED
        )
