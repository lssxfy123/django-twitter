from testing.testcases import TestCase
from rest_framework.test import APIClient
from rest_framework.views import status
from tweets.models import Tweet


# 注意尾部要加上'/'，否则会报301 redirect
TWEET_LIST_API = '/api/tweets/'
TWEET_CREATE_API = '/api/tweets/'
TWEET_RETRIEVE_API = '/api/tweets/{}/'


class TweetApiTests(TestCase):

    def setUp(self):

        self.user1 = self.create_user('user1', 'user1@jiuzhang.com')
        self.tweets1 = [self.create_tweet(self.user1) for _ in range(3)]

        self.user1_client = APIClient()
        # 客户端强制用user1的信息去访问，其它用户无法通过它访问api
        self.user1_client.force_authenticate(self.user1)

        self.user2 = self.create_user('user2', 'user2@jiuzhang.com')
        self.tweet2 = [self.create_tweet(self.user2) for _ in range(2)]

    def test_list_api(self):
        # 必须带有user_id
        response = self.anonymous_client.get(TWEET_LIST_API)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 正常的requeset
        response = self.anonymous_client.get(TWEET_LIST_API, {
            'user_id': self.user1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['tweets']), 3)

        response = self.anonymous_client.get(TWEET_LIST_API, {
            'user_id': self.user2.id})
        self.assertEqual(len(response.data['tweets']), 2)

        # 检测返回的tweets是否是按照创建时间的倒序来排列的
        # Tweet模型中id是PrimaryKey，是自增数字，user是外键
        self.assertEqual(response.data['tweets'][0]['id'], self.tweet2[1].id)
        self.assertEqual(response.data['tweets'][1]['id'], self.tweet2[0].id)

    def test_create_api(self):
        # 发tweet必须登陆
        response = self.anonymous_client.post(TWEET_CREATE_API)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 必须带content
        response = self.user1_client.post(TWEET_CREATE_API)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # content不能太短
        response = self.user1_client.post(TWEET_CREATE_API, {'content': '1'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # content不能太长
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': '0' * 141})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 正常发tweet
        tweets_count = Tweet.objects.count()
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': 'Hello World, this is my first tweet!'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # user1_client强制使用user1的信息验证
        self.assertEqual(response.data['user']['id'], self.user1.id)
        self.assertEqual(Tweet.objects.count(), tweets_count + 1)

    def test_retrieve_api(self):
        url = TWEET_RETRIEVE_API.format(-1)
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # 获取某个 tweet 的时候会一起把 comments 也拿下
        tweet = self.create_tweet(self.user1)
        url = TWEET_RETRIEVE_API.format(tweet.id)
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["comments"]), 0)

        self.create_comment(self.user2, tweet, 'holly s***')
        self.create_comment(self.user1, tweet, 'hmm...')
        self.create_comment(self.user1, self.create_tweet(self.user2), '....')
        response = self.anonymous_client.get(url)
        self.assertEqual(len(response.data['comments']), 2)
