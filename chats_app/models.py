from django.db import models
from auth_app.models import User
from helper.models import UUIDPrimaryKey, TimeLine, IsActiveModel


class Chat(UUIDPrimaryKey, TimeLine, IsActiveModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chats')
    name = models.CharField(max_length=100, null=True, blank=True)
    
    
    class Meta:
        ordering = ['-updated_at', '-created_at']

    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return self.name
    
    def save(self, *args, **kwargs) -> None:
        if self.name is None or self.name == '':
            ...
            # self.name = get_name(self.first_prompt)
        super().save(*args, **kwargs)

