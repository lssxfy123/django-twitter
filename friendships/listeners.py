def invalidate_following_cache(sender, instance, **kwargs):
    """
    instance就是创建或删除的Friendship模型对象
    """
    # 需要在函数内部进行import，不能写在外面，因为services.py中有导入模型Friendship
    # from friendships.models import Friendship
    # 而models.py中又会导入invalidate_following_cache
    # from friendships.listeners import invalidate_following_cache
    # 如果直接在listeners.py中导入FriendshipService，就会出现循环引用
    # 在函数内部导入，这样是执行时才会导入FriendshipService时，它里面的方法都已存在
    # 这是工程化代码的一种常用写法
    from friendships.services import FriendshipService
    FriendshipService.invalidate_following_cache(instance.from_user_id)
