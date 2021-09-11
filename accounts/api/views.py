from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.api.serializers import (
    UserSerializer,
    LoginSerializer,
    SignupSerializer,
    UserProfileSerializerForUpdate,
    UserSerializerForProfile,
)
from django.contrib.auth import (
   login as django_login,
   logout as django_logout,
   authenticate as django_authenticate,
)
from rest_framework.permissions import AllowAny
from accounts.models import UserProfile
from utils.permissions import IsObjectOwner


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allow usert to be viewed or edited
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializerForProfile
    permission_classes = [permissions.IsAdminUser]


class AccountViewSet(viewsets.ViewSet):
    permission_classes = (AllowAny, )
    serializer_class = SignupSerializer

    @action(methods=['POST'], detail=False)
    def signup(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "Please check input.",
                "errors": serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        # 创建用户并保存，会调用SignupSerializer中的create
        user = serializer.save()

        # 创建完成后，帮助用户登陆
        django_login(request, user)
        return Response({
            'success': True,
            # 这里不能用SignupSerializer，会把password也返回
            'user': UserSerializer(user).data,
        }, status=status.HTTP_201_CREATED)    # 返回201更准确，也可以返回200

    @action(methods=['GET'], detail=False)
    def login_status(self, request):
        data = {
            'has_logged_in': request.user.is_authenticated,
            'ip': request.META["REMOTE_ADDR"]
        }
        if request.user.is_authenticated:
            data['user'] = UserSerializer(request.user).data
        return Response(data)

    @action(methods=['POST'], detail=False)
    def logout(self, request):
        django_logout(request)
        return Response({"success:true"})

    @action(methods=['POST'], detail=False)
    def login(self, request):
        # get username and password from request
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "Please check input.",
                "errors": serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        # 用户名不存在
        if not User.objects.filter(username=username).exists():
            return Response({
                "success": False,
                "message": "User does not exists."
            }, status=status.HTTP_400_BAD_REQUEST)

        user = django_authenticate(username=username, password=password)
        if not user or user.is_anonymous:
            return Response({
                "success": False,
                "message": "username and password does not match.",
            }, status=status.HTTP_400_BAD_REQUEST)

        django_login(request, user)
        return Response({
            "success": True,
            "user": UserSerializer(instance=user).data,
        }, status=status.HTTP_200_OK)


class UserProfileViewSet(
    viewsets.GenericViewSet,
    viewsets.mixins.UpdateModelMixin,  # 使用默认的update方法
):
    queryset = UserProfile
    permission_classes = (permissions.IsAuthenticated, IsObjectOwner,)
    serializer_class = UserProfileSerializerForUpdate
