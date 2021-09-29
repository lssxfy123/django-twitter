from django.contrib.auth.models import User
from rest_framework import serializers
from accounts.api.serializers import UserSerializerForFriendship
from friendships.models import Friendship
from rest_framework.exceptions import ValidationError
from friendships.services import FriendshipService


class FollowingUserIdSetMixin:
    """
    公用的插件类
    """

    @property
    def following_user_id_set(self: serializers.ModelSerializer):
        """
        获取当前登录用户所关注的所有好友的user id，从Memcached中或者数据库中获取
        并且存储到serializer对象中，相当于进一步缓存，由Memcached中缓存到了当前对象中
        由于serializer对象生存周期只在一次http请求中，所以它的缓存不需要考虑是否刷新
        的问题，当request请求结束后自然就销毁掉了
        """
        if self.context['request'].user.is_anonymous:
            return {}

        if hasattr(self, '_cached_following_user_id_set'):
            return self._cached_following_user_id_set
        user_id_set = FriendshipService.get_following_user_id_set(
            self.context['request'].user.id,
        )
        setattr(self, '_cached_following_user_id_set', user_id_set)
        return user_id_set


class FollowerSerializer(serializers.ModelSerializer, FollowingUserIdSetMixin):
    """
    可以通过source=xxx指定去访问每个model instance的xxx方法或属性
    即model_instance.xxx来获得数据
    这里是指定user是from_user
    """
    user = UserSerializerForFriendship(source='cached_from_user')
    created_at = serializers.DateTimeField()
    has_followed = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        # fields中的字段会首先从FollowerSerializer中查找
        # 如果找不到，就会从model指定的模型中查找
        fields = ('user', 'created_at', 'has_followed')

    def get_has_followed(self, obj):
        """
        利用缓存优化查询
        """
        return obj.from_user_id in self.following_user_id_set


class FollowingSerializer(serializers.ModelSerializer, FollowingUserIdSetMixin):
    user = UserSerializerForFriendship(source='cached_to_user')
    created_at = serializers.DateTimeField()
    has_followed = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ('user', 'created_at', 'has_followed')

    def get_has_followed(self, obj):
        return obj.to_user_id in self.following_user_id_set


class FriendshipSerializerForCreate(serializers.ModelSerializer):
    from_user_id = serializers.IntegerField()
    to_user_id = serializers.IntegerField()

    class Meta:
        model = Friendship
        fields = ['from_user_id', 'to_user_id']

    def validate(self, data):
        if data['from_user_id'] == data['to_user_id']:
            raise ValidationError({
                'message': 'from_user_id and to_user_id should be different'
            })

        # 验证关注或取消关注的用户是否存在
        # User表单中主键字段是id
        if not User.objects.filter(id=data['to_user_id']).exists():
            raise ValidationError({
                'message': 'You can not follow a non-exist user'
            })
        return data

    def create(self, validated_data):
        from_user_id = validated_data['from_user_id']
        to_user_id = validated_data['to_user_id']
        friendship = Friendship.objects.create(
            from_user_id=from_user_id,
            to_user_id=to_user_id
        )
        return friendship
