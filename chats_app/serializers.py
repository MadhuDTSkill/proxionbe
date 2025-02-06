from rest_framework import serializers
from .models import Chat


class ChatSerializer(serializers.ModelSerializer):

    user = serializers.HiddenField(
      default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Chat
        fields = '__all__'

