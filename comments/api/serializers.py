from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from comments.models import Comment
from accounts.api.serializers import UserSerializerForComment
from tweets.models import Tweet


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializerForComment()

    class Meta:
        model = Comment
        fields = ('id', 'tweet_id', 'user', 'content', 'created_at')


class CommentSerializerForCreate(serializers.ModelSerializer):
    # 这两项必须手动添加，
    # 因为默认ModelSerializer只会自动包含user和tweet，而不是user_id和tweet_id
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
