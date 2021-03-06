from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.contrib.auth.models import User
from friendships.api.serializers import (
    FollowerSerializer,
    FollowingSerializer,
    FriendshipSerializerForCreate,
)
from friendships.services import FriendshipService
from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from gatekeeper.models import GateKeeper
from utils.paginations import EndlessPagination
from friendships.models import HBaseFollowing, HBaseFollower, Friendship


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
    pagination_class = EndlessPagination

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
    @method_decorator(
        ratelimit(key='user_or_ip', rate='3/s', method='GET', block=True))
    def followers(self, request, pk):
        """
        获取有谁关注了user_id=pk的用户
        URL访问地址为：GET /api/friendships/1/followers/
        """
        if GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            page = self.paginator.paginate_hbase(HBaseFollower, (pk,), request)
        else:
            friendships = Friendship.objects.filter(to_user_id=pk)\
                .order_by('-created_at')
            page = self.paginate_queryset(friendships)
        serializer = FollowerSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.paginator.get_paginated_response(serializer.data)

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    @method_decorator(
        ratelimit(key='user_or_ip', rate='3/s', method='GET', block=True))
    def followings(self, request, pk):
        """
        获取user_id=pk的用户关注了谁
        """
        if GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            page = self.paginator.paginate_hbase(HBaseFollowing, (pk,), request)
        else:
            friendships = Friendship.objects.filter(from_user_id=pk)\
              .order_by('-created_at')
            page = self.paginate_queryset(friendships)
        serializer = FollowingSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.paginator.get_paginated_response(serializer.data)

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    @method_decorator(
        ratelimit(key='user', rate='10/s', method='POST', block=True))
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
        if FriendshipService.has_followed(request.user.id, int(pk)):
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
        
        # 第一种触发删除cache某个key的做法，在follow和unfollow时进行cache删除
        # 存在的问题是，需要明确知道哪些地方对Friendship模型对应的表单进行了修改
        # 如果有遗漏，可能就会没有删除对应的cache，另外通过localhost/admin去创建
        # Friendship时，不会调用follow和unfollow，所以也不会进行cache删除
        # FriendshipService.invalidate_following_cache(request.user.id)
        return Response(
            FollowingSerializer(
                instance=instance,
                context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    @method_decorator(
        ratelimit(key='user', rate='10/s', method='POST', block=True))
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

        deleted = FriendshipService.unfollow(request.user.id, int(pk))
        return Response({'success': True, 'deleted': deleted})
