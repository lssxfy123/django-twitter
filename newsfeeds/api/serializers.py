from rest_framework import serializers
from newsfeeds.models import NewsFeed
from tweets.api.serializers import TweetSerializer


class NewsFeedSerializer(serializers.ModelSerializer):
    # TweetSerializer需要使用request，但这里无法添加
    # 需要往NewsFeedSerializer中传递context={'request': request}
    # 它会向下传递给TweetSerializer
    tweet = TweetSerializer()

    class Meta:
        model = NewsFeed
        fields = ('id', 'created_at', 'tweet')
