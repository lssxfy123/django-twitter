from friendships.models import Friendship


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
    def has_followed(cls, from_user, to_user):
        return Friendship.objects.filter(
            from_user=from_user,
            to_user=to_user,
        ).exists()
