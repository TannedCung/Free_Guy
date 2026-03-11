from django.db import models


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
