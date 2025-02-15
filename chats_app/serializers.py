from datetime import datetime, timezone
from django.utils.timesince import timesince
from rest_framework import serializers
from .models import Chat, LLMResponse, ChatNotes

class ChatSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

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
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    chat_name = serializers.SerializerMethodField()
    sections = serializers.SerializerMethodField()


    def get_created_at(self, obj):
        if not obj.created_at:
            return None
        now = datetime.now(timezone.utc)
        time_diff = now - obj.created_at
        if time_diff.total_seconds() < 86400:  # If within 24 hours
            return timesince(obj.created_at) + " ago"
        else:
            return obj.created_at.strftime("%b %d, %Y %I:%M %p")
    
    def get_updated_at(self, obj):
        if not obj.updated_at:
            return None
        now = datetime.now(timezone.utc)
        time_diff = now - obj.updated_at
        if time_diff.total_seconds() < 86400:  # If within 24 hours
            return timesince(obj.updated_at) + " ago"
        else:
            return obj.updated_at.strftime("%b %d, %Y %I:%M %p")
        
    def get_sections(self, obj):
        notes = obj.notes
        sections = []
        for note in notes.keys():
            sections.append(note)
        return sections
    
    def get_chat_name(self, obj):
        return obj.chat.name
    
    class Meta:
        model = ChatNotes
        fields = '__all__'