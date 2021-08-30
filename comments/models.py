from django.db import models
from tweets.models import Tweet
from django.contrib.auth.models import User


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)
    content = models.CharField(max_length=140)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # 获取某个tweet下所有的评论
        index_together = (('tweet', 'created_at'),)

    def __str__(self):
        return '{} - {} says {} at tweet {}'.format(
            self.created_at,
            self.user,  # 查看User的源代码，User的__str__返回的是username
            self.content,
            self.tweet_id,  # 这里要指明tweet_id，如果直接用tweet，会调用Tweet的__str__
        )
