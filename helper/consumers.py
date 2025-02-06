from channels.generic.websocket import AsyncJsonWebsocketConsumer
from langchain_core.messages import trim_messages, AIMessage, HumanMessage
from uuid import uuid4  
from channels.db import database_sync_to_async
from chats_app import models
from config import context_encrypt_storage
from ai.graphs import graphs

class BaseChatAsyncJsonWebsocketConsumer(AsyncJsonWebsocketConsumer):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    
    @database_sync_to_async
    def get_chat(self, chat_id):
        return models.Chat.objects.filter(id = chat_id).first()        
                
    async def user_connect(self):
        user = self.scope.get('user')
        if user is None:
            await self.close(code=4403)  
            return False
        else:
            await self.accept()
            self.user = user
            return True            
        
    async def chat_connect(self):
        chat_id = self.scope.get('url_route', {}).get('kwargs', {}).get('chat_id')
        chat = await self.get_chat(chat_id)
        if not chat:
            await self.send_exception("Can't load this chat")
            return False
        else:
            self.chat = chat
            return True
        
    async def graph_connect(self):
        try :
            self.proxion_agent_graph = graphs.ProxionAgentGraph(self.chat)
            return True
        except Exception as e:
            await self.send_exception(str(e))
            return False

    
    async def send_exception(self, msg=''):
        await self.send_json({
            'type' : "exception",
            'content': msg
        })
        await self.close()
        
    async def send_status(self, msg = ''):
        await self.send_json({
            'type' : "status",
            'content': msg
        })
    
    async def send_llm_response(self, data = {}):
        await self.send_json({
            'type' : "llm_response",
            'data': data
        })

    @classmethod
    async def generate_random_id(cls):
        return str(uuid4())