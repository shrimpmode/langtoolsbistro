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
    tool_used = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}"


class AgentRun(models.Model):
    """One log row per agent turn - what run_agent()/stream_agent_reply()
    actually did, for the admin monitoring view. Written regardless of
    success or failure, since errors are one of the things being monitored.
    """

    class Status(models.TextChoices):
        OK = "ok", "OK"
        ERROR = "error", "Error"

    conversation = models.ForeignKey(
        Conversation, related_name="agent_runs", on_delete=models.CASCADE
    )
    user_message = models.ForeignKey(
        Message, related_name="+", on_delete=models.CASCADE
    )
    assistant_message = models.ForeignKey(
        Message, related_name="+", on_delete=models.SET_NULL, null=True, blank=True
    )
    model_name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OK
    )
    error_message = models.TextField(blank=True, default="")
    latency_ms = models.PositiveIntegerField()
    model_call_count = models.PositiveIntegerField(
        default=0, help_text="Number of LLM calls this turn made (workflow steps)."
    )
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    tool_calls = models.JSONField(
        default=list, blank=True, help_text="[{'name': ..., 'args': {...}}, ...]"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.status}] {self.model_name} · {self.latency_ms}ms"
