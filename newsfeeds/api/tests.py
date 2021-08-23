from testing.testcases import TestCase
from rest_framework.test import APIClient
from friendships.models import Friendship
from newsfeeds.models import NewsFeed
from rest_framework.views import status

NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEETS_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/{}/follow/'


class NewsFeedApiTest(TestCase):
    def setUp(self):
        self.linghu = self.create_user("linghu")
        self.linghu_client = APIClient()
        self.linghu_client.force_authenticate(self.linghu)

        self.dongxie = self.create_user("dongxie")
        self.dongxie_client = APIClient()
        self.dongxie_client.force_authenticate(self.dongxie)

    def test_list(self):
        # 需要登录
        response = self.anonymous_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 不能用post
        response = self.linghu_client.post(NEWSFEEDS_URL)
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

        # 刚开始啥也没有
        response = self.linghu_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["newsfeeds"]), 0)

        # 自己发的信息会出现在自己的新鲜事列表中
        self.linghu_client.post(POST_TWEETS_URL, {"content": "Hello World"})
        response = self.linghu_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data["newsfeeds"]), 1)

        # 关注别人后，可以看别人发的tweet
        self.linghu_client.post(FOLLOW_URL.format(self.dongxie.id))
        response = self.dongxie_client.post(POST_TWEETS_URL, {
            "content": "Hello Twitter"
        })
        post_tweet_id = response.data["id"]
        response = self.linghu_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data["newsfeeds"]), 2)
        self.assertEqual(response.data["newsfeeds"][0]["tweet"]["id"],
                         post_tweet_id)
