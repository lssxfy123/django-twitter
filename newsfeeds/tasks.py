from celery import shared_task
from friendships.services import FriendshipService
from newsfeeds.models import NewsFeed
from utils.time_constants import ONE_HOUR
from newsfeeds.constants import FANOUT_BATCH_SIZE


@shared_task(routing_key='newsfeeds', time_limit=ONE_HOUR)
def fanout_newsfeeds_batch_task(tweet_id, created_at, follower_ids):
    """
    created_at是Tweet的时间戳，而newsfeeds的时间戳其实应该是Tweet的时间戳
    例如昨天发了一条Tweet，但由于粉丝非常多，可能今天才全部fanout完毕，那么NewsFeed
    显示的时间肯定不能是今天，而应该是昨天Tweet发表的时间
    """
    # import写在里面避免循环依赖
    from newsfeeds.services import NewsFeedService

    # 下面这种写法是错误的，因为它会产生N次Queries操作，会非常耗时
    # 不允许for + query，工程代码中
    # 通常Web服务和DB不在同一台机器，甚至同一台机架上
    """
    for follower in followers:
        NewsFeed.objects.create(user=follower, tweet=tweet)
    """
    batch_params = [
        {'user_id': follower_id, 'created_at': created_at, 'tweet_id': tweet_id}
        for follower_id in follower_ids
    ]

    newsfeeds = NewsFeedService.batch_create(batch_params)

    # celery async可以返回值，有助于调试
    return '{} newsfeeds created'.format(len(newsfeeds))


@shared_task(routing_key='default', time_limit=ONE_HOUR)
def fanout_newsfeeds_main_task(tweet_id, created_at, tweet_user_id):
    from newsfeeds.services import NewsFeedService

    # 将推给自己的 Newsfeed 率先创建，确保自己能最快看到
    # 产品层面的考虑，自己发帖子，刷新后自己的新鲜事列表就能看见这个帖子
    NewsFeedService.create(
        user_id=tweet_user_id, tweet_id=tweet_id, created_at=created_at)

    # 获得所有的follower ids，按照batch size拆分开
    follower_ids = FriendshipService.get_follower_ids(tweet_user_id)
    index = 0
    while index < len(follower_ids):
        batch_ids = follower_ids[index: index + FANOUT_BATCH_SIZE]
        fanout_newsfeeds_batch_task.delay(tweet_id, created_at, batch_ids)
        index += FANOUT_BATCH_SIZE

    return '{} newsfeeds going to fanout, {} batches created.'.format(
        len(follower_ids),
        (len(follower_ids) - 1) // FANOUT_BATCH_SIZE + 1,
    )
