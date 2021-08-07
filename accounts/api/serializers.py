from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework import exceptions


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email']


# 检测username, password是否存在
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        if not User.objects.filter(username=data["username"].lower()).exists():
            raise exceptions.ValidationError({
                "username": 'User does not exist.'
            })
        return data


# 相比Serializer更进一步封装，默认包含create和update
class SignupSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=20, min_length=6)
    email = serializers.EmailField()
    password = serializers.CharField(max_length=20, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    # will be called when is_valid is called
    def validate(self, data):
        # 增加验证 username是不是已经存在
        if User.objects.filter(username=data['username'].lower()).exists():
            raise exceptions.ValidationError({
                "username": "This username has been occupied."
            })

        if User.objects.filter(email=data['email'].lower()).exists():
            raise exceptions.ValidationError({
                'email': 'This email address has been occupied.'
            })
        return data

    def create(self, validated_data):
        # 存储用户名时就要是小写，这样validate时提升效率
        username = validated_data['username'].lower()
        email = validated_data['email'].lower()
        password = validated_data['password']

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        return user


