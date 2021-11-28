from django.db import models
from django.contrib.auth.models import User
from utils.time_helpers import utc_now
from likes.models import Like
from django.contrib.contenttypes.models import ContentType
from utils.listeners import invalidate_object_cache
from django.db.models.signals import post_save, pre_delete
from utils.memcached_helper import MemcachedHelper
from tweets.listeners import push_tweet_to_cache


# 在mysql数据库中存储的表为tweets_tweet
# tweets为app名称
class Tweet(models.Model):
    # 外键，记录tweet的发起者
    # help_text是django中记录注释的方式
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text='who posts this tweet',
    )
    content = models.CharField(max_length=255)
    # 创建Tweet对象时自动添加当前日期，并不再变化
    created_at = models.DateTimeField(auto_now_add=True)

    # 新增的 field 一定要设置 null=True，否则 default = 0，如果执行Migration
    # 会遍历整个表单去设置
    # 假如tweet表单中已经有1亿条数据了，相当于是用for循环遍历这一亿条数据去
    # 设置likes_count
    # 导致 Migration 过程非常慢，从而把整张表单锁死，这时如果用户创建新的tweet
    # 就无法成功
    # 设置null=True，执行完Migration后，新创建的tweet默认likes_count就是0了
    # 对于之前的既有数据，它还是null，这时就需要用脚本去回填likes_count了
    # 使用脚本时可以分批执行，并且可以选择在用户不活跃的时段执行
    likes_count = models.IntegerField(default=0, null=True)
    comments_count = models.IntegerField(default=0, null=True)

    class Meta:
        # 书写格式是将需要联合索引的字段组成一个二元组
        # 后面要加一个逗号，表示可能会有其它联合索引
        index_together = (('user', 'created_at'),)
        # 指定排序规则，user_id升序，created_at降序
        ordering = ('user', '-created_at')

    @property
    def hours_to_now(self):
        """
        返回tweet创建时间距离当前时间的小时数
        datetime.now()没有时区信息
        """
        return (utc_now() - self.created_at).seconds // 3600

    @property
    def like_set(self):
        """
        Tweet是Like的外键，django的反向查询机制，tweet.like_set就是查询tweet
        对应的所有like
        """
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(Tweet),
            object_id=self.id,
        ).order_by('-created_at')

    # 打印Tweet的对象时，显示的内容
    # user, created_at, content都是类的属性
    # 可以通过self来访问，也可以通过Tweet访问
    # 不要通过self设置类的属性，会在函数作用域内屏蔽掉它
    def __str__(self):
        # self.content = "lalala"
        return '{created_at} {user}: {content}'.format(
            created_at=self.created_at,
            user=self.user,
            content=self.content
        )

    @property
    def cached_user(self):
        return MemcachedHelper.get_object_through_cache(User, self.user_id)

    @property
    def timestamp(self):
        return int(self.created_at.timestamp() * 1000000)


post_save.connect(invalidate_object_cache, sender=Tweet)
pre_delete.connect(invalidate_object_cache, sender=Tweet)
post_save.connect(push_tweet_to_cache, sender=Tweet)
