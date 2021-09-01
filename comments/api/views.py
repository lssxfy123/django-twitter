from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from comments.api.permissions import IsObjectOwner
from rest_framework.response import Response
from comments.api.serializers import (
    CommentSerializer,
    CommentSerializerForCreate,
    CommentSerializerForUpdate,
)
from comments.models import Comment


class CommentViewSet(viewsets.GenericViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializerForCreate

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]

        # 两个权限检测都要执行，如果只写IsObjectOwner()
        # 假设未登录，尽管在IsObjectOwner()中也会拒绝这次访问
        # 但返回的提示信息会具有误导性，它会返回没有权限访问这个对象
        # 实际是有权限的，只是没有登录
        # 权限检测是按照顺序来的
        if self.action in ['update', 'destroy']:
            return [IsAuthenticated(), IsObjectOwner()]
        return [AllowAny()]

    def create(self, request):
        data = {
            'user_id': request.user.id,
            'tweet_id': request.data.get('tweet_id'),
            'content': request.data.get('content'),
        }
        serializer = CommentSerializerForCreate(data=data)
        if not serializer.is_valid():
            return Response({
                "message": "Please check input.",
                "errors": serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        comment = serializer.save()
        return Response(
            CommentSerializer(comment).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """
        update()对应的是/api/comments/pk/，相当于@action中detail=True
        所以需要检测id=pk的comment对象是否存在
        get_object()会自动进行检测，如果不存在为抛出404
        所以无需做额外的检测
        """
        serializer = CommentSerializerForUpdate(
            instance=self.get_object(),
            data=request.data,
        )

        if not serializer.is_valid():
            return Response({
                "message": "Please check input."
            }, status=status.HTTP_400_BAD_REQUEST)
        # save 方法会触发 serializer 里的 update 方法，点进 save 的具体实现里可以看到
        # save 是根据 instance 参数有没有传来决定是触发 create 还是 update
        comment = serializer.save()
        return Response(
            CommentSerializer(comment).data,
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        comment.delete()
        # DRF 里默认 destroy 返回的是 status code = 204 no content
        # 这里 return 了 success=True 更直观的让前端去做判断，所以 return 200 更合适
        return Response({"success": True}, status=status.HTTP_200_OK)




