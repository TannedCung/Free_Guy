from django.contrib import admin

from .models import (
    Agent,
    AgentMemory,
    Character,
    ConceptNode,
    Conversation,
    ConversationParticipant,
    Demo,
    DemoMovement,
    EnvironmentState,
    KeywordStrength,
    Map,
    MovementRecord,
    Persona,
    PersonaScratch,
    RuntimeState,
    Simulation,
    SimulationStep,
    SpatialMemory,
)


@admin.register(Map)
class MapAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("id", "name", "maze_name", "max_agents", "is_active")
    list_filter = ("is_active",)
    search_fields = ("id", "name", "maze_name")


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "owner", "age", "status", "simulation")
    list_filter = ("status",)
    search_fields = ("name", "owner__username", "traits", "backstory")
    ordering = ("owner", "name")


@admin.register(Simulation)
class SimulationAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "status", "owner", "map_id", "visibility", "maze_name", "step", "created_at", "updated_at")
    list_filter = ("status", "visibility")
    search_fields = ("name", "description", "maze_name")
    ordering = ("-created_at",)


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "simulation", "first_name", "last_name", "age", "status")
    list_filter = ("status", "simulation")
    search_fields = ("name", "first_name", "last_name", "innate", "learned")
    ordering = ("simulation", "name")


@admin.register(PersonaScratch)
class PersonaScratchAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("persona", "curr_time", "act_description", "chatting_with")
    list_filter = ("persona__simulation",)
    search_fields = ("persona__name", "act_description", "act_address")
    ordering = ("persona",)


@admin.register(EnvironmentState)
class EnvironmentStateAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("simulation", "step")
    list_filter = ("simulation",)
    search_fields = ("simulation__name",)
    ordering = ("simulation", "step")


@admin.register(MovementRecord)
class MovementRecordAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("simulation", "step", "sim_curr_time")
    list_filter = ("simulation",)
    search_fields = ("simulation__name",)
    ordering = ("simulation", "step")


@admin.register(ConceptNode)
class ConceptNodeAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "persona",
        "node_id",
        "node_type",
        "depth",
        "subject",
        "predicate",
        "object",
        "poignancy",
        "created",
    )
    list_filter = ("node_type", "persona__simulation")
    search_fields = ("persona__name", "subject", "predicate", "object", "description", "embedding_key")
    ordering = ("persona", "-created")


@admin.register(KeywordStrength)
class KeywordStrengthAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("persona", "keyword", "strength_type", "strength")
    list_filter = ("strength_type", "persona__simulation")
    search_fields = ("persona__name", "keyword")
    ordering = ("persona", "keyword")


@admin.register(SpatialMemory)
class SpatialMemoryAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("persona",)
    list_filter = ("persona__simulation",)
    search_fields = ("persona__name",)
    ordering = ("persona",)


@admin.register(RuntimeState)
class RuntimeStateAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("key", "updated_at")
    search_fields = ("key",)
    ordering = ("key",)


@admin.register(Demo)
class DemoAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("name", "maze_name", "step", "total_steps", "created_at")
    search_fields = ("name", "maze_name")
    ordering = ("-created_at",)


@admin.register(DemoMovement)
class DemoMovementAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("demo", "step")
    list_filter = ("demo",)
    search_fields = ("demo__name",)
    ordering = ("demo", "step")


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("conversation", "persona")
    list_filter = ("persona__simulation",)
    search_fields = ("persona__name",)
    ordering = ("conversation",)


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
