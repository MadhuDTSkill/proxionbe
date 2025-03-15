
from django.urls import path, include


urlpatterns = [
    path('api/auth/', include('auth_app.urls')),
    path('api/chat/', include('chats_app.urls')),
]


def get_ws_urlpatterns():
    from chats_app.ws_urls import urlpatterns
    return urlpatterns
    