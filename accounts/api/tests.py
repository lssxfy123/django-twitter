from rest_framework.test import APIClient
from rest_framework.views import status
from testing.testcases import TestCase
from accounts.models import UserProfile
from django.core.files.uploadedfile import SimpleUploadedFile

LOGIN_URL = '/api/accounts/login/'
LOGOUT_URL = '/api/accounts/logout/'
SIGNUP_URL = '/api/accounts/signup/'
LOGIN_STATUS_URL = '/api/accounts/login_status/'
USER_PROFILE_DETAIL_URL = '/api/profiles/{}/'


# TestCase继承链上有Python自带的unittest
# 会查找以test_开头的函数进行执行
class AccountApiTest(TestCase):

    def setUp(self):
        # 这个函数是重载了父类的函数
        # 这个函数会在每个 test function 执行的时候被执行
        # 所以这里要放的内容是大部分test function都需要的
        self.client = APIClient()
        self.user = self.create_user(
            username='admin',
            email='admin@jiuzhang.com',
            password='correct password',
        )

    def test_login(self):
        # 每个测试函数必须以test_开头，才会被自动调用进行测试
        # 测试必须用post，而不是get
        # 下面这个就是错误的调用方式，会返回405
        response = self.client.get(LOGIN_URL, {
            "username": self.user.username,
            "password": "correct password",
        })

        # 登陆失败，status code 返回405
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED)

        # 用了post，但密码错误
        response = self.client.post(LOGIN_URL, {
            "username": self.user.username,
            "password": "wrong password",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 验证还没有登陆
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data["has_logged_in"], False)

        # 用正确的密码
        response = self.client.post(LOGIN_URL, {
            "username": self.user.username,
            "password": "correct password"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data["user"], None)
        self.assertEqual(response.data['user']['id'], self.user.id)

        # 验证已经登陆了
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data["has_logged_in"], True)

        # 不存在的用户名
        response = self.client.post(LOGIN_URL, {
            'username': 'notexists',
            "password": 'correct password'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(response.data["errors"]["username"][0]),
                         'User does not exist.')

    def test_logout(self):
        # 先登录
        self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })
        # 验证用户已经登录
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

        # 测试必须用 post
        response = self.client.get(LOGOUT_URL)
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED)

        # 改用 post 成功 logout
        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 验证用户已经登出
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)

    def test_signup(self):
        data = {
            'username': 'someone',
            'email': 'someone@jiuzhang.com',
            'password': 'any password',
        }
        # 测试 get 请求失败
        response = self.client.get(SIGNUP_URL, data)
        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED)

        # 测试错误的邮箱
        response = self.client.post(SIGNUP_URL, {
            'username': 'someone',
            'email': 'not a correct email',
            'password': 'any password'
        })
        # print(response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 测试密码太短
        response = self.client.post(SIGNUP_URL, {
            'username': 'someone',
            'email': 'someone@jiuzhang.com',
            'password': '123',
        })
        # print(response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 测试用户名太长
        response = self.client.post(SIGNUP_URL, {
            'username': 'username is tooooooooooooooooo loooooooong',
            'email': 'someone@jiuzhang.com',
            'password': 'any password',
        })
        # print(response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 成功注册
        response = self.client.post(SIGNUP_URL, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['username'], 'someone')
        # 验证 user profile 已经被创建
        created_user_id = response.data['user']['id']
        profile = UserProfile.objects.filter(user_id=created_user_id).first()
        self.assertNotEqual(profile, None)
        # 验证用户已经登入
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)


class UserProfileAPITests(TestCase):

    def test_update(self):
        linghu, linghu_client = self.create_user_and_client('linghu')
        p = linghu.profile
        p.nickname = 'old nickname'
        p.save()
        url = USER_PROFILE_DETAIL_URL.format(p.id)

        # 匿名用户
        response = self.anonymous_client.put(url, {
            'nickname': 'a new nickname',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data['detail'],
            'Authentication credentials were not provided.'
        )

        # test can only be updated by user himself.
        _, dongxie_client = self.create_user_and_client('dongxie')
        response = dongxie_client.put(url, {
            'nickname': 'a new nickname',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data['detail'],
            'You do not have permission to access this object',
        )
        p.refresh_from_db()
        self.assertEqual(p.nickname, 'old nickname')

        # update nickname
        response = linghu_client.put(url, {
            'nickname': 'a new nickname',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        p.refresh_from_db()
        self.assertEqual(p.nickname, 'a new nickname')

        # update avatar
        response = linghu_client.put(url, {
            'avatar': SimpleUploadedFile(
                name='my-avatar.jpg',
                content=str.encode('a fake image'),
                content_type='image/jpeg',
            ),
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 这里不能写my-avatar.jpg，因为django会自动给上传的文件重命名
        # 可以查看media文件夹下面
        self.assertEqual('my-avatar' in response.data['avatar'], True)
        p.refresh_from_db()
        self.assertIsNotNone(p.avatar)
