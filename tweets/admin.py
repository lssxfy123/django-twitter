from django.contrib import admin
from tweets.models import Tweet, TweetPhoto


@admin.register(Tweet)
class TweetAdmin(admin.ModelAdmin):
    """
    ModelAdmin是Django自带的管理员系统
    在浏览器访问admin/可以看到相应的界面
    date_hierarchy是按日期筛选
    list_display是在admin/页面显示的内容
    """
    date_hierarchy = 'created_at'
    list_display = (
        'created_at',
        'user',
        'content',
    )


@admin.register(TweetPhoto)
class TweetPhotoAdmin(admin.ModelAdmin):
    list_display = (
        'tweet',
        'user',
        'file',
        'status',
        'has_deleted',
        'created_at',
    )
    list_filter = ('status', 'has_deleted')
    date_hierarchy = 'created_at'
