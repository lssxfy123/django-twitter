from django.contrib import admin
from likes.models import Like


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    """
    ModelAdmin是Django自带的管理员系统
    在浏览器访问admin/可以看到相应的界面
    date_hierarchy是按日期筛选
    list_display是在admin/页面显示的内容
    """
    date_hierarchy = 'created_at'
    list_display = (
        'user',
        'content_type',
        'object_id',
        'content_object',
        'created_at',
    )
    list_filter = ('content_type',)
