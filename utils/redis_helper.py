from django.conf import settings
from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer


class RedisHelper:

    @classmethod
    def _load_objects_to_cache(cls, key, objects):
        conn = RedisClient.get_connection()

        serialized_list = []
        # objects已经被截断了
        for obj in objects:
            serialized_data = DjangoModelSerializer.serialize(obj)
            serialized_list.append(serialized_data)

        if serialized_list:
            # 在尾部插入serialized_list中的所有元素到key对应的list中
            # rpush, lpush可以接受list值，也可以是单个值
            conn.rpush(key, *serialized_list)
            conn.expire(key, settings.REDIS_KEY_EXPIRE_TIME)  # 设置超时时间

    @classmethod
    def load_objects(cls, key, queryset):
        # 最多只 cache REDIS_LIST_LENGTH_LIMIT 那么多个 objects
        # 超过这个限制的 objects，就去数据库里读取。
        # 一般这个限制会比较大，比如 1000
        # 因此翻页翻到 1000 的用户访问量会比较少，从数据库读取也不是大问题
        queryset = queryset[:settings.REDIS_LIST_LENGTH_LIMIT]
        conn = RedisClient.get_connection()

        # 如果在cache里，就直接拿出来
        if conn.exists(key):
            # 从左往右全部取出来
            serialized_list = conn.lrange(key, 0, -1)
            objects = []
            for serialized_data in serialized_list:
                serialized_obj = DjangoModelSerializer\
                    .deserialize(serialized_data)
                objects.append(serialized_obj)
            return objects

        # 如果key不存在，就存入cache中
        cls._load_objects_to_cache(key, queryset)
        # 这里没有再去从cache中获取tweets，而是采用list
        # 此时list方法不会再次产生query查询，因为在_load_objects_to_cache
        # 中遍历了queryset并产生了query查询，queryset会缓存查询结果
        return list(queryset)

    @classmethod
    def push_object(cls, key, obj, queryset):
        queryset = queryset[:settings.REDIS_LIST_LENGTH_LIMIT]
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            # 如果key不存在，就直接从数据库load
            # 不走单个push的方式加到cache里了
            cls._load_objects_to_cache(key, queryset)
            return
        serialized_data = DjangoModelSerializer.serialize(obj)
        # 这里使用lpush，添加到头部，保证是按时间降序的
        conn.lpush(key, serialized_data)
        conn.ltrim(key, 0, settings.REDIS_LIST_LENGTH_LIMIT - 1)

    @classmethod
    def get_count_key(cls, obj, attr):
        return '{}.{}:{}'.format(obj.__class__.__name__, attr, obj.id)

    @classmethod
    def incr_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj, attr)
        if not conn.exists(key):
            # 回填到cache中
            # 不执行+1操作，因为调用incr_count之前，已经在数据库中执行了+1
            # 并且obj重新从数据库加载了
            obj.refresh_from_db()
            conn.set(key, getattr(obj, attr))
            conn.expire(key, settings.REDIS_KEY_EXPIRE_TIME)
            return getattr(obj, attr)
        return conn.incr(key)

    @classmethod
    def decr_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj, attr)
        if not conn.exists(key):
            obj.refresh_from_db()
            # 不执行-1操作
            conn.set(key, getattr(obj, attr))
            conn.expire(key, settings.REDIS_KEY_EXPIRE_TIME)
            return getattr(obj, attr)
        return conn.decr(key)

    @classmethod
    def get_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj, attr)
        count = conn.get(key)
        if count is not None:
            return int(count)

        # obj有可能是从cache中获取的，要重新从数据库中加载
        obj.refresh_from_db()
        count = getattr(obj, attr)
        conn.set(key, count)
        return count
