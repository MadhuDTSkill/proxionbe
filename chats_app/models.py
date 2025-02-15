from django.db import models
from auth_app.models import User
from helper.models import UUIDPrimaryKey, TimeLine, IsActiveModel


class Chat(UUIDPrimaryKey, TimeLine, IsActiveModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chats')
    name = models.CharField(max_length=100, null=True, blank=True)
    is_new = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return self.name
    
    def save(self, *args, **kwargs) -> None:
        if self.name is None or self.name == '':
            ...
            # self.name = get_name(self.first_prompt)
        super().save(*args, **kwargs)


class LLMResponse(UUIDPrimaryKey, TimeLine):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='llm_responses')
    prompt = models.TextField()
    response = models.TextField()
    is_thoughted = models.BooleanField(default=False)
    thinked_thoughts = models.TextField(null=True, blank=True)
    time_taken = models.FloatField(null=True, blank=True)
    tool_responses = models.JSONField(default=list,null=True, blank=True)

    
    
    class Meta:
        ordering = ['created_at']
        
        
class ChatNotes(UUIDPrimaryKey, TimeLine):
    chat = models.OneToOneField(Chat, on_delete=models.CASCADE, related_name='chat_notes')
    notes = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['created_at']