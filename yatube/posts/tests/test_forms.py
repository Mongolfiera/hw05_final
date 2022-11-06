import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Comment, Group, Post

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
FORM_TEST_TEXT = 'Тестовый текст формы'
COMMENT_TEST_TEXT = 'Тестовый текст комментария'

SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='TestAuthor')
        cls.user = User.objects.create_user(username='TestUser')
        cls.group_0 = Group.objects.create(**GROUP_TEST_DATA_0)
        cls.group_1 = Group.objects.create(**GROUP_TEST_DATA_1)
        cls.post_with_group_0 = Post.objects.create(
            text=f'{POST_TEST_TEXT} 1',
            author=cls.author,
            group=cls.group_0
        )
        cls.post_with_group_1 = Post.objects.create(
            text=f'{POST_TEST_TEXT} 2',
            author=cls.user,
            group=cls.group_1
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostFormsTests.user)
        self.authorized_author = Client()
        self.authorized_author.force_login(PostFormsTests.author)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        form_data = {
            'text': FORM_TEST_TEXT,
            'group': PostFormsTests.group_0.pk,
            'image': uploaded,
        }
        response = self.authorized_author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.author})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        last_post = Post.objects.first()
        self.assertEqual(last_post.text, form_data['text'])
        self.assertEqual(last_post.group.pk, form_data['group'])
        self.assertEqual(last_post.image, f'posts/{uploaded.name}')
        self.assertEqual(last_post.author, PostFormsTests.author)

    def test_create_post_by_guest(self):
        """Валидная форма не создает запись в Post без авторизации
           и не ломается.
        """
        posts_count = Post.objects.count()
        form_data = {
            'text': FORM_TEST_TEXT,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertNotEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(
            response,
            '/auth/login/?next=/create/'
        )
        last_post = Post.objects.first()
        self.assertNotEqual(last_post.text, form_data['text'])

    def test_edit_post(self):
        """Валидная форма редактирует запись в Post."""
        posts_count = Post.objects.count()
        edited = SimpleUploadedFile(
            name='edited.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        post_id = PostFormsTests.post_with_group_0.pk
        form_edit_data = {
            'text': f'{FORM_TEST_TEXT} updated',
            'group': PostFormsTests.group_1.pk,
            'image': edited,
        }
        response = self.authorized_author.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': post_id}
            ),
            data=form_edit_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': f'{post_id}'}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count)
        edited_post = Post.objects.get(pk=post_id)
        self.assertEqual(edited_post.text, form_edit_data['text'])
        self.assertEqual(edited_post.group.pk, form_edit_data['group'])
        self.assertEqual(edited_post.image, f'posts/{edited.name}')
        self.assertEqual(edited_post.author, PostFormsTests.author)

    def test_edit_post_not_author(self):
        """Валидная форма, созданная не автором поста
           не редактирует запись в Post.
        """
        posts_count = Post.objects.count()
        post_id = PostFormsTests.post_with_group_1.pk
        form_edit_data = {
            'text': f'{FORM_TEST_TEXT} updated',
            'group': PostFormsTests.group_0.pk,
        }
        response = self.authorized_author.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': post_id}
            ),
            data=form_edit_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                kwargs={'post_id': f'{post_id}'}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count)
        original_post = Post.objects.get(pk=post_id)
        self.assertEqual(
            original_post.text, PostFormsTests.post_with_group_1.text
        )
        self.assertEqual(
            original_post.group, PostFormsTests.post_with_group_1.group
        )
        self.assertEqual(original_post.author, PostFormsTests.user)

    def test_create_comment(self):
        """Валидная форма создает комментарий."""
        post_id = PostFormsTests.post_with_group_0.pk
        comments_count = Comment.objects.count()
        form_comment_data = {
            'text': COMMENT_TEST_TEXT,
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post_id}),
            data=form_comment_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': post_id})
        )
        last_comment = Comment.objects.first()
        self.assertEqual(last_comment.text, form_comment_data['text'])
        self.assertEqual(last_comment.post.pk, post_id)
        self.assertEqual(last_comment.author, PostFormsTests.user)

    def test_comment_by_guest(self):
        """Валидная форма не создает комментарий без авторизации
           и не ломается.
        """
        post_id = PostFormsTests.post_with_group_0.pk
        comments_count = Comment.objects.count()
        form_comment_data = {
            'text': COMMENT_TEST_TEXT,
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': post_id}),
            data=form_comment_data,
            follow=True
        )
        self.assertNotEqual(Comment.objects.count(), comments_count + 1)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{post_id}/comment/'
        )
