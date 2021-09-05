from testing.testcases import TestCase
from rest_framework import status

LIKE_BASE_URL = '/api/likes/'
LIKE_CANCEL_URL = '/api/likes/cancel/'


class LikeApiTests(TestCase):
    def setUp(self):
        self.linghu, self.linghu_client = self.create_user_and_client('linghu')
        self.dongxie, self.dongxie_client = self.create_user_and_client(
            'dongxie')

    def test_tweet_likes(self):
        tweet = self.create_tweet(self.linghu)
        data = {'content_type': 'tweet', 'object_id': tweet.id}

        # 匿名用户不允许点赞
        response = self.anonymous_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # get方法不允许
        response = self.linghu_client.get(LIKE_BASE_URL, data)
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED)

        # 点赞 success
        response = self.linghu_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(tweet.like_set.count(), 1)

        # 重复点赞
        self.linghu_client.post(LIKE_BASE_URL, data)
        self.assertEqual(tweet.like_set.count(), 1)

        # 其它用户点赞
        self.dongxie_client.post(LIKE_BASE_URL, data)
        self.assertEqual(tweet.like_set.count(), 2)

    def test_comment_likes(self):
        tweet = self.create_tweet(self.linghu)
        comment = self.create_comment(self.dongxie, tweet)
        data = {'content_type': 'comment', 'object_id': comment.id}

        # anonymous is not allowed
        response = self.anonymous_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # get is not allowed
        response = self.linghu_client.get(LIKE_BASE_URL, data)
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED
        )

        # 错误的content_type
        response = self.linghu_client.post(LIKE_BASE_URL, {
            'content_type': 'coment',
            'object_id': comment.id,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual('content_type' in response.data['errors'], True)

        # 错误的object_id
        response = self.linghu_client.post(LIKE_BASE_URL, {
            'content_type': 'comment',
            'object_id': -1,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual('object_id' in response.data['errors'], True)

        # post success
        response = self.linghu_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(comment.like_set.count(), 1)

        # duplicate likes
        response = self.linghu_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(comment.like_set.count(), 1)
        self.dongxie_client.post(LIKE_BASE_URL, data)
        self.assertEqual(comment.like_set.count(), 2)

    def test_cancel(self):
        tweet = self.create_tweet(self.linghu)
        comment = self.create_comment(self.dongxie, tweet)
        like_comment_data = {'content_type': 'comment', 'object_id': comment.id}
        like_tweet_data = {'content_type': 'tweet', 'object_id': tweet.id}

        self.linghu_client.post(LIKE_BASE_URL, like_comment_data)
        self.dongxie_client.post(LIKE_BASE_URL, like_tweet_data)
        self.assertEqual(comment.like_set.count(), 1)
        self.assertEqual(tweet.like_set.count(), 1)

        # 匿名用户不能cancel
        response = self.anonymous_client.post(
            LIKE_CANCEL_URL,
            like_comment_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 不允许get
        response = self.linghu_client.get(LIKE_CANCEL_URL, like_comment_data)
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED)

        # 错误的content_type
        response = self.linghu_client.post(LIKE_CANCEL_URL, {
            'content_type': 'wrong',
            'object_id': 1,
             }
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 错误的object_id
        response = self.linghu_client.post(LIKE_CANCEL_URL, {
            'content_type': 'comment',
            'object_id': -1,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 之前没有点赞某条评论，取消点赞
        response = self.dongxie_client.post(LIKE_CANCEL_URL, like_comment_data)
        # 静默处理，即使之前没有点赞，取消点赞也返回200
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(tweet.like_set.count(), 1)
        self.assertEqual(comment.like_set.count(), 1)

        # 成功取消
        response = self.linghu_client.post(LIKE_CANCEL_URL, like_comment_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(comment.like_set.count(), 0)
        self.assertEqual(tweet.like_set.count(), 1)

        # 之前没点赞某条tweet，取消点赞
        response = self.linghu_client.post(LIKE_CANCEL_URL, like_tweet_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(comment.like_set.count(), 0)
        self.assertEqual(tweet.like_set.count(), 1)

        # 取消点赞成功
        response = self.dongxie_client.post(LIKE_CANCEL_URL, like_tweet_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(comment.like_set.count(), 0)
        self.assertEqual(tweet.like_set.count(), 0)
