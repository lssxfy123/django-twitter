from celery import shared_task
from friendships.services import FriendshipService
from newsfeeds.models import NewsFeed
from tweets.models import Tweet
from utils.time_constants import ONE_HOUR
from newsfeeds.constants import FANOUT_BATCH_SIZE


@shared_task(routing_key='newsfeeds', time_limit=ONE_HOUR)
def fanout_newsfeeds_batch_task(tweet_id, follower_ids):
    # import写在里面避免循环依赖
    from newsfeeds.services import NewsFeedService

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
        NewsFeed(user_id=follower_id, tweet_id=tweet_id)
        for follower_id in follower_ids
    ]

    NewsFeed.objects.bulk_create(newsfeeds)

    # bulk_create不会触发post_save的信号，所以需要手动触发
    for newsfeed in newsfeeds:
        NewsFeedService.push_newsfeed_to_cache(newsfeed)

    # celery async可以返回值，有助于调试
    return '{} newsfeeds created'.format(len(newsfeeds))


@shared_task(routing_key='default', time_limit=ONE_HOUR)
def fanout_newsfeeds_main_task(tweet_id, tweet_user_id):
    # 将推给自己的 Newsfeed 率先创建，确保自己能最快看到
    # 产品层面的考虑，自己发帖子，刷新后自己的新鲜事列表就能看见这个帖子
    NewsFeed.objects.create(user_id=tweet_user_id, tweet_id=tweet_id)

    # 获得所有的follower ids，按照batch size拆分开
    follower_ids = FriendshipService.get_follower_ids(tweet_user_id)
    index = 0
    while index < len(follower_ids):
        batch_ids = follower_ids[index: index + FANOUT_BATCH_SIZE]
        fanout_newsfeeds_batch_task.delay(tweet_id, batch_ids)
        index += FANOUT_BATCH_SIZE

    return '{} newsfeeds going to fanout, {} batches created.'.format(
        len(follower_ids),
        (len(follower_ids) - 1) // FANOUT_BATCH_SIZE + 1,
    )
