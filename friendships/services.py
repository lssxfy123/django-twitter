from friendships.models import Friendship
from django.conf import settings
from django.core.cache import caches
from twitter.cache import FOLLOWINGS_PATTERN


cache = caches['testing'] if settings.TESTING else caches['default']


class FriendshipService:

    @classmethod
    def get_followers(cls, user):
        """
        获取所有关注user的用户
        """

        # 下面这种写法有问题，导致了N + 1次Query，如果数据库很大，会非常耗时
        # filter方法会执行一次Query
        # Friendship.objects.filter()产生的queryset是懒惰加载的，这句代码执行后
        # 不会立刻去访问数据库，所以必须进行for循环操作，才会访问数据库
        # for循环迭代friendships，才会从friendship数据库中加载to_user=user的所有
        # friendships
        # for循环每个friendship取from_user又会耗费N次Queries
        # friendship.from_user会去user table数据库根据from_user_id去查from_user
        # 因此会产生N次Queries
        """
        friendships = Friendship.objects.filter(to_user=user)
        return [friendship.from_user for friendship in friendships]
        """

        # 如果我们知道自己一定会用到某些字段，就可以进行预先加载
        # 下面这种预先加载的方式也有问题，虽然只执行了一次Query，
        # 但其会产生JOIN操作，会把friendship table
        # 和user table在from_user这个字段上join，而JOIN操作忌讳在大量用户的web服务
        # 会非常耗时
        """
        friendships = Friendship.objects.filter(to_user=user)\
            .select_related('from_user')
        return [friendship.from_user for friendship in friendships]
        """

        # 正确的写法一，两次Query，第二次使用了IN Query操作
        """
        friendships = Friendship.objects.filter(to_user=user)
        # from_user_id是存在于friendship table中的，访问它时不会再进行query查询
        follower_ids = [friendship.from_user_id for friendship in friendships]
        # django中的id__in表示参数id in follower_ids
        followers = User.objects.filter(id__in=follower_ids)
        """

        # 正确的写法二，使用了prefetch_related，也是IN Query操作
        # 和上面的写法一是一样的，也有两次Query
        friendships = Friendship.objects.filter(
            to_user=user,
        ).prefetch_related('from_user')
        # friendship.from_user就不会再进行Query查询
        return [friendship.from_user for friendship in friendships]

    @classmethod
    def get_follower_ids(cls, to_user_id):
        friendships = Friendship.objects.filter(to_user_id=to_user_id)
        # 不能产生N+1 Queries，因为from_user_id就在Friendship表中
        # 一次query就会把所有符合条件的from_user_id都查出来
        return [friendship.from_user_id for friendship in friendships]

    @classmethod
    def get_following_user_id_set(cls, from_user_id):
        # Memcached如果内存不够多，导致key的访问速度变慢，会删除掉部分不常用的key
        # 常用的是LRU缓存机制
        key = FOLLOWINGS_PATTERN.format(user_id=from_user_id)
        user_id_set = cache.get(key)
        # memcached中存在
        if user_id_set is not None:
            return user_id_set

        # 获取from_user_id所关注的所有人
        # 一般不会缓存关注to_user_id的所有人，因为对于明星用户来说，关注他的所有人
        # 会非常多，比如有1亿粉丝的用户，而且它会变化的频率会非常快，这样会频繁导致
        # 缓存刷新
        friendships = Friendship.objects.filter(from_user_id=from_user_id)
        # 存储一个set，是方便查找，查找时间复杂度为O(1)
        # 如果存储list，则是O(n)
        user_id_set = set([friendship.to_user_id for friendship in friendships])
        cache.set(key, user_id_set)
        return user_id_set

    @classmethod
    def invalidate_following_cache(cls, from_user_id):
        """
        手动废止掉某个缓存中的key
        如果不手动废止，key会根据settings中配置的或set时设置的TIMEOUT来自动废止
        """
        key = FOLLOWINGS_PATTERN.format(user_id=from_user_id)
        cache.delete(key)
