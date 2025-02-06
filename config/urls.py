
from django.urls import path, include
import chats_app.ws_urls


urlpatterns = [
    path('api/auth/', include('auth_app.urls')),
    path('api/chat/', include('chats_app.urls')),
]

ws_urlpatterns = [
]



ws_urlpatterns += chats_app.ws_urls.urlpatterns