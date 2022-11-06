from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        help_texts = {
            'text': _('Введите текст сообщения.'),
            'group': _('Выберите группу для сообщения.')
        }
        labels = {
            'text': _('Текст поста'),
            'group': _('Группа')
        }

    def clean_text(self):
        data = self.cleaned_data['text']
        if not data:
            raise forms.ValidationError('Текст поста не может быть пустым.')
        return data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        help_texts = {
            'text': _('Введите комментарий'),
        }
        labels = {
            'text': _('Комментарий'),
        }

    def clean_text(self):
        data = self.cleaned_data['text']
        if not data:
            raise forms.ValidationError(
                'Текст комментария не может быть пустым.'
            )
        return data
