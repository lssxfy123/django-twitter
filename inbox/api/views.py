from rest_framework import viewsets, status
from inbox.api.serializers import NotificationSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from notifications.models import Notification


class NotificationViewSet(
    viewsets.GenericViewSet,
    viewsets.mixins.ListModelMixin,  # 使用默认的list方法
):
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated,)
    # 主要是viewsets.mixins.ListModelMixin中的list方法会用到
    # 如果不写，tests.py中test_list最后两个测试通不过，没有进行筛选unread
    filterset_fields = ('unread',)

    def get_queryset(self):
        """
        第一种写法：可以查看Notification模型的源代码
        User是Notification的ForeignKey，定义了related_name='notification'
        """
        # return self.request.user.notifications.all(
        # 所有接收通知的人为self.request.user的通知
        return Notification.objects.filter(recipient=self.request.user)

    @action(methods=['GET'], detail=False, url_path='unread-count')
    def unread_count(self, request):
        """
        指定了url_path，如果不指定则访问函数的url为/api/notifications/unread_count
        这不太符合url的规范，指定了url_path后，url为/api/notifications/unread=count
        """
        count = self.get_queryset().filter(unread=True).count()
        return Response({'unread_count': count}, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False, url_path='mark-all-as-read')
    def mark_all_as_read(self, request):
        """
        标记所有为已读
        """
        # Notification模型中定义了index_together=('recipient', 'unread')
        # 下面这条语句其实是两个filter,
        # filter(recipient=self.request.user).filter(unread=True)
        # 可以用到联合索引，以后自己写Model时，也要注意这些细节
        updated_count = self.get_queryset()\
            .filter(unread=True).update(unread=False)
        return Response({
            "marked_count": updated_count
        },
            status=status.HTTP_200_OK)
