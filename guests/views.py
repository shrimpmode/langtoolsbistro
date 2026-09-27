"""Guest sign-in for a conversation.

A conversation's UUID already acts as its access token (anyone holding it
can post to it), so signing in attaches the verified email to the
conversation rather than starting a separate Django session.
"""
from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.models import Conversation
from chat.serializers import ConversationSerializer

from .models import MockEmail
from .serializers import LoginRequestSerializer, LoginVerifySerializer, MockEmailSerializer
from .services import normalize_email, request_login_code, verify_login_code


class LoginRequestView(APIView):
    def post(self, request, conversation_id):
        get_object_or_404(Conversation, id=conversation_id)
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_login_code(serializer.validated_data["email"])
        return Response({"detail": "Code sent."}, status=status.HTTP_202_ACCEPTED)


class LoginVerifyView(APIView):
    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        serializer = LoginVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        if not verify_login_code(email, serializer.validated_data["code"]):
            return Response(
                {"detail": "That code is wrong or has expired. Request a new one and try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conversation.guest_email = normalize_email(email)
        conversation.save(update_fields=["guest_email"])
        return Response(ConversationSerializer(conversation).data)


class LogoutView(APIView):
    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)
        conversation.guest_email = ""
        conversation.save(update_fields=["guest_email"])
        return Response(ConversationSerializer(conversation).data)


class MockInboxView(APIView):
    def get(self, request):
        if not settings.MOCK_INBOX_ENABLED:
            raise Http404
        emails = MockEmail.objects.all()[:20]
        return Response(MockEmailSerializer(emails, many=True).data)
