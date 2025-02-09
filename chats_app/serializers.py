from rest_framework import serializers
from .models import Chat, LLMResponse, ChatNotes


class ChatSerializer(serializers.ModelSerializer):

    user = serializers.HiddenField(
      default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Chat
        fields = '__all__'


class LLMResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMResponse
        fields = '__all__'
        
        
class ChatNotesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatNotes
        fields = '__all__'