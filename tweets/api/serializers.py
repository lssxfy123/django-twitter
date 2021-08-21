from rest_framework import serializers
from tweets.models import Tweet
from django.contrib.auth.models import User
from accounts.api.serializers import UserSerializerForTweet


class TweetSerializer(serializers.ModelSerializer):
    user = UserSerializerForTweet()

    class Meta:
        model = Tweet
        fields = ('id', 'user', 'created_at', 'content')


class TweetCreateSerializer(serializers.ModelSerializer):
    content = serializers.CharField(min_length=6, max_length=140)

    class Meta:
        model = Tweet
        # 这里不能放入user_id, email等信息
        # 因为Tweet创建肯定是当前登陆用户创建的
        fields = ('content', )

    def create(self, validated_data):
        """
        参考之前的accounts/views中的signup
        如果调用serializer.save()保存创建的tweet
        就必须实现create()方法，serializer.save()
        源码中可以看出，如果不实现，就会抛出异常错误
        """
        content = validated_data['content']
        # 创建TweetCreateSerializer传递的额外信息到context参数中
        user = self.context['request'].user
        tweet = Tweet.objects.create(user=user, content=content)
        return tweet
