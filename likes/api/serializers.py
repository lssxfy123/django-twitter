from rest_framework import serializers
from likes.models import Like
from accounts.api.serializers import UserSerializerForLike
from rest_framework.exceptions import ValidationError
from tweets.models import Tweet
from comments.models import Comment
from django.contrib.contenttypes.models import ContentType


class LikeSerializer(serializers.ModelSerializer):
    # source中指定从Like model中取一个cached_user的函数
    user = UserSerializerForLike(source='cached_user')

    class Meta:
        model = Like
        fields = ('user', 'created_at')


class BaseLikeSerializerForCreateAndCancel(serializers.ModelSerializer):
    object_id = serializers.IntegerField()
    # choices可以和前端约定写什么
    content_type = serializers.ChoiceField(choices=['tweet', 'comment'])

    class Meta:
        model = Like
        fields = ('content_type', 'object_id',)

    def _get_model_class(self, data):
        if data['content_type'] == 'comment':
            return Comment
        if data['content_type'] == 'tweet':
            return Tweet
        return None

    def validate(self, data):
        model_class = self._get_model_class(data)
        if model_class is None:
            raise ValidationError({
                'content_type': 'Content type does not exist'
            })
        like_object = model_class.objects.filter(id=data['object_id']).first()
        if like_object is None:
            raise ValidationError({
                'object_id': 'Object does not exist'
            })
        return data


class LikeSerializerForCreate(BaseLikeSerializerForCreateAndCancel):

    # 返回值有之前的Like对象变成了(instance, created)
    # created表示是否创建成功Like对象，如果之前已创建，是直接get的，
    # created就是False
    # 这样因为viewset发送notification时，需要知道这个赞是创建的，
    # 还是get到的，只有创建的赞才会发送notification
    def get_or_create(self):
        validated_data = self.validated_data
        model_class = self._get_model_class(validated_data)
        return Like.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(model_class),
            object_id=validated_data['object_id'],
            user=self.context['request'].user,
        )


class LikeSerializerForCancel(BaseLikeSerializerForCreateAndCancel):

    def cancel(self):
        """
        cancel 方法是一个自定义的方法，cancel 不会被 serializer.save 调用
        所以需要直接调用 serializer.cancel()
        """
        model_class = self._get_model_class(self.validated_data)
        """
        这个删除其实不一定会成功，因为取消点赞并没有等待点赞成功之后再进行，
        所以like对象不一定存在于数据库中，不过也不需要进行验证，因为取消不成功也
        没关系，可以容忍这种不成功，前端页面可以显示为成功取消了
        也可以在缓存中记录cancel，等create到来时，可以在缓存中查找是否cancel，如果
        cancel了就直接不创建了
        """
        deleted, _ = Like.objects.filter(
            content_type=ContentType.objects.get_for_model(model_class),
            object_id=self.validated_data['object_id'],
            user=self.context['request'].user,
        ).delete()
        return deleted
