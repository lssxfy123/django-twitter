from rest_framework import serializers
from tweets.api.serializers import TweetSerializer


class NewsFeedSerializer(serializers.Serializer):
    tweet = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    # # TweetSerializer需要使用request，但这里无法添加
    # # 需要往NewsFeedSerializer中传递context={'request': request}
    # # 它会向下传递给TweetSerializer
    # tweet = TweetSerializer(source='cached_tweet')

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    def get_tweet(self, obj):
        # 要手动指定context，通过SerializerMethodField调用，不会自动往下传递context
        return TweetSerializer(obj.cached_tweet, context=self.context).data

    def get_created_at(self, obj):
        return obj.created_at
