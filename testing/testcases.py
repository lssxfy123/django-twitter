from django.test import TestCase as DjangoTestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from tweets.models import Tweet
from comments.models import Comment
from likes.models import Like
from rest_framework.test import APIClient
from newsfeeds.models import NewsFeed


class TestCase(DjangoTestCase):
    """
    将测试中使用的一些公共方法抽取到一个公共类中
    """

    # 未登陆的匿名客户端
    # 添加装饰器property可以把anonymous_client()方法当属性使用
    @property
    def anonymous_client(self):
        # 下面这种写法是一种比较好的方式，设置一个内部的缓存
        if hasattr(self, "_anonymous_client"):
            return self._anonymous_client
        self._anonymous_client = APIClient()
        return self._anonymous_client

    def create_user(self, username, email=None, password=None):
        if password is None:
            password = "generic password"
        if email is None:
            email = '{}@jiuzhang.com'.format(username)
        # 不能使用User.objects.create()
        # 因为password需要被加密，username和email需要normalize处理
        return User.objects.create_user(
            username=username,
            email=email,
            password=password)

    def create_tweet(self, user, content=None):
        if content is None:
            content = 'default tweet content'

        return Tweet.objects.create(user=user, content=content)

    def create_comment(self, user, tweet, content=None):
        if content is None:
            content = 'default comment content'
        return Comment.objects.create(user=user, tweet=tweet, content=content)

    def create_like(self, user, target):
        # target is comment or tweet
        instance, _ = Like.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(target.__class__),
            object_id=target.id,
            user=user,
        )
        return instance

    def create_user_and_client(self, *args, **kwargs):
        user = self.create_user(*args, **kwargs)
        client = APIClient()
        client.force_authenticate(user)
        return user, client

    def create_newsfeed(self, user, tweet):
        return NewsFeed.objects.create(user=user, tweet=tweet)
