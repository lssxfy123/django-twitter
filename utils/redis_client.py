from django.conf import settings
import redis


class RedisClient:
    # 类似C++中的静态变量，保证全局唯一的redis connection
    # 1次request会频繁的调用redis的get，set等方法
    # 所以把connection设置为全局共享的，不用频繁创建connection
    # 项目中的其它远端服务也应该如此
    conn = None

    @classmethod
    def get_connection(cls):
        # 使用singleton模式，全局只创建一个connection
        if cls.conn:
            return cls.conn
        cls.conn = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
        )
        return cls.conn

    @classmethod
    def clear(cls):
        """
        测试情况下清空redis缓存
        """
        if not settings.TESTING:
            raise Exception("You can not flush redis in production environment")
        conn = cls.get_connection()
        conn.flushdb()
