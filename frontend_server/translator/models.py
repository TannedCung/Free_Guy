from django.db import models


class Map(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    preview_image_url = models.CharField(max_length=500, blank=True)
    maze_name = models.CharField(max_length=255)
    max_agents = models.IntegerField(default=25)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"


class Simulation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    fork_sim_code = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.DateTimeField(blank=True, null=True)
    curr_time = models.DateTimeField(blank=True, null=True)
    sec_per_step = models.IntegerField(blank=True, null=True)
    maze_name = models.CharField(max_length=255, blank=True, null=True)
    step = models.IntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"


class Persona(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="personas", db_index=True)
    name = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255, blank=True, default="")
    last_name = models.CharField(max_length=255, blank=True, default="")
    age = models.IntegerField(blank=True, null=True)
    innate = models.TextField(blank=True, default="")
    learned = models.TextField(blank=True, default="")
    currently = models.TextField(blank=True, default="")
    lifestyle = models.TextField(blank=True, default="")
    living_area = models.CharField(max_length=500, blank=True, default="")
    daily_plan_req = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    class Meta:
        unique_together = [("simulation", "name")]

    def __str__(self) -> str:
        return f"{self.name} ({self.simulation.name})"


class PersonaScratch(models.Model):
    persona = models.OneToOneField(Persona, on_delete=models.CASCADE, related_name="scratch")

    # Perception fields
    vision_r = models.IntegerField(default=8)
    att_bandwidth = models.IntegerField(default=8)
    retention = models.IntegerField(default=8)

    # Temporal fields
    curr_time = models.DateTimeField(blank=True, null=True)
    curr_tile = models.JSONField(default=list, blank=True)
    concept_forget = models.IntegerField(default=100)
    daily_reflection_time = models.IntegerField(default=180)
    daily_reflection_size = models.IntegerField(default=5)

    # Scoring fields
    overlap_reflect_th = models.IntegerField(default=4)
    kw_strg_event_reflect_th = models.IntegerField(default=10)
    kw_strg_thought_reflect_th = models.IntegerField(default=9)
    recency_w = models.FloatField(default=1.0)
    relevance_w = models.FloatField(default=1.0)
    importance_w = models.FloatField(default=1.0)
    recency_decay = models.FloatField(default=0.995)
    importance_trigger_max = models.IntegerField(default=150)
    importance_trigger_curr = models.IntegerField(default=150)
    importance_ele_n = models.IntegerField(default=0)
    thought_count = models.IntegerField(default=5)

    # Schedule fields
    daily_req = models.JSONField(default=list, blank=True)
    f_daily_schedule = models.JSONField(default=list, blank=True)
    f_daily_schedule_hourly_org = models.JSONField(default=list, blank=True)

    # Action fields
    act_address = models.CharField(max_length=500, blank=True, default="")
    act_start_time = models.DateTimeField(blank=True, null=True)
    act_duration = models.IntegerField(blank=True, null=True)
    act_description = models.TextField(blank=True, default="")
    act_pronunciatio = models.CharField(max_length=100, blank=True, default="")
    act_event = models.JSONField(default=list, blank=True)
    act_obj_description = models.TextField(blank=True, default="")
    act_obj_pronunciatio = models.CharField(max_length=100, blank=True, default="")
    act_obj_event = models.JSONField(default=list, blank=True)

    # Chat fields
    chatting_with = models.CharField(max_length=255, blank=True, null=True)
    chat = models.JSONField(blank=True, null=True)
    chatting_with_buffer = models.JSONField(default=dict, blank=True)
    chatting_end_time = models.DateTimeField(blank=True, null=True)
    act_path_set = models.BooleanField(default=False)
    planned_path = models.JSONField(default=list, blank=True)

    def __str__(self) -> str:
        return f"Scratch({self.persona.name})"


class EnvironmentState(models.Model):
    simulation = models.ForeignKey(
        Simulation, on_delete=models.CASCADE, related_name="environment_states", db_index=True
    )
    step = models.IntegerField()
    agent_positions = models.JSONField()

    class Meta:
        unique_together = [("simulation", "step")]
        indexes = [
            models.Index(fields=["simulation", "step"]),
        ]

    def __str__(self) -> str:
        return f"EnvironmentState({self.simulation.name}, step={self.step})"


class MovementRecord(models.Model):
    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="movement_records", db_index=True)
    step = models.IntegerField()
    sim_curr_time = models.DateTimeField(blank=True, null=True)
    persona_movements = models.JSONField()

    class Meta:
        unique_together = [("simulation", "step")]
        indexes = [
            models.Index(fields=["simulation", "step"]),
        ]

    def __str__(self) -> str:
        return f"MovementRecord({self.simulation.name}, step={self.step})"


