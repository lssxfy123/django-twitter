from django.db import models
from tweets.models import Tweet
from django.contrib.auth.models import User
from likes.models import Like
from django.contrib.contenttypes.models import ContentType
from utils.memchached_helper import MemcachedHelper


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)
    content = models.CharField(max_length=140)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # 获取某个tweet下所有的评论
        index_together = (('tweet', 'created_at'),)

    @property
    def like_set(self):
        """
        Comment是Like的外键，django的反向查询机制，comment.like_set就是查询comment
        对应的所有like
        """
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(Comment),
            object_id=self.id,
        ).order_by('-created_at')

    def __str__(self):
        return '{} - {} says {} at tweet {}'.format(
            self.created_at,
            self.user,  # 查看User的源代码，User的__str__返回的是username
            self.content,
            self.tweet_id,  # 这里要指明tweet_id，如果直接用tweet，会调用Tweet的__str__
        )

    @property
    def cached_user(self):
        return MemcachedHelper.get_object_through_cache(User, self.user_id)
