from testing.testcases import TestCase
from rest_framework.test import APIClient
from friendships.models import Friendship
from newsfeeds.models import NewsFeed
from rest_framework.views import status
from utils.paginations import EndlessPagination
from django.conf import settings
from newsfeeds.services import NewsFeedService

NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEETS_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/{}/follow/'


class NewsFeedApiTest(TestCase):
    def setUp(self):
        self.clear_cache()
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
        self.assertEqual(len(response.data["results"]), 0)

        # 自己发的信息会出现在自己的新鲜事列表中
        self.linghu_client.post(POST_TWEETS_URL, {"content": "Hello World"})
        response = self.linghu_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data["results"]), 1)

        # 关注别人后，可以看别人发的tweet
        self.linghu_client.post(FOLLOW_URL.format(self.dongxie.id))
        response = self.dongxie_client.post(POST_TWEETS_URL, {
            "content": "Hello Twitter"
        })
        post_tweet_id = response.data["id"]
        response = self.linghu_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["tweet"]["id"],
                         post_tweet_id)

    def test_pagination(self):
        page_size = EndlessPagination.page_size
        followed_user = self.create_user('followed')
        newsfeeds = []
        for i in range(page_size * 2):
            tweet = self.create_tweet(followed_user)
            newsfeeds.append(self.create_newsfeed(self.linghu, tweet))

        # 按创建时间降序排列
        newsfeeds = newsfeeds[::-1]

        # 拉取第一页
        response = self.linghu_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.data['has_next_page'], True)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['results'][0]['id'], newsfeeds[0].id)
        self.assertEqual(response.data['results'][1]['id'], newsfeeds[1].id)
        self.assertEqual(
            response.data['results'][page_size - 1]['id'],
            newsfeeds[page_size - 1].id,
        )

        # pull the second page
        response = self.linghu_client.get(
            NEWSFEEDS_URL,
            {'created_at__lt': newsfeeds[page_size - 1].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        results = response.data['results']
        self.assertEqual(len(results), page_size)
        self.assertEqual(results[0]['id'], newsfeeds[page_size].id)
        self.assertEqual(results[1]['id'], newsfeeds[page_size + 1].id)
        self.assertEqual(
            results[page_size - 1]['id'],
            newsfeeds[2 * page_size - 1].id,
        )

        # pull latest newsfeeds
        response = self.linghu_client.get(
            NEWSFEEDS_URL,
            {'created_at__gt': newsfeeds[0].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 0)

        tweet = self.create_tweet(followed_user)
        new_newsfeed = self.create_newsfeed(user=self.linghu, tweet=tweet)

        response = self.linghu_client.get(
            NEWSFEEDS_URL,
            {'created_at__gt': newsfeeds[0].created_at},
        )
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], new_newsfeed.id)

    def test_user_cache(self):
        profile = self.dongxie.profile
        profile.nickname = 'huanglaoxie'
        profile.save()  # save()方法执行时，cache中对应的key会删除掉

        self.assertEqual(self.linghu.username, 'linghu')
        self.create_newsfeed(self.dongxie, self.create_tweet(self.linghu))
        self.create_newsfeed(self.dongxie, self.create_tweet(self.dongxie))

        response = self.dongxie_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'dongxie')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'huanglaoxie')
        self.assertEqual(results[1]['tweet']['user']['username'], 'linghu')

        self.linghu.username = 'linghuchong'
        self.linghu.save()
        profile.nickname = 'huangyaoshi'
        profile.save()

        response = self.dongxie_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'dongxie')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'huangyaoshi')
        self.assertEqual(results[1]['tweet']['user']['username'], 'linghuchong')

    def test_tweet_cache(self):
        tweet = self.create_tweet(self.linghu, 'content1')
        self.create_newsfeed(self.dongxie, tweet)
        response = self.dongxie_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'linghu')
        self.assertEqual(results[0]['tweet']['content'], 'content1')

        # update username
        self.linghu.username = 'linghuchong'
        self.linghu.save()
        response = self.dongxie_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'linghuchong')

        # update content
        tweet.content = 'content2'
        tweet.save()
        response = self.dongxie_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['content'], 'content2')

    def _paginate_to_get_newsfeeds(self, client):
        # 一直翻页到最底部
        response = client.get(NEWSFEEDS_URL)
        results = response.data['results']
        while response.data['has_next_page']:
            created_at__lt = response.data['results'][-1]['created_at']
            response = client.get(NEWSFEEDS_URL, {
                'created_at__lt': created_at__lt
            })
            results.extend(response.data['results'])
        return results

    def test_redis_list_limit(self):
        list_limit = settings.REDIS_LIST_LENGTH_LIMIT
        page_size = 10
        users = [self.create_user('user{}'.format(i)) for i in range(5)]
        newsfeeds = []
        for i in range(list_limit + page_size):
            tweet = self.create_tweet(
                user=users[i % 5],
                content='feed{}'.format(i)
            )
            feed = self.create_newsfeed(self.linghu, tweet)
            newsfeeds.append(feed)
        newsfeeds = newsfeeds[::-1]

        # 最多获取list_limit的缓存数据
        cached_newsfeeds = NewsFeedService.get_cached_newsfeeds(self.linghu.id)
        self.assertEqual(len(cached_newsfeeds), list_limit)

        # 数据库中所有的newsfeeds
        queryset = NewsFeed.objects.filter(user=self.linghu)
        self.assertEqual(len(queryset), list_limit + page_size)

        # 翻页一直翻到底
        results = self._paginate_to_get_newsfeeds(self.linghu_client)
        self.assertEqual(len(results), list_limit + page_size)
        for i in range(list_limit + page_size):
            self.assertEqual(newsfeeds[i].id, results[i]['id'])

        # linghu关注dongxie
        self.create_friendship(self.linghu, self.dongxie)
        # dongxie发布一条tweet
        new_tweet = self.create_tweet(self.dongxie, 'a new tweet')
        NewsFeedService.fanout_to_followers(new_tweet)

        def _test_newsfeeds_after_new_feed_pushed():
            results = self._paginate_to_get_newsfeeds(self.linghu_client)
            self.assertEqual(len(results), list_limit + page_size + 1)
            self.assertEqual(results[0]['tweet']['id'], new_tweet.id)
            for i in range(list_limit + page_size):
                self.assertEqual(newsfeeds[i].id, results[i + 1]['id'])

        _test_newsfeeds_after_new_feed_pushed()

        # 缓存失效
        self.clear_cache()
        _test_newsfeeds_after_new_feed_pushed()
