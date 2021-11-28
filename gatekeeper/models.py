from utils.redis_client import RedisClient


class GateKeeper:
    """
    GateKeeper要缓存到Redis中，因为它会被经常访问到
    """
    @classmethod
    def get(cls, gk_name):
        conn = RedisClient.get_connection()
        name = 'gatekeeper:{}'.format(gk_name)
        if not conn.exists(name):
            return {'percent': 0, 'description': ''}

        # hgetall获取所有的key-value
        redis_hash = conn.hgetall(name)
        return {
            'percent': int(redis_hash.get(b'percent', 0)),
            'description': str(redis_hash.get(b'description', '')),
        }

    @classmethod
    def set_kv(cls, gk_name, key, value):
        conn = RedisClient.get_connection()
        name = f'gatekeeper:{gk_name}'
        conn.hset(name, key, value)

    @classmethod
    def is_switch_on(cls, gk_name):
        """
        0-1型开关，要么开，要么不开
        """
        return cls.get(gk_name)['percent'] == 100

    @classmethod
    def turn_on(cls, gk_name):
        cls.set_kv(gk_name, 'percent', 100)

    @classmethod
    def in_gk(cls, gk_name, user_id):
        """
        漏斗型开关：部分放开，例如放开20%，user_id % 100如果小于20，就表示可以使用
        某些功能，否则不能使用
        """
        return user_id % 100 < cls.get(gk_name)['percent']
