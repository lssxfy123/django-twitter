def user_changed(sender, instance, **kwargs):
    # import写在函数里，避免循环依赖
    from accounts.services import UserService
    UserService.invalidate_user(instance.id)


def profile_changed(sender, instance, **kwargs):
    from accounts.services import UserService
    UserService.invalidate_profile(instance.user_id)
