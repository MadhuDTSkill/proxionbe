from django.urls import path, include
from .views import ChatViewSet, LLMResponseListView, ChatNotesListView, ChatNoteRetrieveDeleteView, NewChatAttachmentView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('chats', ChatViewSet, basename='chats')

urlpatterns = [
    path('', include(router.urls)),
    path('<chat_id>/notes/', ChatNoteRetrieveDeleteView.as_view(), name='llm-responses'),
    path('notes-list/', ChatNotesListView.as_view(), name='llm-responses'),
    path('<chat_id>/llm-responses/', LLMResponseListView.as_view(), name='llm-responses'),
    path('<chat_id>/new-chat-attachment/', NewChatAttachmentView.as_view(), name='new-chat-attachment'),
]
