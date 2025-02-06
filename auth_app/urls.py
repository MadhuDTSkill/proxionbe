from django.urls import path
from . import views

urlpatterns = [
    path('register', views.RegisterView.as_view(), name='register'),
    path('login', views.LoginView.as_view(), name='login'),
    path('logout', views.LogoutView.as_view(), name='login'),
    path('social-login', views.SocialLoginView.as_view(), name='social-login'),
    path('me', views.UserSelfUpdateView.as_view(), name='me'),
]

