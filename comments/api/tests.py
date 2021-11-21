from testing.testcases import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from comments.models import Comment

COMMENT_URL = '/api/comments/'
TWEET_LIST_API = '/api/tweets/'
TWEET_DETAIL_API = '/api/tweets/{}/'
NEWSFEED_LIST_API = '/api/newsfeeds/'


class CommentApiTests(TestCase):

    def setUp(self):
        super().setUp()
        self.linghu = self.create_user('linghu')
        self.linghu_client = APIClient()
        self.linghu_client.force_authenticate(self.linghu)

        self.dongxie = self.create_user('dongxie')
        self.dongxie_client = APIClient()
        self.dongxie_client.force_authenticate(self.dongxie)

        self.tweet = self.create_tweet(self.linghu)

    def test_create(self):
        # 匿名不可以创建comment
        response = self.anonymous_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 没有参数
        response = self.linghu_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 只带 tweet_id 不行
        response = self.linghu_client.post(COMMENT_URL,
                                           {'tweet_id': self.tweet.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 只带 content 不行
        response = self.linghu_client.post(COMMENT_URL, {'content': '1'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # content 太长不行
        response = self.linghu_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1' * 141,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual('content' in response.data['errors'], True)

        # tweet_id 和 content 都带才行
        response = self.linghu_client.post(COMMENT_URL, {
            'tweet_id': self.tweet.id,
            'content': '1',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['id'], self.linghu.id)
        self.assertEqual(response.data['tweet_id'], self.tweet.id)
        self.assertEqual(response.data['content'], '1')

    def test_destroy(self):
        comment = self.create_comment(self.linghu, self.tweet)
        url = '{}{}/'.format(COMMENT_URL, comment.id)

        # 匿名不可以删除
        response = self.anonymous_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 非本人不能删除
        response = self.dongxie_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 本人可以删除
        count = Comment.objects.count()
        response = self.linghu_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Comment.objects.count(), count - 1)

    def test_update(self):
        # 先创建一个comment
        comment = self.create_comment(self.linghu, self.tweet, "original")
        another_tweet = self.create_tweet(self.dongxie)
        url = '{}{}/'.format(COMMENT_URL, comment.id)

        # 使用put
        # 匿名不能更新
        response = self.anonymous_client.put(url, {'content': 'new'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 非本人不能更新
        response = self.dongxie_client.put(url, {'content': 'new'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # 刷新comment对象，验证其并未更新成功
        # update时需要使用这个方法，因为put是更新了数据库，
        # comment对象本身并未变化，所以需要从数据库取数据刷新它
        comment.refresh_from_db()
        self.assertNotEqual(comment.content, "new")

        # 不能更新除content的其它内容
        # 静默处理，只更新内容
        before_updated_at = comment.updated_at
        before_created_at = comment.created_at
        now = timezone.now()

        response = self.linghu_client.put(url, {
            "content": 'new',
            'user_id': self.dongxie.id,
            "tweet_id": another_tweet.id,
            'created_at': now,
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertEqual(comment.content, 'new')
        self.assertEqual(comment.user, self.linghu)
        self.assertEqual(comment.tweet, self.tweet)
        self.assertEqual(comment.created_at, before_created_at)
        self.assertNotEqual(comment.created_at, now)
        # comment对象的updated_at会自动发生改变
        self.assertNotEqual(comment.updated_at, before_updated_at)

    def test_list(self):
        # 必须带 tweet_id
        response = self.anonymous_client.get(COMMENT_URL)
        self.assertEqual(response.status_code, 400)

        # 带了 tweet_id 可以访问
        # 一开始没有评论
        response = self.anonymous_client.get(COMMENT_URL, {
                'tweet_id': self.tweet.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['comments']), 0)

        # 评论按照时间顺序排序
        self.create_comment(self.linghu, self.tweet, '1')
        self.create_comment(self.dongxie, self.tweet, '2')
        self.create_comment(self.dongxie, self.create_tweet(self.dongxie), '3')
        response = self.anonymous_client.get(COMMENT_URL, {
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(len(response.data['comments']), 2)
        self.assertEqual(response.data['comments'][0]['content'], '1')
        self.assertEqual(response.data['comments'][1]['content'], '2')

        # 同时提供 user_id 和 tweet_id 只有 tweet_id 会在 filter 中生效
        response = self.anonymous_client.get(COMMENT_URL, {
             'tweet_id': self.tweet.id,
             'user_id': self.linghu.id,
        })
        self.assertEqual(len(response.data['comments']), 2)

    def test_comments_count(self):
        # test tweet detail api
        tweet = self.create_tweet(self.linghu)
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.dongxie_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comments_count'], 0)

        # test tweet list api
        self.create_comment(self.linghu, tweet)
        response = self.dongxie_client.get(
            TWEET_LIST_API,
            {'user_id': self.linghu.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['comments_count'], 1)

        # test newsfeeds list api
        self.create_comment(self.dongxie, tweet)
        self.create_newsfeed(self.dongxie, tweet)
        response = self.dongxie_client.get(NEWSFEED_LIST_API)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data['results'][0]['tweet']['comments_count'], 2)

    def test_comments_count_with_cache(self):
        tweet_url = '/api/tweets/{}/'.format(self.tweet.id)
        response = self.linghu_client.get(tweet_url)
        self.assertEqual(self.tweet.comments_count, 0)
        self.assertEqual(response.data['comments_count'], 0)

        data = {'tweet_id': self.tweet.id, 'content': 'a comment'}
        for i in range(2):
            _, client = self.create_user_and_client('user{}'.format(i))
            client.post(COMMENT_URL, data)
            response = client.get(tweet_url)
            self.assertEqual(response.data['comments_count'], i + 1)
            self.tweet.refresh_from_db()
            self.assertEqual(self.tweet.comments_count, i + 1)

        comment_data = self.dongxie_client.post(COMMENT_URL, data).data
        response = self.dongxie_client.get(tweet_url)
        self.assertEqual(response.data['comments_count'], 3)
        self.tweet.refresh_from_db()
        self.assertEqual(self.tweet.comments_count, 3)

        # update comment shouldn't update comments_count
        comment_url = '{}{}/'.format(COMMENT_URL, comment_data['id'])
        response = self.dongxie_client.put(comment_url, {'content': 'updated'})
        self.assertEqual(response.status_code, 200)
        response = self.dongxie_client.get(tweet_url)
        self.assertEqual(response.data['comments_count'], 3)
        self.tweet.refresh_from_db()
        self.assertEqual(self.tweet.comments_count, 3)

        # delete a comment will update comments_count
        response = self.dongxie_client.delete(comment_url)
        self.assertEqual(response.status_code, 200)
        response = self.linghu_client.get(tweet_url)
        self.assertEqual(response.data['comments_count'], 2)
        self.tweet.refresh_from_db()
        self.assertEqual(self.tweet.comments_count, 2)
