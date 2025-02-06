import requests
from rest_framework import serializers
from rest_framework_simplejwt.tokens import AccessToken
from auth_app import models
from helper.exceptions import SmoothException
from helper.utils import decode_token, encode_token, create_session


###################################################################### Authentication ######################################################################


class UserSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = models.User
        exclude = ['password', 'profile_picture']

class UserSelfUpdateSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(read_only=True)
    
    class Meta:
        model = models.User
        fields = ['id', 'first_name', 'last_name', 'email', 'profile_picture']


class RegisterSerializer(serializers.ModelSerializer):
    
    def create(self, validated_data):
        """Create and return a new user."""
        user = models.User.objects.create_user(**validated_data)
        return user            
            

    def to_representation(self, instance):
        return {
            "detail" : "Registration completed successfully.",
        }

    class Meta:
        model = models.User
        fields = ['email', 'password', 'first_name', 'last_name']
        

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """Validate the email and password, then authenticate and generate a token."""

        email = data.get('email')
        password = data.get('password')
        login_data = {}

        user = models.User.objects.filter(email=email).first()
        if not user:
            raise SmoothException("User with this email does not exist.")
        
        if not user.check_password(password):
            raise SmoothException("Incorrect password.")

        if not user.is_active:
            raise SmoothException("This account is deactivated. Contact to your administrator to activate it.")

        session_data = {
            "user_id": str(user.id),
        }
        session_key = create_session(session_data)
        token = encode_token({
            'session_key' : session_key
        })
        user_data = UserSerializer(user).data
        
        login_data['user'] = user_data
        login_data['token'] = str(token)
        return login_data
    
    
class SocialLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    given_name = serializers.CharField()
    family_name = serializers.CharField()

    def authenticate_google(self, token):
        google_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
        response = requests.get(google_url)
        if response.status_code == 200:
            return response.json()
        return None        
        
    def authenticate_microsoft(self, token):
        microsoft_url = f"https://graph.microsoft.com/v1.0/me"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(microsoft_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        return None


    def validate(self, data):
        """Validate the email, given name and family, then authenticate and generate a token."""

        provider = data.get('provider')
        token = data.get('token')
        login_data = {}
        
        if provider == "google":
            user_data = self.authenticate_google(token)
        elif provider == "microsoft":
            user_data = self.authenticate_microsoft(token)
        else:
            raise SmoothException("Invalid provider!", status_code=401)

        if not user_data:
            raise SmoothException("Invalid token.", status_code=401)
        
        email = user_data.get('email')
        first_name = user_data.get('given_name')
        last_name = user_data.get('family_name')
        
        user, created = models.User.objects.get_or_create(email=email, first_name=first_name, last_name=last_name)
        if created:
                user.set_unusable_password()
                user.save()        
        
        session_data = {
            "user_id": str(user.id),
        }
        session_key = create_session(session_data)
        token = encode_token({
            'session_key' : session_key
        })
        user_data = UserSerializer(user).data
        
        login_data['user'] = user_data
        login_data['token'] = str(token)
        return login_data
    

    
        
        
        