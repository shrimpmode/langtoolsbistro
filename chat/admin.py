from django.contrib import admin

from .models import AgentRun, Conversation, Message


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    """Read-only log of every agent turn: latency, token usage, estimated
    cost, tool calls, workflow steps (model_call_count), and errors.
    """

    list_display = (
        "created_at",
        "status",
        "model_name",
        "latency_ms",
        "model_call_count",
        "tool_names",
        "total_tokens",
        "estimated_cost_usd",
        "conversation",
    )
    list_filter = ("status", "model_name")
    search_fields = ("conversation__id", "error_message", "user_message__content")
    ordering = ("-created_at",)
    readonly_fields = [f.name for f in AgentRun._meta.fields]
    date_hierarchy = "created_at"

    @admin.display(description="Tools called")
    def tool_names(self, obj):
        return ", ".join(call["name"] for call in obj.tool_calls) or "—"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at")
    ordering = ("-created_at",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "role", "tool_used", "created_at", "short_content")
    list_filter = ("role", "tool_used")
    search_fields = ("content", "conversation__id")
    ordering = ("-created_at",)

    @admin.display(description="Content")
    def short_content(self, obj):
        return obj.content[:80]
