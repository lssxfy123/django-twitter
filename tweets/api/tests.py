from testing.testcases import TestCase
from rest_framework.test import APIClient
from rest_framework.views import status
from tweets.models import Tweet, TweetPhoto
from django.core.files.uploadedfile import SimpleUploadedFile
from utils.paginations import EndlessPagination


# 注意尾部要加上'/'，否则会报301 redirect
TWEET_LIST_API = '/api/tweets/'
TWEET_CREATE_API = '/api/tweets/'
TWEET_RETRIEVE_API = '/api/tweets/{}/'


class TweetApiTests(TestCase):

    def setUp(self):
        self.clear_cache()

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
        self.assertEqual(len(response.data['results']), 3)

        response = self.anonymous_client.get(TWEET_LIST_API, {
            'user_id': self.user2.id})
        self.assertEqual(len(response.data['results']), 2)

        # 检测返回的tweets是否是按照创建时间的倒序来排列的
        # Tweet模型中id是PrimaryKey，是自增数字，user是外键
        self.assertEqual(response.data['results'][0]['id'], self.tweet2[1].id)
        self.assertEqual(response.data['results'][1]['id'], self.tweet2[0].id)

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

    def test_create_with_files(self):
        # 上传的data没有files,兼容就的客户端
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': 'a selfie no files',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TweetPhoto.objects.count(), 0)

        # 上传空文件列表
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': 'a selfie',
            'files': [],
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TweetPhoto.objects.count(), 0)

        # 上传单个文件
        # content 需要是一个 bytes 类型，所以用 str.encode 转换一下
        file = SimpleUploadedFile(
            name='selfie.jpg',
            content=str.encode('a fake image'),
            content_type='image/jpeg',
        )
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': 'a selfie',
            'files': [file],
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TweetPhoto.objects.count(), 1)

        # 测试多个文件上传
        file1 = SimpleUploadedFile(
            name='selfie1.jpg',
            content=str.encode('selfie 1'),
            content_type='image/jpeg',
        )
        file2 = SimpleUploadedFile(
            name='selfie2.jpg',
            content=str.encode('selfie 2'),
            content_type='image/jpeg',
        )
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': 'two selfies',
            'files': [file1, file2],
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TweetPhoto.objects.count(), 3)

        # 从读取的 API 里确保已经包含了 photo 的地址
        retrieve_url = TWEET_RETRIEVE_API.format(response.data['id'])
        response = self.user1_client.get(retrieve_url)
        self.assertEqual(len(response.data['photo_urls']), 2)
        self.assertEqual('selfie1' in response.data['photo_urls'][0], True)
        self.assertEqual('selfie2' in response.data['photo_urls'][1], True)

        # 测试上传超过 9 个文件会失败
        files = [
            SimpleUploadedFile(
                name=f'selfie{i}.jpg',
                content=str.encode(f'selfie{i}'),
                content_type='image/jpeg',
            )
            for i in range(10)
        ]
        response = self.user1_client.post(TWEET_CREATE_API, {
            'content': 'failed due to number of photos exceeded limit',
            'files': files,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(TweetPhoto.objects.count(), 3)

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

        # tweet 里包含用户的头像和昵称
        profile = self.user1.profile
        self.assertEqual(response.data['user']['nickname'], profile.nickname)
        self.assertEqual(response.data['user']['avatar_url'], None)

    def test_pagination(self):
        page_size = EndlessPagination.page_size

        # create page_size * 2 tweets
        # we have created self.tweets1 in setUp
        for i in range(page_size * 2 - len(self.tweets1)):
            self.tweets1.append(
                self.create_tweet(self.user1, 'tweet{}'.format(i))
            )

        # 按创建时间降序排列
        tweets = self.tweets1[::-1]

        # 拉取第一页tweets
        response = self.user1_client.get(
            TWEET_LIST_API,
            {'user_id': self.user1.id}
        )
        self.assertEqual(response.data["has_next_page"], True)
        self.assertEqual(len(response.data["results"]), page_size)
        self.assertEqual(response.data["results"][0]["id"], tweets[0].id)
        self.assertEqual(response.data["results"][1]["id"], tweets[1].id)
        self.assertEqual(
            response.data["results"][page_size - 1]["id"],
            tweets[page_size - 1].id
        )

        # 拉取第二页
        response = self.user1_client.get(
            TWEET_LIST_API, {
                'user_id': self.user1.id,
                'created_at__lt': tweets[page_size - 1].created_at
            }
        )
        self.assertEqual(response.data["has_next_page"], False)
        self.assertEqual(len(response.data["results"]), page_size)
        self.assertEqual(
            response.data["results"][0]["id"],
            tweets[page_size].id
        )
        self.assertEqual(
            response.data["results"][1]["id"],
            tweets[page_size + 1].id
        )
        self.assertEqual(
            response.data["results"][page_size - 1]["id"],
            tweets[page_size * 2 - 1].id
        )

        # 拉取最新的tweets
        response = self.user1_client.get(
            TWEET_LIST_API, {
                'user_id': self.user1.id,
                'created_at__gt': tweets[0].created_at
            }
        )
        self.assertEqual(response.data["has_next_page"], False)
        self.assertEqual(len(response.data["results"]), 0)

        # 创建一个新的tweet
        new_tweet = self.create_tweet(self.user1, 'a new tweet come in')
        response = self.user1_client.get(
            TWEET_LIST_API, {
                'user_id': self.user1.id,
                'created_at__gt': tweets[0].created_at
            }
        )
        self.assertEqual(response.data["has_next_page"], False)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], new_tweet.id)
