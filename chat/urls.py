from django.urls import path

from .views import (
    ConversationCreateView,
    ConversationDetailView,
    MessageListCreateView,
    stream_message,
)

urlpatterns = [
    path("conversations/", ConversationCreateView.as_view(), name="conversation-create"),
    path(
        "conversations/<uuid:conversation_id>/",
        ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
    path(
        "conversations/<uuid:conversation_id>/messages/",
        MessageListCreateView.as_view(),
        name="message-list-create",
    ),
    path(
        "conversations/<uuid:conversation_id>/messages/stream/",
        stream_message,
        name="message-stream",
    ),
]
