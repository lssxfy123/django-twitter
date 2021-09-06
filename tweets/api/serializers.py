from rest_framework import serializers
from tweets.models import Tweet
from comments.api.serializers import CommentSerializer
from accounts.api.serializers import UserSerializerForTweet
from likes.services import LikeService
from likes.api.serializers import LikeSerializer


class TweetSerializer(serializers.ModelSerializer):
    user = UserSerializerForTweet()
    # 是否被赞， 需要实现一个get_has_liked()方法
    # SerializerMethodField()不是原本就存在的，需要通过
    # 如计算等方式才能获取的属性
    has_liked = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()

    class Meta:
        model = Tweet
        fields = (
            'id',
            'user',
            'created_at',
            'content',
            'comments_count',
            'likes_count',
            'has_liked',
        )

    def get_likes_count(self, obj):
        return obj.like_set.count()

    def get_comments_count(self, obj):
        # comment_set是django定义的反查机制
        return obj.comment_set.count()

    def get_has_liked(self, obj):
        return LikeService.has_liked(self.context["request"].user, obj)


class TweetSerializerWithDetail(TweetSerializer):
    user = UserSerializerForTweet()
    # Tweet是Comment的外键，django中允许tweet.comment_set来访问tweet对应
    # 的所有comments，所以在serializer中用source进行指定来源
    comments = CommentSerializer(source='comment_set', many=True)
    likes = LikeSerializer(source='like_set', many=True)

    class Meta:
        model = Tweet
        fields = (
            'id',
            'user',
            'comments',
            'created_at',
            'content',
            'likes',
            'likes_count',
            'comments_count',
            'has_liked',
        )


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
