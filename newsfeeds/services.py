from newsfeeds.models import NewsFeed
from friendships.services import FriendshipService


class NewsFeedService:

    @classmethod
    def fanout_to_followers(cls, tweet):
        followers = FriendshipService.get_followers(tweet.user)

        # 下面这种写法是错误的，因为它会产生N次Queries操作，会非常耗时
        # 不允许for + query，工程代码中
        # 通常Web服务和DB不在同一台机器，甚至同一台机架上
        """
        for follower in followers:
            NewsFeed.objects.create(user=follower, tweet=tweet)
        """

        # 使用bulk_create，会把insert语句合成一条
        # 先生成所有的NewsFeed
        newsfeeds = [
            NewsFeed(user=follower, tweet=tweet)
            for follower in followers
        ]

        # 插入一条自身的NewsFeed，默认自己是自己的follower
        newsfeeds.append(NewsFeed(user=tweet.user, tweet=tweet))
        NewsFeed.objects.bulk_create(newsfeeds)


