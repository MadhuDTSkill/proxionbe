from django.urls import path, include
from .views import ChatViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('chats', ChatViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
