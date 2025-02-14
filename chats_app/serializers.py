from datetime import datetime, timezone
from django.utils.timesince import timesince
from rest_framework import serializers
from .models import Chat, LLMResponse, ChatNotes

class ChatSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = '__all__'

    def get_created_at(self, obj):
        if not obj.created_at:
            return None

        now = datetime.now(timezone.utc)
        time_diff = now - obj.created_at

        if time_diff.total_seconds() < 86400:  # If within 24 hours
            return timesince(obj.created_at) + " ago"
        else:
            return obj.created_at.strftime("%b %d, %Y %I:%M %p") 


class LLMResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = LLMResponse
        fields = '__all__'
        
        
class ChatNotesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatNotes
        fields = '__all__'