class ConceptNode(models.Model):
    class NodeType(models.TextChoices):
        EVENT = "event", "Event"
        THOUGHT = "thought", "Thought"
        CHAT = "chat", "Chat"

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="concept_nodes", db_index=True)
    node_id = models.IntegerField()
    node_count = models.IntegerField(default=0)
    type_count = models.IntegerField(default=0)
    node_type = models.CharField(max_length=10, choices=NodeType.choices, default=NodeType.EVENT)
    depth = models.IntegerField(default=0)
    created = models.DateTimeField(blank=True, null=True)
    expiration = models.DateTimeField(blank=True, null=True)
    last_accessed = models.DateTimeField(blank=True, null=True)
    subject = models.CharField(max_length=255, blank=True, default="")
    predicate = models.CharField(max_length=255, blank=True, default="")
    object = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    embedding_key = models.CharField(max_length=255, blank=True, default="")
    poignancy = models.FloatField(default=0.0)
    keywords = models.JSONField(default=list, blank=True)
    filling = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["persona", "node_id"], name="unique_persona_node_id"),
        ]
        indexes = [
            models.Index(fields=["persona", "node_type"], name="cn_per_node_type_idx"),
            models.Index(fields=["persona", "subject"], name="cn_per_subject_idx"),
            models.Index(fields=["persona", "-created"], name="cn_per_created_idx"),
        ]

    def __str__(self) -> str:
        return f"ConceptNode({self.persona.name}, {self.node_type}, {self.node_id})"


class KeywordStrength(models.Model):
    class StrengthType(models.TextChoices):
        EVENT = "event", "Event"
        THOUGHT = "thought", "Thought"

    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name="keyword_strengths", db_index=True)
    keyword = models.CharField(max_length=255)
    strength_type = models.CharField(max_length=10, choices=StrengthType.choices)
    strength = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["persona", "keyword", "strength_type"],
                name="unique_persona_keyword_strength_type",
            ),
        ]

    def __str__(self) -> str:
        return f"KeywordStrength({self.persona.name}, {self.keyword}, {self.strength_type}={self.strength})"


class SpatialMemory(models.Model):
    persona = models.OneToOneField(Persona, on_delete=models.CASCADE, related_name="spatial_memory")
    tree = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"SpatialMemory({self.persona.name})"


class RuntimeState(models.Model):
    key = models.CharField(max_length=255, unique=True)
    value = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"RuntimeState({self.key})"


class Demo(models.Model):
    name = models.CharField(max_length=255, unique=True)
    fork_sim_code = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.DateTimeField(blank=True, null=True)
    curr_time = models.DateTimeField(blank=True, null=True)
    sec_per_step = models.IntegerField(blank=True, null=True)
    maze_name = models.CharField(max_length=255, blank=True, null=True)
    persona_names = models.JSONField(default=list, blank=True)
    step = models.IntegerField(default=0)
    total_steps = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Demo({self.name})"


class DemoMovement(models.Model):
    demo = models.ForeignKey(Demo, on_delete=models.CASCADE, related_name="movements", db_index=True)
    step = models.IntegerField()
    agent_movements = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["demo", "step"], name="unique_demomovement_demo_step"),
        ]

    def __str__(self) -> str:
        return f"DemoMovement({self.demo.name}, step={self.step})"


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(
        "Conversation", on_delete=models.CASCADE, related_name="participants_new", db_index=True
    )
    persona = models.ForeignKey(
        Persona, on_delete=models.CASCADE, related_name="conversation_participants", db_index=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["conversation", "persona"], name="unique_conversation_persona"),
        ]

    def __str__(self) -> str:
        return f"ConversationParticipant({self.persona.name} in {self.conversation_id})"


class Agent(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        IDLE = "idle", "Idle"
        SLEEPING = "sleeping", "Sleeping"

    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="agents", db_index=True)
    name = models.CharField(max_length=255)
    personality_traits = models.TextField(blank=True, default="")
    current_location = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    class Meta:
        unique_together = [("simulation", "name")]

    def __str__(self) -> str:
        return f"{self.name} ({self.simulation.name})"


class SimulationStep(models.Model):
    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="steps", db_index=True)
    step_number = models.PositiveIntegerField(db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    world_state = models.JSONField(default=dict)

    class Meta:
        ordering = ["step_number"]
        unique_together = [("simulation", "step_number")]

    def __str__(self) -> str:
        return f"{self.simulation.name} step {self.step_number}"


class AgentMemory(models.Model):
    class MemoryType(models.TextChoices):
        EVENT = "event", "Event"
        THOUGHT = "thought", "Thought"
        CHAT = "chat", "Chat"

    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="memories", db_index=True)
    memory_type = models.CharField(
        max_length=20,
        choices=MemoryType.choices,
        default=MemoryType.EVENT,
        db_index=True,
    )
    content = models.TextField()
    importance_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.agent.name} {self.memory_type}: {self.content[:50]}"


class Conversation(models.Model):
    simulation = models.ForeignKey(
        Simulation,
        on_delete=models.CASCADE,
        related_name="conversations",
        db_index=True,
    )
    participants = models.ManyToManyField(Agent, related_name="conversations", blank=True)
    started_at = models.DateTimeField(db_index=True)
    transcript = models.JSONField(default=list)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Conversation in {self.simulation.name} at {self.started_at}"
