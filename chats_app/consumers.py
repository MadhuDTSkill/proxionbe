from helper.consumers import BaseChatAsyncJsonWebsocketConsumer
from .models import Chat
from config import context_encrypt_storage
from channels.db import database_sync_to_async
import asyncio


class ChatConsumer(BaseChatAsyncJsonWebsocketConsumer):
    groups = []

    async def connect(self):        
        if await self.user_connect() and await self.chat_connect():
            context_encrypt_storage.set_current_consumer_object(self)
    
    async def receive_json(self, content, **kwargs):
        ...

    async def disconnect(self, close_code):
        context_encrypt_storage.clear()
        ...