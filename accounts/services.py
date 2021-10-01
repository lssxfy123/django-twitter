from django.core.cache import caches
from django.conf import settings
from accounts.models import UserProfile
from twitter.cache import USER_PROFILE_PATTER

cache = caches['testing'] if settings.TESTING else caches['default']


class UserService:

    @classmethod
    def get_profile_through_cache(cls, user_id):
        """
        User的缓存和Tweet的缓存统一了起来，但UserProfile的缓存没有统一进去
        因为它缓存的key使用的不是自身的id，而是user_id
        """
        key = USER_PROFILE_PATTER.format(user_id=user_id)

        profile = cache.get(key)
        if profile is not None:
            return profile

        profile, _ = UserProfile.objects.get_or_create(user_id=user_id)
        cache.set(key, profile)
        return profile

    @classmethod
    def invalidate_profile(cls, user_id):
        key = USER_PROFILE_PATTER.format(user_id=user_id)
        cache.delete(key)
