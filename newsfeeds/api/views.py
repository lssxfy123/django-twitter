from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from newsfeeds.models import NewsFeed
from newsfeeds.api.serializers import NewsFeedSerializer
from utils.paginations import EndlessPagination
from newsfeeds.services import NewsFeedService


class NewsFeedViewSet(viewsets.GenericViewSet):
    # 新鲜事只能当前登录用户查看，所以要验证登录
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    def get_queryset(self):
        """
        自定义 queryset，因为 newsfeed 的查看是有权限的
        只能看 user=当前登录用户的 newsfeed
        也可以是 self.request.user.newsfeed_set.all()
        但是一般最好还是按照 NewsFeed.objects.filter 的方式写，更清晰直观
        """
        return NewsFeed.objects.filter(user=self.request.user)

    # NewsFeedViesSet不需要提供增删改查，只需要提供一个list就行了
    def list(self, request):
        # 不像之前的Serializer都是提供request.data，这次序列化的数据不是
        # 从request中传递的，而是需要从数据库中查找
        newsfeeds = NewsFeedService.get_cached_newsfeeds(request.user.id)
        page = self.paginate_queryset(newsfeeds)
        serializer = NewsFeedSerializer(
            page,
            context={'request': request},
            many=True,
        )
        return self.get_paginated_response(serializer.data)
