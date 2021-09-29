from django.db import models
from django.contrib.auth.models import User
from utils.time_helpers import utc_now
from likes.models import Like
from django.contrib.contenttypes.models import ContentType
from tweets.constants import TweetPhotoStatus, TWEET_PHOTO_STATUS_CHOICES
from accounts.services import UserService


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
        return UserService.get_user_through_cache(self.user_id)


class TweetPhoto(models.Model):
    # 图片在哪个Tweet下面
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)

    # 谁上传了这张图片，这个信息虽然可以从 tweet 中获取到，但是重复的记录在Photo 里可以在
    # 使用上带来很多遍历，比如某个人经常上传一些不合法的照片，那么这个人新上传的照片可以被标记
    # 为重点审查对象。或者我们需要封禁某个用户上传的所有照片的时候，就可以通过这个 model 快速
    # 进行筛选
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # 图片文件
    file = models.FileField()
    order = models.IntegerField(default=0)

    # 图片状态，用于审核等情况
    status = models.IntegerField(
        default=TweetPhotoStatus.PENDING,
        choices=TWEET_PHOTO_STATUS_CHOICES,
    )

    # 软删除(soft delete)标记，当一个照片被删除的时候，首先会被标记为已经被删除，在一定时间之后
    # 才会被真正的删除。这样做的目的是，如果在 tweet 被删除的时候马上执行真删除的通常会花费一定的
    # 时间，影响效率。可以用异步任务在后台慢慢做真删除。软删除也类似一个回收站机制
    has_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (
            ('user', 'created_at'),
            ('has_deleted', 'created_at'),
            ('status', 'created_at'),
            ('tweet', 'order'),
        )

    def __str__(self):
        return '{}: {}'.format(self.tweet_id, self.file)
