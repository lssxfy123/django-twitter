from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from comments.models import Comment
from accounts.api.serializers import UserSerializerForComment
from tweets.models import Tweet
from likes.services import LikeService


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializerForComment(source='cached_user')
    has_liked = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = (
            'id',
            'tweet_id',
            'user',
            'content',
            'created_at',
            'likes_count',
            'has_liked',
        )

    def get_likes_count(self, obj):
        return obj.like_set.count()

    def get_has_liked(self, obj):
        return LikeService.has_liked(self.context['request'].user, obj)


class CommentSerializerForCreate(serializers.ModelSerializer):
    # 这两项必须手动添加，
    # 因为默认ModelSerializer中的user_id和tweet_id都是只读字段
    # 创建时validate()的data参数和create()的validated_data都不包含这两个字段
    # 它们只包含可写字段
    user_id = serializers.IntegerField()
    tweet_id = serializers.IntegerField()

    class Meta:
        model = Comment
        fields = ('user_id', 'tweet_id', 'content')

    def validate(self, data):
        tweet_id = data["tweet_id"]
        if not Tweet.objects.filter(id=tweet_id).exists():
            raise ValidationError({"message": "tweet doses not exist."})
        return data

    def create(self, validated_data):
        return Comment.objects.create(
            user_id=validated_data["user_id"],
            tweet_id=validated_data["tweet_id"],
            content=validated_data["content"],
        )


class CommentSerializerForUpdate(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('content',)

    def update(self, instance, validated_data):
        instance.content = validated_data['content']
        instance.save()
        # update方法要求return修改后的instance
        return instance
