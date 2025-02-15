from helper.consumers import BaseChatAsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from chats_app.models import ChatNotes
from ai import schemas
from langchain_groq import ChatGroq

class ChatConsumer(BaseChatAsyncJsonWebsocketConsumer):
    groups = []

    async def connect(self):        
        """Establishes WebSocket connection and initializes LLM."""
        if await self.user_connect() and await self.chat_connect() and await self.graph_connect():
            self.llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0.1,
            )

    async def disconnect(self, close_code):
        """Handles WebSocket disconnection."""
        ...

    async def receive_json(self, content, **kwargs):
        """Handles incoming JSON messages."""
        prompt = content.get('prompt', {})
        await self.get_response(prompt)
    
    async def get_response(self, prompt):
        """Processes user prompt and sends response."""
        content = prompt.get('content', '')
        mode = prompt.get('mode', 'Casual')
        if not content:
            await self.send_exception("Prompt is empty")
        await self.send_status("Thinking...")
        response = await self.graph.ainvoke(content, selected_mode=mode)
        await self.change_chat_is_new_flag_if_response_is_first_time(content, response.get('final_response', ''))
        await self.generate_bullet_points(response.get('final_response', ''))
        await self.send_llm_response(response)
    
    async def get_structured_response(self, prompt, schema):
        """Generates a structured response using the LLM."""
        structured_llm = self.llm.with_structured_output(schema)
        return await structured_llm.ainvoke(prompt)
    
    async def get_new_chat_name(self, prompt, llm_response):
        """Extracts a name for a new chat from the LLM response."""
        response = await self.get_structured_response(prompt, schemas.ChatNameResponse)
        return response.model_dump()
    
    async def change_chat_is_new_flag_if_response_is_first_time(self, prompt, llm_response):
        """Marks the chat as new if this is the first response."""
        if await self.get_current_chat_responses_count() == 0:
            new_chat_name = await self.get_new_chat_name(prompt, llm_response)
            new_chat_name = new_chat_name.get('name', '')
            await self.change_chat_is_new_flag_to_true(new_chat_name)
    
    async def generate_bullet_points(self, llm_response):
        """Generates and stores bullet points from the LLM response."""
        response = await self.get_structured_response(llm_response, schemas.BulletPoints)
        bullet_points = response.model_dump()        
        await self.create_or_update_current_chat_notes(bullet_points)
    
    @database_sync_to_async
    def create_or_update_current_chat_notes(self, bullet_points: schemas.BulletPoints):
        """Creates or updates chat notes with extracted bullet points."""
        chat_notes, _ = ChatNotes.objects.get_or_create(chat=self.chat)
        old_notes = chat_notes.notes
        new_notes_title = bullet_points.get('title', '')
        new_notes_points = bullet_points.get('points', [])
        
        if new_notes_title not in old_notes:
            old_notes[new_notes_title] = new_notes_points
        else:
            old_notes[new_notes_title] += new_notes_points
        
        chat_notes.notes = old_notes
        chat_notes.save()
    
    @database_sync_to_async
    def change_chat_is_new_flag_to_true(self, name):
        """Sets chat name and marks it as new."""
        self.chat.name = name[:100]
        self.chat.is_new = True
        self.chat.save()
    
    @database_sync_to_async
    def get_current_chat_responses_count(self):
        """Returns the number of responses in the current chat."""
        return len(list(self.chat.llm_responses.all()))
