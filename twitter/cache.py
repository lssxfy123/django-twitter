# Memcached
FOLLOWINGS_PATTERN = 'followings:{user_id}'
# 这里不使用userprofile_id，对UserProfile的查询通常也不是根据userprofile_id
# 来查询的，user_id会作为外键存在很多表单中，所以通常使用user_id来查询UserProfile
USER_PROFILE_PATTER = 'userprofile:{user_id}'

# Redis
USER_TWEETS_PATTERN = 'user_tweets:{user_id}'
USER_NEWSFEEDS_PATTERN = 'user_newsfeeds:{user_id}'
