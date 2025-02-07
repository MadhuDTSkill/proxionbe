from django.urls import path, include
from .views import ChatViewSet, LLMResponseViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('chats', ChatViewSet, basename='chats')
router.register('responses', LLMResponseViewSet, basename='responses')

urlpatterns = [
    path('', include(router.urls)),
]
