from django_hbase.models import HBaseField, IntegerField, TimestampField
from django_hbase.client import HBaseClient
from django.conf import settings
from django_hbase.models.exceptions import BadRowKeyError, EmptyColumnError


class HBaseModel:

    class Meta:
        table_name = None
        row_key = ()

    @classmethod
    def get_table(cls):
        conn = HBaseClient.get_connection()

        return conn.table(cls.get_table_name())

    @property
    def row_key(self):
        return self.serialize_row_key(self.__dict__)

    @classmethod
    def get_table_name(cls):
        if not cls.Meta.table_name:
            raise NotImplementedError(
                'Missing table_name in HBaseModel meta class')
        if settings.TESTING:
            return 'test_{}'.format(cls.Meta.table_name)
        return cls.Meta.table_name

    @classmethod
    def drop_table(cls):
        if not settings.TESTING:
            raise Exception('You can not create table outside of unit tests')
        conn = HBaseClient.get_connection()
        conn.delete_table(cls.get_table_name(), True)

    @classmethod
    def create_table(cls):
        """
        只能在单元测试时使用，正常的数据库类似mysql，在命令行中创建
        """
        if not settings.TESTING:
            raise Exception('You can not create table outside of unit tests')
        conn = HBaseClient.get_connection()
        # decode将bytes转换为str
        tables = [table.decode('utf-8') for table in conn.tables()]
        if cls.get_table_name() in tables:
            # 已经存在
            return
        # 字典解析式，create_table接收的参数就是这样
        column_families = {
            field.column_family: dict()
            for key, field in cls.get_field_hash().items()
            if field.column_family is not None
        }
        conn.create_table(cls.get_table_name(), column_families)

    @classmethod
    def get_field_hash(cls):
        """
        key为field的名称,value为HBaseField对象的dict
        """
        field_hash = {}
        for field in cls.__dict__:
            field_obj = getattr(cls, field)
            if isinstance(field_obj, HBaseField):
                field_hash[field] = field_obj
        return field_hash

    def __init__(self, **kwargs):
        """
        构造函数，把kwargs中key-value赋给Model中对应的key-value
        setattr方法用的很巧妙
        """
        for key, field in self.get_field_hash().items():
            value = kwargs.get(key)
            setattr(self, key, value)

    @classmethod
    def init_from_row(cls, row_key, row_data):
        """
        把从HBase中获取的一行数据，初始化为一个HBaseModel instance
        """
        if not row_data:
            return None
        data = cls.deserialize_row_key(row_key)
        for column_key, column_value in row_data.items():
            column_key = column_key.decode('utf-8')
            # remove column family
            key = column_key[column_key.find(':') + 1:]
            data[key] = cls.deserialize_field(key, column_value)
        return cls(**data)

    @classmethod
    def serialize_row_key(cls, data, is_prefix=False):
        """
        row key进行序列化，存储的实际是Mode中row key对应的value
        例如HBaseFollowing中from_user_id对应的值
        不能直接存from_user_id这个名称，否则所有的row_key都是相同的
        而row_key类似于mysql中的primary key，不能相同
        serialize dict to bytes (not str)
        {key1: val1} => b"val1"
        {key1: val1, key2: val2} => b"val1:val2"
        {key1: val1, key2: val2, key3: val3} => b"val1:val2:val3"
        """
        field_hash = cls.get_field_hash()
        values = []
        for key, field in field_hash.items():
            # field为column key
            if field.column_family:
                continue
            value = data.get(key)
            if value is None:
                # 如果value为None，但是有前缀，也是允许行的
                if not is_prefix:
                    raise BadRowKeyError(f'{key} is missing in row key')
                break
            value = cls.serialize_field(field, value)
            if ':' in value:
                raise BadRowKeyError(
                    f'{key} should not contain ":" in value: {value}')
            values.append(value)
        return bytes(':'.join(values), encoding='utf-8')

    @classmethod
    def deserialize_row_key(cls, row_key):
        data = {}
        if isinstance(row_key, bytes):
            row_key = row_key.decode('utf-8')

        # val1:val2 => val1:val2: 方便每次 find(':') 都能找到一个 val
        row_key = row_key + ':'
        for key in cls.Meta.row_key:
            index = row_key.find(':')
            if index == -1:
                break
            data[key] = cls.deserialize_field(key, row_key[:index])
            row_key = row_key[index + 1:]
        return data

    @classmethod
    def serialize_field(cls, field, value):
        value = str(value)
        # TimestampField不需要补位，因为它存储的是一个非常大的整数
        # 最高位很难发生进位(下辈子都不会)，不会因为长度影响排序
        if isinstance(field, IntegerField):
            # 因为排序规则是按照字典序排序，那么就可能出现 1 10 2 这样的排序
            # 解决的办法是固定 int 的位数为 16 位（8的倍数更容易利用空间），不足位补 0
            value = str(value)
            while len(value) < 16:
                value = '0' + value
        if field.reverse:
            value = value[::-1]
        return value

    @classmethod
    def deserialize_field(cls, key, value):
        field = cls.get_field_hash()[key]
        if field.reverse:
            value = value[::-1]
        if field.field_type in [IntegerField.field_type,
                                TimestampField.field_type]:
            return int(value)
        return value

    @classmethod
    def serialize_row_data(cls, data):
        """
        序列化除row key之外的值，也就是row data，列中的值
        它是一个dict，其key就是column key
        """
        row_data = {}
        field_hash = cls.get_field_hash()
        for key, field in field_hash.items():
            # 如果是row key
            if not field.column_family:
                continue
            column_key = '{}:{}'.format(field.column_family, key)
            column_value = data.get(key)
            if column_value is None:
                continue
            row_data[column_key] = cls.serialize_field(field, column_value)
        return row_data

    def save(self, batch=None):
        row_data = self.serialize_row_data(self.__dict__)
        # 如果 row_data 为空，即没有任何 column key values 需要存储 hbase 会直接不存储
        # 这个 row_key, 因此我们可以 raise 一个 exception 提醒调用者，避免存储空值
        if len(row_data) == 0:
            raise EmptyColumnError
        if batch:
            # batch.put()不会立刻产生一个HBase的数据库请求
            # 而是会等到batch.send()执行后，一次性把所有的批量数据都写入到HBase
            # batch的好处是：通常情况下HBase和Web Server不在同一台机器上，这样每次写
            # HBase都会产生一个类似request的请求，而batch只会产生一次请求，
            # 可以节省时间
            batch.put(self.row_key, row_data)
        else:
            table = self.get_table()
            table.put(self.row_key, row_data)

    @classmethod
    def get(cls, **kwargs):
        """
        获取指定的一行数据，并初始化为一个instance
        """
        # 这里直接传kwargs，就是传一个dict进去
        row_key = cls.serialize_row_key(kwargs)
        table = cls.get_table()
        row = table.row(row_key)
        return cls.init_from_row(row_key, row)

    # <HOMEWORK> 实现一个 get_or_create 的方法，返回 (instance, created)

    @classmethod
    def serialize_row_key_from_tuple(cls, row_key_tuple):
        if row_key_tuple is None:
            return None
        data = {
            key: value
            for key, value in zip(cls.Meta.row_key, row_key_tuple)
        }
        return cls.serialize_row_key(data, is_prefix=True)

    @classmethod
    def filter(cls, start=None, stop=None, prefix=None,
               limit=None, reverse=False):
        # serialize tuple to str
        # start, stop, prefix可以直接传一个tuple进来，类似(1, ts)
        # 表示from_user_id=1,timestamp=ts的row_key
        # 通过serialize_row_key_from_tuple序列化为字符串
        # 如果不这样，而直接调用serialize_row_key，就需要传一个dict进来，
        # 类似{'from_user_id': 1, 'timestamp': ts}，这样比较
        # 麻烦，不如tuple那样方便调用者使用
        row_start = cls.serialize_row_key_from_tuple(start)
        row_stop = cls.serialize_row_key_from_tuple(stop)
        row_prefix = cls.serialize_row_key_from_tuple(prefix)

        # scan table
        table = cls.get_table()
        rows = table.scan(
            row_start, row_stop, row_prefix,
            limit=limit, reverse=reverse)

        # deserialize to instance list
        results = []
        for row_key, row_data in rows:
            instance = cls.init_from_row(row_key, row_data)
            results.append(instance)
        return results

    @classmethod
    def delete(cls, **kwargs):
        row_key = cls.serialize_row_key(kwargs)
        table = cls.get_table()
        return table.delete(row_key)

    # step 1：创建HBaseModel
    @classmethod
    def create(cls, batch=None, **kwargs):
        # 类似django ORM的写法
        # 调用__init__构造函数
        instance = cls(**kwargs)
        instance.save(batch=batch)
        return instance

    @classmethod
    def batch_create(cls, batch_data):
        table = cls.get_table()
        batch = table.batch()
        results = []
        for data in batch_data:
            results.append(cls.create(batch=batch, **data))
        batch.send()
        return results

