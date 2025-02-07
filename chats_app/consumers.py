from helper.consumers import BaseChatAsyncJsonWebsocketConsumer
from .models import Chat
from channels.db import database_sync_to_async
import asyncio


class ChatConsumer(BaseChatAsyncJsonWebsocketConsumer):
    groups = []

    async def connect(self):        
        if await self.user_connect() and await self.chat_connect() and await self.graph_connect():
            ...
            
    async def receive_json(self, content, **kwargs):
        prompt = content.get('prompt', {})
        await self.get_response(prompt)        
        
    async def get_response(self, prompt):
        content = prompt.get('content', '')
        if not content:
            await self.send_exception("Prompt is empty")
        await self.send_status("Processing...")
        response = await self.graph.invoke(content)
        await self.send_llm_response(response)

    async def disconnect(self, close_code):
        ...