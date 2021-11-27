"""
Deprecated
use newsfeeds.hbase_models.HBaseNewsFeed instead
"""
from django.db import models
from django.contrib.auth.models import User
from tweets.models import Tweet
from utils.memcached_helper import MemcachedHelper
from django.db.models.signals import post_save
from newsfeeds.listeners import push_newsfeed_to_cache


class NewsFeed(models.Model):
    # 这里的user不是存储谁发了这条tweet，而是谁可以看到这条tweet
    # 某个用户登陆后，就会看到他能看到的新鲜事流
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (('user', 'created_at'), )
        # 相同的user和tweet只能在数据库存储一条记录
        unique_together = (('user', 'tweet'), )
        ordering = ('user', '-created_at')

    def __str__(self):
        return '{} inbox of {}: {}'.format(
            self.created_at,
            self.user,
            self.tweet)

    @property
    def cached_tweet(self):
        return MemcachedHelper.get_object_through_cache(Tweet, self.tweet_id)


post_save.connect(push_newsfeed_to_cache, sender=NewsFeed)
