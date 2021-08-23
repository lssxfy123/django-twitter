from django.test import TestCase as DjangoTestCase
from django.contrib.auth.models import User
from tweets.models import Tweet
from rest_framework.test import APIClient


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