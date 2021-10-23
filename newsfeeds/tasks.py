from celery import shared_task
from friendships.services import FriendshipService
from newsfeeds.models import NewsFeed
from tweets.models import Tweet
from utils.time_constants import ONE_HOUR


@shared_task(time_limit=ONE_HOUR)
def fanout_newsfeeds_task(tweet_id):
    # import写在里面避免循环依赖
    from newsfeeds.services import NewsFeedService

    tweet = Tweet.objects.filter(id=tweet_id).first()

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

    # bulk_create不会触发post_save的信号，所以需要手动触发
    for newsfeed in newsfeeds:
        NewsFeedService.push_newsfeed_to_cache(newsfeed)
