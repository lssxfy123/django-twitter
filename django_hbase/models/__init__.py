"""
这里用了相对包导入
from django_hbase.models import xxx等同于
from django_hbase.models.__init__ import xxx
这样可以在__init__.py中通过相对包导入fields和hbase_models中的内容
把fields和hbase_models层级向上提
只有这种情况下，才会使用相对路径，从这个文件的当前目录寻找，而不是绝对路径的找法
"""
from .fields import *
from .hbase_models import *
from .exceptions import *
