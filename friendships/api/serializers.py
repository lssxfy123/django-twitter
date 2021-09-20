from django.contrib.auth.models import User
from rest_framework import serializers
from accounts.api.serializers import UserSerializerForFriendship
from friendships.models import Friendship
from rest_framework.exceptions import ValidationError
from friendships.services import FriendshipService


class FollowerSerializer(serializers.ModelSerializer):
    """
    可以通过source=xxx指定去访问每个model instance的xxx方法或属性
    即model_instance.xxx来获得数据
    这里是指定user是from_user
    """
    user = UserSerializerForFriendship(source='from_user')
    created_at = serializers.DateTimeField()
    has_followed = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        # fields中的字段会首先从FollowerSerializer中查找
        # 如果找不到，就会从model指定的模型中查找
        fields = ('user', 'created_at', 'has_followed')

    def get_has_followed(self, obj):
        if self.context['request'].user.is_anonymous:
            return False

        # <TODO> 这个部分会对每个 object 都去执行一次 SQL 查询，速度会很慢，如何优化呢？
        # 我们将在后序的课程中解决这个问题
        return FriendshipService.has_followed(
            self.context['request'].user,
            obj.from_user,
        )


class FollowingSerializer(serializers.ModelSerializer):
    user = UserSerializerForFriendship(source='to_user')
    created_at = serializers.DateTimeField()
    has_followed = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ('user', 'created_at', 'has_followed')

    def get_has_followed(self, obj):
        if self.context['request'].user.is_anonymous:
            return False
        return FriendshipService.has_followed(
            self.context['request'].user,
            obj.to_user,
        )


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
