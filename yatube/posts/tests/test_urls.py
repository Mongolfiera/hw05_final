from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Follow, Group, Post

GROUP_TEST_DATA = {
    'title': 'Тестовый заголовок группы',
    'description': 'Тестовое описание группы',
    'slug': 'test-slug',
}

POST_TEST_TEXT = 'Тестовый текст поста'

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='TestAuthor')
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(**GROUP_TEST_DATA)
        cls.post = Post.objects.create(
            text=POST_TEST_TEXT,
            author=cls.author,
            group=cls.group
        )
        cls.follow = Follow.objects.create(
            user=cls.user,
            author=cls.author
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)
        self.urls_resp_status = {
            reverse('posts:index'): {
                'unauth': HTTPStatus.OK,
                'auth': HTTPStatus.OK,
                'author': HTTPStatus.OK,
                'template': 'posts/index.html',
            },
            reverse(
                'posts:group_posts',
                kwargs={'slug': self.group.slug}
            ): {
                'unauth': HTTPStatus.OK,
                'auth': HTTPStatus.OK,
                'author': HTTPStatus.OK,
                'template': 'posts/group_list.html',
            },
            reverse(
                'posts:profile',
                kwargs={'username': self.user}
            ): {
                'unauth': HTTPStatus.OK,
                'auth': HTTPStatus.OK,
                'author': HTTPStatus.OK,
                'template': 'posts/profile.html',
            },
            reverse('posts:post_create'): {
                'unauth': HTTPStatus.FOUND,
                'auth': HTTPStatus.OK,
                'author': HTTPStatus.OK,
                'template': 'posts/create_post.html',
            },
            reverse(
                'posts:post_detail',
                kwargs={'post_id': self.post.pk}
            ): {
                'unauth': HTTPStatus.OK,
                'auth': HTTPStatus.OK,
                'author': HTTPStatus.OK,
                'template': 'posts/post_detail.html',
            },
            reverse(
                'posts:post_edit',
                kwargs={'post_id': self.post.pk}
            ): {
                'unauth': HTTPStatus.FOUND,
                'auth': HTTPStatus.FOUND,
                'author': HTTPStatus.OK,
                'template': 'posts/create_post.html',
            },
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.pk}
            ): {
                'unauth': HTTPStatus.FOUND,
                'auth': HTTPStatus.FOUND,
                'author': HTTPStatus.FOUND,
                'template': 'posts/create_post.html',
            },
            reverse('posts:follow_index'): {
                'unauth': HTTPStatus.FOUND,
                'auth': HTTPStatus.OK,
                'author': HTTPStatus.OK,
                'template': 'posts/follow.html',
            },
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author}
            ): {
                'unauth': HTTPStatus.FOUND,
                'auth': HTTPStatus.FOUND,
                'author': HTTPStatus.FOUND,
                'template': 'posts/profile.html'
            },
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author}
            ): {
                'unauth': HTTPStatus.FOUND,
                'auth': HTTPStatus.FOUND,
                'author': HTTPStatus.FOUND,
                'template': 'posts/profile.html'
            },
            '/unexisting_page/': {
                'unauth': HTTPStatus.NOT_FOUND,
                'auth': HTTPStatus.NOT_FOUND,
                'author': HTTPStatus.NOT_FOUND,
                'template': 'core/404.html'
            },
        }

    def test_post_url_exists_at_desired_location(self):
        """Проверка доступности страниц разным типам пользователей."""
        users = {
            'unauth': self.guest_client,
            'auth': self.authorized_client,
            'author': self.authorized_author,
        }
        for user, client in users.items():
            for address, status in self.urls_resp_status.items():
                with self.subTest(address=address):
                    response = client.get(address)
                    self.assertEqual(response.status_code, status[user])

    def test_post_url_unauth_redirect_on_admin_login(self):
        """Страницы создания и редактирования поста перенаправят
        анонимного пользователя на страницу логина.
        """
        urls_unauth_redirect = {
            reverse('posts:post_create'): '/auth/login/?next=/create/',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostURLTests.post.pk}
            ):
                f'/auth/login/?next=/posts/{PostURLTests.post.pk}/edit/',
            reverse(
                'posts:add_comment',
                kwargs={'post_id': PostURLTests.post.pk}
            ):
                f'/auth/login/?next=/posts/{PostURLTests.post.pk}/comment/',
            reverse(
                'posts:profile_follow',
                kwargs={'username': PostURLTests.author}
            ):
                f'/auth/login/?next=/profile/{PostURLTests.author}/follow/',
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': PostURLTests.author}
            ):
                f'/auth/login/?next=/profile/{PostURLTests.author}/unfollow/',
        }
        for address, redirect_url in urls_unauth_redirect.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address, follow=True)
                self.assertRedirects(response, redirect_url)

    def test_post_url_auth_redirect_edit_on_post_page(self):
        """Страница редактирования поста перенаправит авторизованного
        не автора поста на страницу просмотра поста.
        """
        response = self.authorized_client.get(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostURLTests.post.pk}
            ), follow=True
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail',
                kwargs={'post_id': PostURLTests.post.pk}
            ))

    def test_urls_uses_correct_template(self):
        """URL-адреса используют правильные шаблоны."""
        for address, status in self.urls_resp_status.items():
            with self.subTest(address=address):
                response = self.authorized_author.get(address)
                if response.status_code != HTTPStatus.FOUND:
                    self.assertTemplateUsed(response, status['template'])
