from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete
from accounts.listeners import profile_changed
from utils.listeners import invalidate_object_cache


class UserProfile(models.Model):
    # OneToOneField相当于unique，确保不会有多个UserProfile指向同一个User
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True)
    # django中还有一个ImageField，但是尽量不要用，会有很多的问题，用FileField可以起到
    # 同样的效果，因为最后我们都是以文件的形式存储起来，使用的是文件的url进行访问
    # 头像
    avatar = models.FileField(null=True)
    # 当一个user被创建之后，会创建一个user profile的object
    # 次数用户还来不及设置nickname等信息，因此null=True
    # 昵称
    nickname = models.CharField(null=True, max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '{} {}'.format(self.user, self.nickname)

# 定义一个 profile 的 property 方法，植入到 User 这个 model 里
# 这样当我们通过 user 的一个实例化对象访问 profile 的时候，即 user_instance.profile
# 就会在 UserProfile 中进行 get_or_create 来获得对应的 profile 的 object
# 这种写法实际上是一个利用 Python 的灵活性进行 hack 的方法，这样会方便我们通过 user 快速
# 访问到对应的 profile 信息。
# OneToOneField让user可以通过user.userprofile这种方式去访问profile信息，但这个需要每次
# 都去查询数据库


def get_profile(user):
    # 避免循环依赖
    from accounts.services import UserService

    # 在user对象上添加_cached_user_profile属性
    # 只有user对象不发生变化，_cached_user_profile就会存在
    if hasattr(user, '_cached_user_profile'):
        return getattr(user, '_cached_user_profile')
    
    # 不再直接访问数据库

    profile = UserService.get_profile_through_cache(user.id)
    # profile, _ = UserProfile.objects.get_or_create(user=user)
    # 使用 user 对象的属性进行缓存(cache)，避免多次调用同一个 user 的 profile 时
    # 重复的对数据库进行查询
    setattr(user, '_cached_user_profile', profile)
    return profile


# 给 User Model 增加了一个 profile 的 property 方法用于快捷访问
User.profile = property(get_profile)

# signal机制
pre_delete.connect(invalidate_object_cache, sender=User)
post_save.connect(invalidate_object_cache, sender=User)

pre_delete.connect(profile_changed, sender=UserProfile)
post_save.connect(profile_changed, sender=UserProfile)
