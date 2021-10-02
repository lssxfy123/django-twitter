from testing.testcases import TestCase
from utils.redis_client import RedisClient


class UtilsTests(TestCase):

    def setUp(self):
        self.clear_cache()
        RedisClient.clear()

    def test_redis_client(self):
        conn = RedisClient.get_connection()
        # 在list的左边添加一个1
        # 如果不存在，就创建一个空列表并插入1
        # lpush把1转换为b'1'存储在Redis中
        conn.lpush('redis_key', 1)
        conn.lpush('redis_key', 2)

        # 读取key为redis_key的值，从索引0到末尾
        cached_list = conn.lrange('redis_key', 0, -1)
        # b''表示字节型字符串
        # 如果希望使用1,2，还需要进行转换，Redis中存储的是字节型字符串
        self.assertEqual(cached_list, [b'2', b'1'])

        RedisClient.clear()
        cached_list = conn.lrange('redis_key', 0, -1)
        self.assertEqual(cached_list, [])
