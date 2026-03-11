# Generated for US-007 - Create SpatialMemory, RuntimeState, Demo, DemoMovement, and Conversation models

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("translator", "0011_conceptnode_keywordstrength"),
    ]

    operations = [
        migrations.CreateModel(
            name="SpatialMemory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("tree", models.JSONField(blank=True, default=dict)),
                (
                    "persona",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="spatial_memory",
                        to="translator.persona",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="RuntimeState",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("key", models.CharField(max_length=255, unique=True)),
                ("value", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Demo",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("name", models.CharField(max_length=255, unique=True)),
                ("fork_sim_code", models.CharField(blank=True, max_length=255, null=True)),
                ("start_date", models.DateTimeField(blank=True, null=True)),
                ("curr_time", models.DateTimeField(blank=True, null=True)),
                ("sec_per_step", models.IntegerField(blank=True, null=True)),
                ("maze_name", models.CharField(blank=True, max_length=255, null=True)),
                ("persona_names", models.JSONField(blank=True, default=list)),
                ("step", models.IntegerField(default=0)),
                ("total_steps", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="DemoMovement",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("step", models.IntegerField()),
                ("agent_movements", models.JSONField()),
                (
                    "demo",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="movements",
                        to="translator.demo",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="demomovement",
            constraint=models.UniqueConstraint(
                fields=["demo", "step"], name="unique_demomovement_demo_step"
            ),
        ),
        migrations.CreateModel(
            name="ConversationParticipant",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "conversation",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participants_new",
                        to="translator.conversation",
                    ),
                ),
                (
                    "persona",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="conversation_participants",
                        to="translator.persona",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="conversationparticipant",
            constraint=models.UniqueConstraint(
                fields=["conversation", "persona"], name="unique_conversation_persona"
            ),
        ),
    ]
