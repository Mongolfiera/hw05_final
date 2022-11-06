from django.contrib.auth import get_user_model
from django.test import TestCase

from posts.models import Comment, Group, Post

TEXT_LENGTH = 15

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestAuthor')
        cls.group = Group.objects.create(
            title='Тестовый заголовок группы',
            slug='test-slug',
            description='Тестовое описание группы',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст поста',
            group=cls.group
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый комментарий'
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        model_str = [
            {'model': PostModelTest.post,
             'str_print': PostModelTest.post.text[:TEXT_LENGTH], },
            {'model': PostModelTest.group,
             'str_print': PostModelTest.group.title, },
            {'model': PostModelTest.comment,
             'str_print': PostModelTest.comment.text[:TEXT_LENGTH]}]
        for item in model_str:
            with self.subTest(model=item['model']):
                self.assertEqual(str(item['model']), item['str_print'])
