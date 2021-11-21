from django.contrib.auth.models import User
from rest_framework import serializers
from accounts.api.serializers import UserSerializerForFriendship
from friendships.models import Friendship
from rest_framework.exceptions import ValidationError
from friendships.services import FriendshipService
from accounts.services import UserService


class BaseFriendshipSerializer(serializers.Serializer):
    """
    公用的Serializer基类
    """
    user = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    has_followed = serializers.SerializerMethodField()

    # 这个Serializer基类是用来做渲染的，不用实现update和create
    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    # 类似C++中的虚函数，基类中的某个方法是抽象方法，python中就抛出未实现的error
    def get_user_id(self, obj):
        raise NotImplementedError

    def _get_following_user_id_set(self: serializers.ModelSerializer):
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

    def get_has_followed(self, obj):
        return self.get_user_id(obj)in self._get_following_user_id_set()

    def get_user(self, obj):
        user = UserService.get_user_by_id(self.get_user_id(obj))
        return UserSerializerForFriendship(user).data

    def get_created_at(self, obj):
        return obj.created_at


class FollowerSerializer(BaseFriendshipSerializer):
    def get_user_id(self, obj):
        return obj.from_user_id


class FollowingSerializer(BaseFriendshipSerializer):
    def get_user_id(self, obj):
        return obj.to_user_id


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
        friendship = FriendshipService.follow(
            from_user_id=from_user_id,
            to_user_id=to_user_id
        )
        return friendship
