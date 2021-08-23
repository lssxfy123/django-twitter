from django.db import models
from django.contrib.auth.models import User


class Friendship(models.Model):
    # 关注者
    from_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='following_friendship_set',
    )

    # 被关注者
    to_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='follower_friendship_set',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (
            # 获取我作为关注者相关的friendship，按照关注时间排序
            ('from_user_id', 'created_at'),
            # 获取我作为被关注者相关的friendship，按照关注时间排序
            ('to_user_id', 'created_at'),
        )

        # 关注者和被关注者需要满足唯一约束
        # 关注者和被关注者应当是唯一的，数据库不能存完全相同的两条friendship
        unique_together = (('from_user_id', 'to_user_id'),)

    def __str__(self):
        return '{} followed {}'.format(self.from_user_id, self.to_user_id)
