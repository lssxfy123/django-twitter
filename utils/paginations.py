from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class FriendshipPagination(PageNumberPagination):
    # 默认的page size，也就是page没有在url参数里的时候
    page_size = 20

    # 默认的page_size_query_param是None，表示不允许客户端指定每一页的大小
    # 如果加上这个配置，表示客户端可以通过size=10来指定一个特定的大小用于不同的场景
    # 例如手机端和web端访问同一个API但是需要的size大小是不同的
    # 如果没有指定size，默认就是page_size
    page_size_query_param = 'size'

    # 允许客户端指定的最大page_size
    # 不允许客户端无限制的指定size的大小
    max_page_size = 20

    def get_paginated_response(self, data):
        return Response({
            'total_results': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'page_number': self.page.number,
            'has_next_page': self.page.has_next(),
            'results': data,
        })
