from django.contrib.auth.models import User
from django.test import TestCase
from tweets.models import Tweet
from datetime import timedelta
from util.time_helpers import utc_now


class TweetTests(TestCase):

    def test_hour_to_now(self):
        user = User.objects.create_user(username="linghu")
        tweet = Tweet.objects.create(user=user, content="Jiuzhang Dafa Good!")
        tweet.created_at = utc_now() - timedelta(hours=10)
        tweet.save()
        self.assertEqual(tweet.hours_to_now, 10)
