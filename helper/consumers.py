import asyncio
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from langchain_core.messages import trim_messages, AIMessage, HumanMessage
from uuid import uuid4  
from channels.db import database_sync_to_async
from chats_app import models, serializers
from config import context_encrypt_storage
from langchain_groq import ChatGroq
# from ai.graphs import graphs
from workflow_graphs.proxion.graph import ProxionWorkflow


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
            llm_instance = ChatGroq(model="llama3-70b-8192")
            tool_llm_instance = ChatGroq(model="deepseek-r1-distill-llama-70b")            
            self.graph = await ProxionWorkflow.init_graph(
                chat = self.chat,
                user = self.user,
                consumer = self,
                llm = llm_instance,
                tool_llm_instance = tool_llm_instance
            )
            return True
        except Exception as e:
            await self.send_exception(str(e))
            return False

    @database_sync_to_async
    def save_llm_response(self, data):
        serializer = serializers.LLMResponseSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return True
        return False
    
    
    async def send_exception(self, msg=''):
        await self.send_json({
            'type' : "exception",
            "data" : {
                'content': msg
            }
        })
        await self.close()
        
    async def send_status(self, msg = ''):
        if len(msg) > 100:
            msg = msg[:100] + '...'
        await self.send_json({
            'type' : "status",
            "data" : {
              'content': msg
            }
        })
    
    async def send_llm_response(self, data = {}):
        status = await self.save_llm_response(data)
        if status:
            await self.send_json({
                'type' : "llm_response",
                'data': data
            })
        else:
            await self.send_json({
                'type' : "llm_response",
                'data': data
            })
            await self.send_exception("Error saving LLM response")
    
    async def send_json(self, *args, **kwargs):
        await asyncio.sleep(0.1)
        await super().send_json(*args, **kwargs)

    @classmethod
    async def generate_random_id(cls):
        return str(uuid4())