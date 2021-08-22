from django.contrib.auth.models import User
from rest_framework import serializers
from accounts.api.serializers import UserSerializerForFriendship
from friendships.models import Friendship
from rest_framework.exceptions import ValidationError


class FollowerSerializer(serializers.ModelSerializer):
    """
    可以通过source=xxx指定去访问每个model instance的xxx方法或属性
    即model_instance.xxx来获得数据
    这里是指定user是from_user
    """
    user = UserSerializerForFriendship(source='from_user')
    created_at = serializers.DateTimeField()

    class Meta:
        model = Friendship
        # fields中的字段会首先从FollowerSerializer中查找
        # 如果找不到，就会从model指定的模型中查找
        fields = ('user', 'created_at')


class FollowingSerializer(serializers.ModelSerializer):
    user = UserSerializerForFriendship(source='to_user')
    created_at = serializers.DateTimeField()

    class Meta:
        model = Friendship
        fields = ('user', 'created_at')


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
