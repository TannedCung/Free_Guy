# Generated for US-004 - Create PersonaScratch model

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("translator", "0007_simulation_extra_fields_persona"),
    ]

    operations = [
        migrations.CreateModel(
            name="PersonaScratch",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                # Perception fields
                ("vision_r", models.IntegerField(default=8)),
                ("att_bandwidth", models.IntegerField(default=8)),
                ("retention", models.IntegerField(default=8)),
                # Temporal fields
                ("curr_time", models.DateTimeField(blank=True, null=True)),
                ("curr_tile", models.JSONField(blank=True, default=list)),
                ("concept_forget", models.IntegerField(default=100)),
                ("daily_reflection_time", models.IntegerField(default=180)),
                ("daily_reflection_size", models.IntegerField(default=5)),
                # Scoring fields
                ("overlap_reflect_th", models.IntegerField(default=4)),
                ("kw_strg_event_reflect_th", models.IntegerField(default=10)),
                ("kw_strg_thought_reflect_th", models.IntegerField(default=9)),
                ("recency_w", models.FloatField(default=1.0)),
                ("relevance_w", models.FloatField(default=1.0)),
                ("importance_w", models.FloatField(default=1.0)),
                ("recency_decay", models.FloatField(default=0.995)),
                ("importance_trigger_max", models.IntegerField(default=150)),
                ("importance_trigger_curr", models.IntegerField(default=150)),
                ("importance_ele_n", models.IntegerField(default=0)),
                ("thought_count", models.IntegerField(default=5)),
                # Schedule fields
                ("daily_req", models.JSONField(blank=True, default=list)),
                ("f_daily_schedule", models.JSONField(blank=True, default=list)),
                ("f_daily_schedule_hourly_org", models.JSONField(blank=True, default=list)),
                # Action fields
                ("act_address", models.CharField(blank=True, default="", max_length=500)),
                ("act_start_time", models.DateTimeField(blank=True, null=True)),
                ("act_duration", models.IntegerField(blank=True, null=True)),
                ("act_description", models.TextField(blank=True, default="")),
                ("act_pronunciatio", models.CharField(blank=True, default="", max_length=100)),
                ("act_event", models.JSONField(blank=True, default=list)),
                ("act_obj_description", models.TextField(blank=True, default="")),
                ("act_obj_pronunciatio", models.CharField(blank=True, default="", max_length=100)),
                ("act_obj_event", models.JSONField(blank=True, default=list)),
                # Chat fields
                ("chatting_with", models.CharField(blank=True, max_length=255, null=True)),
                ("chat", models.JSONField(blank=True, null=True)),
                ("chatting_with_buffer", models.JSONField(blank=True, default=dict)),
                ("chatting_end_time", models.DateTimeField(blank=True, null=True)),
                ("act_path_set", models.BooleanField(default=False)),
                ("planned_path", models.JSONField(blank=True, default=list)),
                # FK
                (
                    "persona",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scratch",
                        to="translator.persona",
                    ),
                ),
            ],
        ),
    ]
