from rest_framework import views, generics, status, response
from . import serializers
from auth_app import models
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle
from helper.utils import delete_session


class RegisterView(generics.CreateAPIView):
    serializer_class = serializers.RegisterSerializer
    queryset = models.User.objects.all()
    authentication_classes = []
    permission_classes = [AllowAny]
    
    
class LoginView(views.APIView):
    serializer_class = serializers.LoginSerializer
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        login_data = serializer.validated_data
        return response.Response(login_data, status=status.HTTP_200_OK)
     
     
class LogoutView(views.APIView):
    
    def post(self, request):
        session_key = request.decoded_payload.get('session_key')
        if session_key:
            delete_session(session_key)
        return response.Response({'detail' : "Successfully logged out"}, status=status.HTTP_200_OK)
 
 
class SocialLoginView(views.APIView):
    serializer_class = serializers.SocialLoginSerializer
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        login_data = serializer.validated_data
        return response.Response(login_data, status=status.HTTP_200_OK)
    
    
class UserSelfUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = serializers.UserSelfUpdateSerializer
    queryset = models.User.objects.all()

    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return serializers.UserSerializer
        return super().get_serializer_class()
    
   
    