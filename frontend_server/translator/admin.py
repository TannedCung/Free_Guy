from django.contrib import admin

from .models import Agent, AgentMemory, Conversation, Simulation, SimulationStep


@admin.register(Simulation)
class SimulationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("name", "description")
    ordering = ("-created_at",)


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "simulation", "status", "current_location")
    list_filter = ("status", "simulation")
    search_fields = ("name", "personality_traits")
    ordering = ("simulation", "name")


@admin.register(SimulationStep)
class SimulationStepAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("simulation", "step_number", "timestamp")
    list_filter = ("simulation",)
    search_fields = ("simulation__name",)
    ordering = ("simulation", "step_number")


@admin.register(AgentMemory)
class AgentMemoryAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("agent", "memory_type", "importance_score", "created_at", "content_preview")
    list_filter = ("memory_type", "agent__simulation")
    search_fields = ("agent__name", "content")
    ordering = ("-created_at",)

    def content_preview(self, obj: AgentMemory) -> str:
        return obj.content[:80]

    content_preview.short_description = "Content"  # type: ignore[attr-defined]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("simulation", "started_at", "participant_names")
    list_filter = ("simulation",)
    search_fields = ("simulation__name",)
    ordering = ("-started_at",)

    def participant_names(self, obj: Conversation) -> str:
        return ", ".join(obj.participants.values_list("name", flat=True))

    participant_names.short_description = "Participants"  # type: ignore[attr-defined]
