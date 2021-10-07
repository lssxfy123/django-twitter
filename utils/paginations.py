from rest_framework.pagination import BasePagination
from rest_framework.response import Response
from dateutil import parser
from django.conf import settings


class EndlessPagination(BasePagination):
    page_size = 20

    def __init__(self):
        super(EndlessPagination, self).__init__()
        self.has_next_page = False

    def to_html(self):
        pass

    def paginate_ordered_list(self, reverse_ordered_list, request):
        if 'created_at__gt' in request.query_params:
            created_at__gt = \
                parser.isoparse(request.query_params['created_at__gt'])
            objects = []
            for obj in reverse_ordered_list:
                if obj.created_at > created_at__gt:
                    objects.append(obj)
                else:
                    break
            self.has_next_page = False
            return objects

        index = 0
        if 'created_at__lt' in request.query_params:
            created_at__lt = \
                parser.isoparse(request.query_params['created_at__lt'])
            for index, obj in enumerate(reverse_ordered_list):
                """
                reverse_ordered_list是按created_at降序排列的
                如果某个obj.created_at小于指定的created_at__lt
                说明之后的objects都小于created_at__lt
                如果没有执行break，就会跳到下面的else中，说明没有满足条件的obj
                """
                if obj.created_at < created_at__lt:
                    break
            else:
                # 没有找到任何满足条件的objects，返回空数组
                # 注意这个else对应的是for，参加python的for else 语法
                reverse_ordered_list = []

        # 默认情况下
        self.has_next_page = len(reverse_ordered_list) > index + self.page_size
        return reverse_ordered_list[index: index + self.page_size]

    def paginate_cached_list(self, cached_list, request):
        paginated_list = self.paginate_ordered_list(cached_list, request)
        # 如果上翻页，paginated_list里是所有的最新的数据，直接返回
        if 'created_at__gt' in request.query_params:
            return paginated_list

        # 如果还有下一页，说明cached_list里的数据还没有取完，也直接返回
        if self.has_next_page:
            return paginated_list

        # 如果cached_list的长度不足redis缓存设置的最大限制，说明cached_list里已经
        # 是所有数据了，数据库中也没有更多数据，否则会添加到cached_list里直到满足限制
        # 长度
        if len(cached_list) < settings.REDIS_LIST_LENGTH_LIMIT:
            return paginated_list

        # 如果进入这里，说明可能存在在数据库里没有 load 在 cache 里的数据，
        # 需要直接去数据库查询
        return None

    def paginate_queryset(self, queryset, request, view=None):

        if 'created_at__gt' in request.query_params:
            # created_at__gt 用于下拉刷新的时候加载最新的内容进来
            # 为了简便起见，下拉刷新不做翻页机制，直接加载所有更新的数据
            # 因为如果数据很久没有更新的话，不会采用下拉刷新的方式进行更新，而是重新加载最新的数据
            created_at__gt = request.query_params['created_at__gt']
            queryset = queryset.filter(created_at__gt=created_at__gt)
            self.has_next_page = False
            return queryset.order_by('-created_at')

        if 'created_at__lt' in request.query_params:
            # created_at__lt 用于向上滚屏（往下翻页）的时候加载下一页的数据
            # 寻找 created_at < created_at__lt 的 objects 里按照 created_at 倒序的前
            # page_size + 1 个 objects
            # 比如目前的 created_at 列表是 [10, 9, 8, 7 .. 1] 如果 created_at__lt=10
            # page_size = 2 则应该返回 [9, 8, 7]，多返回一个 object 的原因是为了判断是否
            # 还有下一页从而减少一次空加载。
            created_at__lt = request.query_params['created_at__lt']
            queryset = queryset.filter(created_at__lt=created_at__lt)

        # 默认情况下
        queryset = queryset.order_by('-created_at')[:self.page_size + 1]
        self.has_next_page = len(queryset) > self.page_size
        return queryset[:self.page_size]

    def get_paginated_response(self, data):
        return Response({
            'has_next_page': self.has_next_page,
            'results': data,
        })
