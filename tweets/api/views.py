from rest_framework import viewsets
from rest_framework.views import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from tweets.models import Tweet
from tweets.api.serializers import TweetSerializer, TweetCreateSerializer


class TweetViewSet(viewsets.GenericViewSet,
                   viewsets.mixins.CreateModelMixin,
                   viewsets.mixins.ListModelMixin):
    # 如果调用get_queryset()会从queryset中查找
    queryset = Tweet.objects.all()
    serializer_class = TweetCreateSerializer

    def get_permissions(self):
        """
        获取权限许可：AlloAny()表示允许任何访问权限
        IsAuthenticated表示需要登陆
        """
        if self.action == 'list':
            return [AllowAny()]
        return [IsAuthenticated()]

    def list(self, request, *args, **kwargs):
        """
        重载list方法，不列出所有tweets，必须指定user_id
        """
        # query_params就是url中参数
        if 'user_id' not in request.query_params:
            return Response(
                'missing user_id',
                status=status.HTTP_400_BAD_REQUEST)

        """
        查找指定user_id的Tweets，并且按created_at降序排列
        相当于sql
        select * from tweets_tweet where user_id = xxx order by created_at desc
        Tweet模型中user_id是一个外键，django会默认给它创建索引，但索引中不
        保证created_at是降序的，所以需要一个user_id和created_at的联合索引
        """
        tweets = Tweet.objects.filter(user_id=request.query_params['user_id'])\
            .order_by('-created_at')
        # many=True，表示序列化的是一个list of dict
        # 每个dict都是一条tweet的序列化数据
        serializer = TweetSerializer(tweets, many=True)
        return Response({'tweets': serializer.data})

    def create(self, request, *args, **kwargs):
        serializer = TweetCreateSerializer(
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
        # 展示创建后的tweet时，用TweetSerialzier
        return Response(
            TweetSerializer(instance=tweet).data,
            status=status.HTTP_201_CREATED)
