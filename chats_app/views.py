import base64
from groq import Groq
from datetime import datetime, timedelta
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import ListAPIView, RetrieveDestroyAPIView, CreateAPIView
from .models import Chat, LLMResponse, ChatNotes
from .serializers import ChatSerializer, LLMResponseSerializer, ChatNotesSerializer

class ChatViewSet(ModelViewSet):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer

    def get_queryset(self):
        return super().get_queryset().filter(user = self.request.user)

    def list(self, request, *args, **kwargs):
        today = datetime.now().date()
        
        # Time boundaries
        today_start = today  # Beginning of today
        yesterday_start = today - timedelta(days=1)  # Beginning of yesterday
        seven_days_ago_start = today - timedelta(days=7)  # 7 days ago (starting point)
        thirty_days_ago_start = today - timedelta(days=30)  # 30 days ago (starting point)

        # Querysets for each group
        today_chats = Chat.objects.filter(created_at__date=today_start)

        yesterday_chats = Chat.objects.filter(
            created_at__date__gte=yesterday_start,
            created_at__date__lt=today_start  # Strictly yesterday
        )

        previous_7_days_chats = Chat.objects.filter(
            created_at__date__gte=seven_days_ago_start,
            created_at__date__lt=yesterday_start  # Not including yesterday or today
        )

        previous_30_days_chats = Chat.objects.filter(
            created_at__date__gte=thirty_days_ago_start,
            created_at__date__lt=seven_days_ago_start  # From 30 days ago to just before 7 days ago
        )

        # Serialize the data
        today_data = ChatSerializer(today_chats, many=True).data
        yesterday_data = ChatSerializer(yesterday_chats, many=True).data
        previous_7_days_data = ChatSerializer(previous_7_days_chats, many=True).data
        previous_30_days_data = ChatSerializer(previous_30_days_chats, many=True).data
        
        # Group the data into the required format
        response_data = {
            "Very Recent": today_data,
            "Recents": yesterday_data,
            "Rare": previous_7_days_data,
            "Very Rare": previous_30_days_data
        }
    
        return Response(response_data)
    
    
class NewChatAttachmentView(CreateAPIView):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)
    
    def get_object(self):
        chat_id = self.kwargs.get('chat_id')
        return Chat.objects.get(id=chat_id)

    def get_message_from_image(self, image):
        """Encodes the image and gets a message using Groq API."""
        client = Groq()

        # Encode image to base64
        base64_image = base64.b64encode(image.read()).decode('utf-8')

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            model="llama-3.2-11b-vision-preview",
        )

        return chat_completion.choices[0].message.content

    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')

        if not file:
            return Response({"error": "No file provided"}, status=400)
        try:
            message = self.get_message_from_image(file)
            chat = self.get_object()
            chat.img_attachment_content = message
            chat.save()
            return Response({"detail": f"{file.name} image message added successfully."}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
        
        
    
class ChatNotesListView(ListAPIView):

    queryset = ChatNotes.objects.all()
    serializer_class = ChatNotesSerializer

    def get_queryset(self):
        return super().get_queryset().filter(chat__user = self.request.user)

class ChatNoteRetrieveDeleteView(RetrieveDestroyAPIView):
    queryset = ChatNotes.objects.all()
    serializer_class = ChatNotesSerializer
    
    def get_object(self):
        chat_id = self.kwargs['chat_id']
        return self.queryset.get_or_create(chat_id=chat_id)[0]

class LLMResponseListView(ListAPIView):
    
    queryset = LLMResponse.objects.all()
    serializer_class = LLMResponseSerializer
    
    def get_queryset(self):
        chat_id = self.kwargs['chat_id']
        return super().get_queryset().filter(chat_id=chat_id)
    
    