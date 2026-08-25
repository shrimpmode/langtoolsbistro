from django.urls import path

from .views import ConversationCreateView, MessageListCreateView

urlpatterns = [
    path("conversations/", ConversationCreateView.as_view(), name="conversation-create"),
    path(
        "conversations/<uuid:conversation_id>/messages/",
        MessageListCreateView.as_view(),
        name="message-list-create",
    ),
]
