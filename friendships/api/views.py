from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth.models import User
from friendships.models import Friendship
from friendships.api.serializers import (
    FollowerSerializer,
    FollowingSerializer,
    FriendshipSerializerForCreate,
)
from friendships.paginations import FriendshipPagination


class FriendshipViewSet(viewsets.GenericViewSet):
    """
    我们希望POST /api/friendship/1/follow是取follow user_id=1的用户
    因此这里queryset需要是User.objects.all()
    如果设置为Friendship.objects.all()，就会返回404
    因为follow()中会调用get_object()方法去验证user_id=1的用户是否存在
    也就是queryset.filter(pk=1)查询一下这个object是否存在
    pk就是PrimaryKey的简写
    """
    queryset = User.objects.all()
    serializer_class = FriendshipSerializerForCreate
    pagination_class = FriendshipPagination

    def list(self, request):
        if 'to_user_id' in request.query_params:
            friendships = Friendship.objects\
                .filter(to_user_id=request.query_params['to_user_id'])
            serializer = FollowerSerializer(
                friendships,
                many=True,
                context={'request': request}
            )
            return Response({
                'followers': serializer.data
            })

        if 'from_user_id' in request.query_params:
            friendships = Friendship.objects\
                .filter(from_user_id=request.query_params['from_user_id'])
            serializer = FollowingSerializer(
                friendships,
                many=True,
                context={'request': request}
            )
            return Response({
                'followings': serializer.data
            })

        return Response(
            "missing to_user_id or from_user_id",
            status.HTTP_400_BAD_REQUEST
        )

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    def followers(self, request, pk):
        """
        获取有谁关注了user_id=pk的用户
        URL访问地址为：GET /api/friendships/1/followers/
        """
        friendships = Friendship.objects.filter(to_user_id=pk)\
            .order_by('-created_at')
        page = self.paginate_queryset(friendships)
        serializer = FollowerSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    def followings(self, request, pk):
        """
        获取user_id=pk的用户关注了谁
        """
        friendships = Friendship.objects.filter(from_user_id=pk)\
            .order_by('-created_at')
        page = self.paginate_queryset(friendships)
        serializer = FollowingSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    def follow(self, request, pk):
        """
        创建好友关系，关注user_id=pk的用户
        需要验证是否登录：IsAuthenticated
        """
        # 相对于FriendshipSerializerForCreate中校验函数中，另外一种验证
        # user_id=pk的用户是否存在
        # 它会自动从queryset中查找id=pk的用户，找不到会返回404
        # 而serializer中会返回400
        self.get_object()

        # 特殊判断重复follow的情况
        # 静默处理，不报错，因为这类操作多是因为网络延迟，不需要当做错误处理
        if Friendship.objects.filter(from_user=request.user, to_user=pk)\
                .exists():
            return Response({
                'success': True,
                'duplicate': True,
            }, status=status.HTTP_201_CREATED)

        # 这里不能直接data=request.data，之前的SignupSerializer可以这样用
        # 是因为其使用的参数是django rest_framework中自带的
        # 而FriendshipSerializerForCreate使用的参数是自定义的
        serializer = FriendshipSerializerForCreate(data={
            'from_user_id': request.user.id,
            'to_user_id': pk,
        })

        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # 会调用FriendshipSerializerForCreate中的create()
        instance = serializer.save()
        return Response(
            FollowingSerializer(
                instance=instance,
                context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    def unfollow(self, request, pk):
        """
        取消关注user_id=pk的用户
        """
        self.get_object()
        if request.user.id == int(pk):
            return Response({
                'success': False,
                'message': 'You cannot unfollow youself.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # https://docs.djangoproject.com/en/3.1/ref/models/querysets/#delete
        # Queryset 的 delete 操作返回两个值，一个是删了多少数据，一个是具体每种类型删了多少
        # 为什么会出现多种类型数据的删除？因为可能因为 foreign key 设置了 cascade 出现级联
        # 删除，也就是比如 A model 的某个属性是 B model 的 foreign key，并且设置了
        # on_delete=models.CASCADE, 那么当 B 的某个数据被删除的时候，A 中的关联也会被删除。
        # 所以 CASCADE 是很危险的，我们一般最好不要用，而是用 on_delete=models.SET_NULL
        # 取而代之，这样至少可以避免误删除操作带来的多米诺效应。
        deleted, _ = Friendship.objects.filter(
            from_user=request.user,
            to_user=pk
        ).delete()
        return Response({'success': True, 'deleted': deleted})
