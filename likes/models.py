from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Like(models.Model):
    # 谁点的赞
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # tweet_id or comment_id
    object_id = models.PositiveBigIntegerField()

    # 通用的外键
    # https://docs.djangoproject.com/en/3.1/ref/contrib/contenttypes/#generic-relations
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
    )

    # content_object不会记录到实际的数据库表单中
    # 它是一个快捷的访问方式
    content_object = GenericForeignKey('content_type', 'object_id')

    # 什么时间点赞
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # unique_together会创建一个unique index，唯一索引
        # 确保每个用户对每条comment或tweet只能点赞一次
        # 要在数据库的层面去保证，如果在api层面去保证，由于web的高并发特性，无法完全
        # 确保一定只点赞一次
        # 这个索引同时还可以具备查询某个 user 点赞 了哪些不同的 objects 的功能
        # 因此如果 unique together 改成 <content_type, object_id, user>
        # 就没有这样的效果了
        unique_together = (('user', 'content_type', 'object_id'),)

        index_together = (
            # 查询某个被like的对象所有的likes
            ('content_type', 'object_id', 'created_at'),
            # 查询某个用户点赞的对象按时间排序
            ('user', 'content_type', 'created_at'),
        )

    def __str__(self):
        return '{} - {} liked {} {}'.format(
            self.created_at,
            self.user,
            self.content_type,
            self.object_id,
        )
