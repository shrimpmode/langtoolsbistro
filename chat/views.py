from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .agent.orchestrator import run_agent
from .models import Conversation, Message
from .serializers import (
    ConversationSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)


class ConversationCreateView(APIView):
    def post(self, request):
        conversation = Conversation.objects.create()
        return Response(
            ConversationSerializer(conversation).data, status=status.HTTP_201_CREATED
        )


class MessageListCreateView(APIView):
    def get(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        messages = conversation.messages.all()
        return Response(MessageSerializer(messages, many=True).data)

    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_content = serializer.validated_data["content"]

        prior_messages = list(conversation.messages.all())
        Message.objects.create(
            conversation=conversation, role=Message.Role.USER, content=user_content
        )

        result = run_agent(user_content, prior_messages)

        assistant_message = Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=result["reply"],
            tool_used=result["tool_used"],
        )

        return Response(
            MessageSerializer(assistant_message).data, status=status.HTTP_201_CREATED
        )
