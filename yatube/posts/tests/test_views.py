import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

GROUP_TEST_DATA_0 = {
    'title': 'Тестовый заголовок группы',
    'description': 'Тестовое описание группы',
    'slug': 'test-slug',
}
GROUP_TEST_DATA_1 = {
    'title': 'Тестовый заголовок группы 1',
    'description': 'Тестовое описание группы 1',
    'slug': 'test-slug-1',
}

POST_TEST_TEXT = 'Тестовый текст поста'
COMMENT_TEST_TEXT = 'Тестовый комментарий'

SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)

UPLOADED_0 = SimpleUploadedFile(
    name='small_0.gif',
    content=SMALL_GIF,
    content_type='image/gif'
)
UPLOADED_1 = SimpleUploadedFile(
    name='small_1.gif',
    content=SMALL_GIF,
    content_type='image/gif'
)

POSTS_ON_PAGE = 10
TOTAL_POSTS_NUM = 35

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='TestAuthor')
        cls.user = User.objects.create_user(username='TestUser')
        cls.group_0 = Group.objects.create(**GROUP_TEST_DATA_0)
        cls.group_1 = Group.objects.create(**GROUP_TEST_DATA_1)
        cls.post_with_group_0 = Post.objects.create(
            text=f'1. {POST_TEST_TEXT}',
            author=cls.author,
            group=cls.group_0,
            image=UPLOADED_0
        )
        cls.post_with_group_1 = Post.objects.create(
            text=f'2. {POST_TEST_TEXT}',
            author=cls.user,
            group=cls.group_1,
            image=UPLOADED_1
        )
        cls.post_no_group = Post.objects.create(
            text=f'3. {POST_TEST_TEXT}',
            author=cls.author
        )
        cls.comment_0 = Comment.objects.create(
            post=cls.post_with_group_0,
            author=cls.user,
            text=f'1. {COMMENT_TEST_TEXT}'
        )
        cls.comment_1 = Comment.objects.create(
            post=cls.post_with_group_0,
            author=cls.user,
            text=f'2. {COMMENT_TEST_TEXT}'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)

    def test_pages_uses_correct_template(self):
        """Во view-функциях используются правильные шаблоны."""
        urls_templates = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_posts',
                kwargs={'slug': PostPagesTests.group_0.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile',
                kwargs={'username': PostPagesTests.author}
            ): 'posts/profile.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse(
                'posts:post_detail',
                kwargs={'post_id': PostPagesTests.post_with_group_0.pk}
            ): 'posts/post_detail.html',
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostPagesTests.post_with_group_0.pk}
            ): 'posts/create_post.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }

        for address, template in urls_templates.items():
            with self.subTest(address=address):
                response = self.authorized_author.get(address)
                self.assertTemplateUsed(response, template)

    def test_form_pages_show_correct_context(self):
        """Шаблоны сформированы с правильным контекстом.
           Типы полей формы в словаре context соответствуют ожиданиям.
        """
        urls_form = {
            reverse('posts:post_create'): {
                'text': forms.fields.CharField,
                'group': forms.fields.ChoiceField,
                'image': forms.fields.ImageField,
            },
            reverse(
                'posts:post_edit',
                kwargs={'post_id': PostPagesTests.post_with_group_0.pk}
            ): {
                'text': forms.fields.CharField,
                'group': forms.fields.ChoiceField,
                'image': forms.fields.ImageField,
            },
        }

        for address, form_fields in urls_form.items():
            response = self.authorized_author.get(address)
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_post_pages_show_correct_context(self):
        """Шаблоны страниц с постами сформированы с правильным контекстом."""
        urls_context = {
            reverse('posts:index'): [
                PostPagesTests.post_with_group_0,
                PostPagesTests.post_with_group_1,
                PostPagesTests.post_no_group
            ],
            reverse(
                'posts:group_posts',
                kwargs={'slug': PostPagesTests.group_0.slug}
            ): [PostPagesTests.post_with_group_0],
            reverse(
                'posts:group_posts',
                kwargs={'slug': PostPagesTests.group_1.slug}
            ): [PostPagesTests.post_with_group_1],
            reverse(
                'posts:profile',
                kwargs={'username': PostPagesTests.author}
            ): [
                PostPagesTests.post_with_group_0,
                PostPagesTests.post_no_group
            ],
        }

        for address, page_context in urls_context.items():
            with self.subTest(address=address):
                response = self.authorized_author.get(address)
                for post in response.context['page_obj']:
                    self.assertIn(post, page_context)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        address = reverse(
            'posts:post_detail',
            kwargs={'post_id': PostPagesTests.post_with_group_0.pk}
        )
        post = PostPagesTests.post_with_group_0
        comments = [
            PostPagesTests.comment_0,
            PostPagesTests.comment_1
        ]
        response = self.authorized_author.get(address)
        self.assertEqual(response.context.get('post'), post)
        for comment in response.context.get('comments'):
            self.assertIn(comment, comments)

    def test_post_with_group_appears_in_right_places(self):
        """Пост с группой появляется на корректных страницах."""
        post = PostPagesTests.post_with_group_0
        urls_include = {
            reverse('posts:index'): True,
            reverse(
                'posts:group_posts',
                kwargs={'slug': PostPagesTests.group_0.slug}
            ): True,
            reverse(
                'posts:profile',
                kwargs={'username': PostPagesTests.author}
            ): True,
            reverse(
                'posts:group_posts',
                kwargs={'slug': PostPagesTests.group_1.slug}
            ): False,
        }

        for address, include in urls_include.items():
            with self.subTest(address=address):
                response = self.authorized_author.get(address)
                if include:
                    self.assertIn(post, response.context.get('page_obj'))
                else:
                    self.assertNotIn(post, response.context.get('page_obj'))


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.follower = User.objects.create_user(username='TestFollower')
        cls.author = User.objects.create_user(username='TestAuthor')
        cls.group = Group.objects.create(**GROUP_TEST_DATA_0)
        cls.post_with_group = Post.objects.create(
            text=f'1. {POST_TEST_TEXT}',
            author=cls.author,
            group=cls.group,
            image=UPLOADED_0
        )
        cls.post_no_group = Post.objects.create(
            text=f'2. {POST_TEST_TEXT}',
            author=cls.author
        )
        cls.follow = Follow.objects.create(
            user=cls.follower,
            author=cls.author
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)
        self.authorized_follower = Client()
        self.authorized_follower.force_login(self.follower)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)

    def test_follow(self):
        """Авторизованный пользователь может подписаться на автора,
           подписанный пользователь не может подписаться второй раз,
           неавторизованный пользователь не может подписаться на автора,
           автор не может подписаться на себя.
        """
        address = reverse(
            'posts:profile_follow',
            kwargs={'username': self.author.username}
        )
        users_to_check = {
            self.authorized_user: 1,
            self.authorized_follower: 0,
            self.guest_client: 0,
            self.authorized_author: 0,
        }
        for user, count in users_to_check.items():
            follow_count = Follow.objects.count()
            with self.subTest(address=address):
                response = user.get(address)
                self.assertEqual(Follow.objects.count(), follow_count + count)
                if count:
                    self.assertTrue(
                        Follow.objects.filter(
                            user=response.wsgi_request.user,
                            author=self.author
                        ).exists()
                    )
                    follow = Follow.objects.last()
                    self.assertEqual(follow.user, self.user)
                    self.assertEqual(follow.author, self.author)
                    follow.delete()

    def test_unfollow(self):
        """Авторизованный пользователь может отписаться от подписки."""
        Follow.objects.create(
            user=self.user,
            author=self.author
        )
        address = reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.author.username}
        )
        follow_count = Follow.objects.count()
        self.authorized_user.get(address)
        self.assertEqual(Follow.objects.count(), follow_count - 1)
        self.assertFalse(
            Follow.objects.filter(
                user=self.user,
                author=self.author
            ).exists()
        )

    def test_new_post_appears_on_following_not_unfollowing(self):
        """Новая запись пользователя появляется в ленте тех, кто
           на него подписан и не появляется в ленте тех, кто не подписан.
        """
        new_post = Post.objects.create(
            text=f'Follow {POST_TEST_TEXT}',
            author=self.author,
            group=FollowTests.group,
            image=UPLOADED_0
        )
        count = Post.objects.filter(author=self.author).count()
        address = reverse('posts:follow_index')
        users_to_check = {
            self.authorized_follower: True,
            self.authorized_user: False,
            self.authorized_author: False,
        }
        for user, check in users_to_check.items():
            with self.subTest(address=address):
                response = user.get(address)
                if check:
                    context = response.context.get('page_obj')
                    self.assertIn(new_post, context)
                    self.assertEqual(len(context.object_list), count)
                else:
                    self.assertNotIn(
                        new_post,
                        response.context.get('page_obj')
                    )


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='TestAuthor')
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(**GROUP_TEST_DATA_0)

    def setUp(self):
        cache.clear()
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)

    def test_cache_index_page_deleted_post_remains_in_cache(self):
        """Страница index.html кэшируется корректно.
           Удаленная запись остается в кэше.
        """
        post = Post.objects.create(
            text=f'Cache {POST_TEST_TEXT}',
            author=self.author,
            group=CacheTests.group,
            image=UPLOADED_0
        )
        address = reverse('posts:index')
        response_post_created = self.authorized_user.get(address)
        post.delete()
        response_post_deleted = self.authorized_user.get(address)
        self.assertEqual(
            response_post_created.content,
            response_post_deleted.content
        )

    def test_cache_clear_index_page(self):
        """Страница index.html кэшируется корректно.
           После очистки кэша изменения появляются.
        """
        post = Post.objects.create(
            text=f'Cache {POST_TEST_TEXT}',
            author=self.author,
            group=CacheTests.group,
            image=UPLOADED_0
        )
        address = reverse('posts:index')
        response_post_created = self.authorized_user.get(address)
        post.delete()
        cache.clear()
        response_cache_cleared = self.authorized_user.get(address)
        self.assertNotEqual(
            response_post_created.content,
            response_cache_cleared.content
        )


class PaginatorViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='TestAuthor')
        cls.group = Group.objects.create(**GROUP_TEST_DATA_0)
        posts = [
            Post(text=f'{post_number}. {POST_TEST_TEXT}',
                 author=cls.author,
                 group=cls.group)
            for post_number in range(1, TOTAL_POSTS_NUM + 1)
        ]
        Post.objects.bulk_create(posts)

    def test_pages_contain_correct_number_of_records(self):
        """Проверка паджинатора."""
        urls_with_paginator = [
            reverse('posts:index'),
            reverse(
                'posts:group_posts',
                kwargs={'slug': PaginatorViewsTests.group.slug}
            ),
            reverse(
                'posts:profile',
                kwargs={'username': PaginatorViewsTests.author}
            ),
        ]
        number_of_pages = (
            TOTAL_POSTS_NUM // POSTS_ON_PAGE
            + int(bool(TOTAL_POSTS_NUM % POSTS_ON_PAGE)))

        for page_number in range(number_of_pages):
            posts_on_page = min(
                TOTAL_POSTS_NUM - page_number * POSTS_ON_PAGE,
                POSTS_ON_PAGE
            )

            for address in urls_with_paginator:
                with self.subTest(address=address):
                    response = self.client.get(
                        address, {'page': page_number + 1}
                    )
                    number_of_posts = len(response.context['page_obj'])
                    self.assertEqual(number_of_posts, posts_on_page)
