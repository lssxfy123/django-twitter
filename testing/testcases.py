from django.test import TestCase as DjangoTestCase
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from tweets.models import Tweet
from comments.models import Comment
from likes.models import Like
from rest_framework.test import APIClient
from newsfeeds.services import NewsFeedService
from django.core.cache import caches
from utils.redis_client import RedisClient
from django_hbase.models import HBaseModel
from friendships.services import FriendshipService
from gatekeeper.models import GateKeeper


class TestCase(DjangoTestCase):
    hbase_tables_created = False

    # 针对HBase的测试，需要自己重载setUp和tearDown，每个test调用时会先调用
    # setUp，test结束时会调用tearDown
    # 因为django不会自动创建HBase的表单并在测试结束后销毁掉它
    # 如果HBase的Test自身还有setUp，就需要通过super()调用基类的setUp
    def setUp(self):
        self.clear_cache()
        try:
            self.hbase_tables_created = True
            for hbase_model_class in HBaseModel.__subclasses__():
                hbase_model_class.create_table()
        except Exception:
            self.tearDown()
            # 抛出异常，以便于查找
            raise

    def tearDown(self):
        if not self.hbase_tables_created:
            return
        for hbase_model_class in HBaseModel.__subclasses__():
            hbase_model_class.drop_table()

    """
    将测试中使用的一些公共方法抽取到一个公共类中
    """

    def clear_cache(self):
        """
        将放大cache中的key全部清除掉
        """
        caches['testing'].clear()
        RedisClient.clear()
        GateKeeper.turn_on('switch_friendship_to_hbase')
        GateKeeper.turn_on('switch_newsfeed_to_hbase')

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

    def create_friendship(self, from_user, to_user):
        return FriendshipService.follow(
            from_user_id=from_user.id, to_user_id=to_user.id)

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
        if GateKeeper.is_switch_on('switch_newsfeed_to_hbase'):
            created_at = tweet.timestamp
        else:
            created_at = tweet.created_at
        return NewsFeedService.create(
            user_id=user.id, tweet_id=tweet.id, created_at=created_at)
