def incr_likes_count(sender, instance, created, **kwargs):
    from tweets.models import Tweet
    from django.db.models import F

    if not created:
        return

    model_class = instance.content_type.model_class()
    if model_class != Tweet:
        return

    # 不可以使用 tweet.likes_count += 1; tweet.save() 的方式
    # 因此这个操作不是原子操作，必须使用 update 语句才是原子操作
    # mysql有row lock行锁，保证原子操作
    tweet = instance.content_object
    # 对应的sql: UPDATE tweets_tweet SET likes_count = likes_count + 1 WHERE
    # id = tweet.id
    # F函数是保证sql语句翻译为likes_count = likes_count + 1，而不是把likes_count
    # 的实际值拿出来，例如likes_count = 10 + 1，这样确保更新时使用的是likes_count
    # 的最新值
    Tweet.objects.filter(id=tweet.id).update(likes_count=F('likes_count') + 1)


def decr_likes_count(sender, instance, **kwargs):
    from tweets.models import Tweet
    from django.db.models import F

    model_class = instance.content_type.model_class()
    if model_class != Tweet:
        return

    # 不可以使用 tweet.likes_count += 1; tweet.save() 的方式
    # 因此这个操作不是原子操作，必须使用 update 语句才是原子操作
    tweet = instance.content_object
    Tweet.objects.filter(id=tweet.id).update(likes_count=F('likes_count') - 1)
