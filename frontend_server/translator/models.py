from django.db import models


class Simulation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"


class Agent(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        IDLE = "idle", "Idle"
        SLEEPING = "sleeping", "Sleeping"

    simulation = models.ForeignKey(
        Simulation, on_delete=models.CASCADE, related_name="agents", db_index=True
    )
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
    simulation = models.ForeignKey(
        Simulation, on_delete=models.CASCADE, related_name="steps", db_index=True
    )
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

    agent = models.ForeignKey(
        Agent, on_delete=models.CASCADE, related_name="memories", db_index=True
    )
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
