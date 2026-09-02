import json
import logging

from django.http import Http404, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .agent.orchestrator import run_agent, stream_agent_reply
from .models import Conversation, Message
from .serializers import (
    ConversationSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)

logger = logging.getLogger(__name__)


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


@csrf_exempt
async def stream_message(request, conversation_id):
    """SSE variant of MessageListCreateView.post - streams the reply as it's
    generated instead of waiting for the full turn to finish.

    A plain async view rather than a DRF APIView: everything else in this
    API is sync, and this one only needs to be async because streaming an
    async generator body requires it. csrf_exempt matches the rest of this
    API - there's no session auth anywhere here (see AllowAny in settings),
    so there's no CSRF token for the frontend to send.
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed"}, status=405)

    try:
        conversation = await Conversation.objects.aget(id=conversation_id)
    except Conversation.DoesNotExist:
        raise Http404

    try:
        body = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON body"}, status=400)

    user_content = (body.get("content") or "").strip()
    if not user_content:
        return JsonResponse({"content": ["This field may not be blank."]}, status=400)

    prior_messages = [m async for m in conversation.messages.all()]
    await Message.objects.acreate(
        conversation=conversation, role=Message.Role.USER, content=user_content
    )

    async def event_stream():
        # Headers are already sent by the time an error can happen here, so
        # there's no HTTP status left to signal failure with - an `error`
        # SSE event is the only way to tell the client the turn didn't
        # finish. No assistant message is persisted in that case.
        try:
            async for event in stream_agent_reply(user_content, prior_messages):
                if event["type"] != "done":
                    yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
                    continue

                assistant_message = await Message.objects.acreate(
                    conversation=conversation,
                    role=Message.Role.ASSISTANT,
                    content=event["reply"],
                    tool_used=event["tool_used"],
                )
                payload = MessageSerializer(assistant_message).data
                yield f"event: done\ndata: {json.dumps(payload)}\n\n"
        except Exception:
            logger.exception(
                "Streaming agent reply failed for conversation %s", conversation_id
            )
            error_payload = {"detail": "Something went wrong talking to the assistant."}
            yield f"event: error\ndata: {json.dumps(error_payload)}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"  # disable proxy buffering, if ever fronted by one
    return response
