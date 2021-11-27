from django.contrib.auth.models import User
from django_hbase import models
from tweets.models import Tweet
from utils.memcached_helper import MemcachedHelper


class NewsFeed(models.HBaseModel):
    # 这里的user不是存储谁发了这条tweet，而是谁可以看到这条tweet
    # 某个用户登陆后，就会看到他能看到的新鲜事流
    # user_id带有时序性，越大的越靠后，需要进行reverse，避免hot，导致数据分布不均匀
    user_id = models.IntegerField(reverse=True)
    # 时间戳带有时序性，但不能进行reverse，因为需要做范围查询
    created_at = models.TimestampField()
    tweet_id = models.IntegerField(column_family='cf')

    class Meta:
        table_name = 'twitter_newsfeeds'
        row_key = ('user_id', 'created_at')

    def __str__(self):
        return '{} inbox of {}: {}'.format(
            self.created_at,
            self.user_id,
            self.tweet_id)

    @property
    def cached_tweet(self):
        return MemcachedHelper.get_object_through_cache(Tweet, self.tweet_id)

    @property
    def cached_user(self):
        return MemcachedHelper.get_object_through_cache(User, self.user_id)
