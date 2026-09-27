import uuid

from django.db import models


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"

    conversation = models.ForeignKey(
        Conversation, related_name="messages", on_delete=models.CASCADE
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    # Every tool the agent called this turn, in order: [{"name": ..., "args": {...}}].
    tool_calls = models.JSONField(default=list, blank=True)
    # The full LangChain message sequence the agent produced this turn
    # (tool-calling AIMessages, ToolMessages, final AIMessage), serialized
    # with messages_to_dict. Replayed as history on later turns so the model
    # still sees what its tools returned, not just its final text.
    turn_messages = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"
