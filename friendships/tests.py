from friendships.models import Friendship
from friendships.services import FriendshipService
from testing.testcases import TestCase


class FriendshipServiceTests(TestCase):

    def setUp(self):
        """
        django运行每个unittest时都会调用setUp函数，并且会创建一个transaction，数据库
        的事务，并且test结束后会回滚掉，所以每一个unittest的数据库都可以认为是干净的，
        不会受到其它unittest的影响，也没有所谓的历史数据。
        同理，对于cache来说，它也需要和数据库类似，每个unittest在都需要先清空cache，以
        避免历史数据的干扰
        """
        self.clear_cache()
        self.linghu = self.create_user('linghu')
        self.dongxie = self.create_user('dongxie')

    def test_following(self):
        user1 = self.create_user('user1')
        user2 = self.create_user('user2')

        for to_user in [user1, user2, self.dongxie]:
            Friendship.objects.create(from_user=self.linghu, to_user=to_user)

        # FriendshipService.invalidate_following_cache(self.linghu.id)

        user_id_set = FriendshipService.get_following_user_id_set(self.linghu.id)
        self.assertSetEqual(user_id_set, {user1.id, user2.id, self.dongxie.id})

        Friendship.objects.filter(
            from_user=self.linghu,
            to_user=self.dongxie).delete()
        # FriendshipService.invalidate_following_cache(self.linghu.id)
        user_id_set = FriendshipService\
            .get_following_user_id_set(self.linghu.id)
        self.assertSetEqual(user_id_set, {user1.id, user2.id})
