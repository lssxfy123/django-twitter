from django.test import TestCase as DjangoTestCase
from django.contrib.auth.models import User
from tweets.models import Tweet


class TestCase(DjangoTestCase):
    """
    将测试中使用的一些公共方法抽取到一个公共类中
    """
    def create_user(self, username, email, password=None):
        if password is None:
            password = "generic password"
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