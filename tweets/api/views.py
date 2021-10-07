from rest_framework import viewsets
from rest_framework.views import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from tweets.models import Tweet
from tweets.api.serializers import (
    TweetSerializer,
    TweetSerializerForCreate,
    TweetSerializerWithDetail,
)
from newsfeeds.services import NewsFeedService
from utils.decorators import required_params
from utils.paginations import EndlessPagination
from tweets.services import TweetService


class TweetViewSet(viewsets.GenericViewSet,
                   viewsets.mixins.CreateModelMixin,
                   viewsets.mixins.ListModelMixin):
    # 如果调用get_queryset()会从queryset中查找
    queryset = Tweet.objects.all()
    serializer_class = TweetSerializerForCreate
    pagination_class = EndlessPagination

    def get_permissions(self):
        """
        获取权限许可：AlloAny()表示允许任何访问权限
        IsAuthenticated表示需要登陆
        """
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    """
    重载list方法，不列出所有tweets，必须指定user_id
    """
    @required_params(params=['user_id'])
    def list(self, request, *args, **kwargs):
        """
        查找指定user_id的Tweets，并且按created_at降序排列
        相当于sql
        select * from tweets_tweet where user_id = xxx order by created_at desc
        Tweet模型中user_id是一个外键，django会默认给它创建索引，但索引中不
        保证created_at是降序的，所以需要一个user_id和created_at的联合索引
        """
        # tweets = Tweet.objects
        # .filter(user_id=request.query_params['user_id'])\
        #     .order_by('-created_at')

        # 从Redis缓存中读取tweets
        user_id = request.query_params['user_id']
        cached_tweets = TweetService.get_cached_tweets(user_id)
        # 这里要使用self.paginator，因为paginate_cached_list是自定义的函数
        # ViewSet中没有相应的函数
        page = self.paginator.paginate_cached_list(cached_tweets, request)
        # 直接从数据库读取
        if page is None:
            # 这句查询会被翻译为
            # select * from twitter_tweets
            # where user_id = xxx
            # order by created_at desc
            # 这句 SQL 查询会用到 user 和 created_at 的联合索引
            # 单纯的 user 索引是不够的
            queryset = Tweet.objects.filter(user_id=user_id)\
                .order_by('-created_at')
            page = self.paginate_queryset(queryset)

        # many=True，表示序列化的是一个list of dict
        # 每个dict都是一条tweet的序列化数据
        serializer = TweetSerializer(
            page,
            context={'request': request},
            many=True,
        )
        # 查看get_paginated_response()的源码可以看出
        # 最终会调用EndlessPagination中的get_paginated_response()
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        tweet = self.get_object()
        return Response(TweetSerializerWithDetail(
            tweet,
            context={'request': request},
        ).data)

    def create(self, request, *args, **kwargs):
        serializer = TweetSerializerForCreate(
            data=request.data,
            context={'request': request}
        )

        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Please check input.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        # 会调用TweetCreateSerializer中的create()
        tweet = serializer.save()
        # 采用push模式，fanout写扩散
        # 当用户发tweet时，把相关的tweet写入到关注他的用户的newsfeed table中
        # 这类方法一般都是放到一个service类中，比较耗时
        NewsFeedService.fanout_to_followers(tweet)
        # 展示创建后的tweet时，用TweetSerialzier
        return Response(
            TweetSerializer(
                instance=tweet,
                context={'request': request},
            ).data,
            status=status.HTTP_201_CREATED)
