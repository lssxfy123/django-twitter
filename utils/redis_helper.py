from django.conf import settings
from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer


class RedisHelper:

    @classmethod
    def _load_objects_to_cache(cls, key, objects):
        conn = RedisClient.get_connection()

        serialized_list = []
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
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            # 如果key不存在，就直接从数据库load
            # 不走单个push的方式加到cache里了
            cls._load_objects_to_cache(key, queryset)
            return
        serialized_data = DjangoModelSerializer.serialize(obj)
        # 这里使用lpush，添加到头部，保证是按时间降序的
        conn.lpush(key, serialized_data)
