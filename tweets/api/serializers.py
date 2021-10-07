from rest_framework import serializers
from tweets.models import Tweet
from comments.api.serializers import CommentSerializer
from accounts.api.serializers import UserSerializerForTweet
from likes.services import LikeService
from likes.api.serializers import LikeSerializer
from tweets.constants import TWEET_PHOTOS_UPLOAD_LIMIT
from rest_framework.exceptions import ValidationError
from tweets.services import TweetService
from utils.redis_helper import RedisHelper


class TweetSerializer(serializers.ModelSerializer):
    # 使用缓存中的user object
    user = UserSerializerForTweet(source='cached_user')
    # 是否被赞， 需要实现一个get_has_liked()方法
    # SerializerMethodField()不是原本就存在的，需要通过
    # 如计算等方式才能获取的属性
    has_liked = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    photo_urls = serializers.SerializerMethodField()

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
            'photo_urls',
        )

    def get_likes_count(self, obj):
        # N + Queries
        # N如果是db queries-->不可接受
        # N如果是redis/memached queries-->可以接受
        return RedisHelper.get_count(obj, 'likes_count')

    def get_comments_count(self, obj):
        # comment_set是django定义的反查机制
        return RedisHelper.get_count(obj, 'comments_count')

    def get_has_liked(self, obj):
        return LikeService.has_liked(self.context["request"].user, obj)

    def get_photo_urls(self, obj):
        photo_urls = []
        for photo in obj.tweetphoto_set.all().order_by('order'):
            photo_urls.append(photo.file.url)
        return photo_urls


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
            'photo_urls',
        )


class TweetSerializerForCreate(serializers.ModelSerializer):
    content = serializers.CharField(min_length=6, max_length=140)
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=True,  # 允许'files'中的值为空[]
        required=False,  # data中'files'键是否需要存在
    )

    class Meta:
        model = Tweet
        # 这里不能放入user_id, email等信息
        # 因为Tweet创建肯定是当前登陆用户创建的
        fields = ('content', 'files')

    def validate(self, data):
        if len(data.get('files', [])) > TWEET_PHOTOS_UPLOAD_LIMIT:
            raise ValidationError({
                'message':
                    'You can upload {} photos'
                    ' at most'.format(TWEET_PHOTOS_UPLOAD_LIMIT)
            })
        return data

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
        if validated_data.get('files'):
            TweetService.create_photos_from_files(
                tweet,
                validated_data['files'],
            )
        return tweet
