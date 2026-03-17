from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("translator", "0010_alter_conceptnode_id_alter_conversation_id_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConceptNode",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("node_id", models.IntegerField()),
                ("node_count", models.IntegerField(default=0)),
                ("type_count", models.IntegerField(default=0)),
                (
                    "node_type",
                    models.CharField(
                        choices=[("event", "Event"), ("thought", "Thought"), ("chat", "Chat")],
                        default="event",
                        max_length=10,
                    ),
                ),
                ("depth", models.IntegerField(default=0)),
                ("created", models.DateTimeField(blank=True, null=True)),
                ("expiration", models.DateTimeField(blank=True, null=True)),
                ("last_accessed", models.DateTimeField(blank=True, null=True)),
                ("subject", models.CharField(blank=True, default="", max_length=255)),
                ("predicate", models.CharField(blank=True, default="", max_length=255)),
                ("object", models.CharField(blank=True, default="", max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("embedding_key", models.CharField(blank=True, default="", max_length=255)),
                ("poignancy", models.FloatField(default=0.0)),
                ("keywords", models.JSONField(blank=True, default=list)),
                ("filling", models.JSONField(blank=True, default=list)),
                (
                    "persona",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="concept_nodes",
                        to="translator.persona",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="KeywordStrength",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("keyword", models.CharField(max_length=255)),
                (
                    "strength_type",
                    models.CharField(
                        choices=[("event", "Event"), ("thought", "Thought")],
                        max_length=10,
                    ),
                ),
                ("strength", models.IntegerField(default=0)),
                (
                    "persona",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="keyword_strengths",
                        to="translator.persona",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="conceptnode",
            constraint=models.UniqueConstraint(fields=["persona", "node_id"], name="unique_persona_node_id"),
        ),
        migrations.AddIndex(
            model_name="conceptnode",
            index=models.Index(fields=["persona", "node_type"], name="conceptnode_persona_node_type_idx"),
        ),
        migrations.AddIndex(
            model_name="conceptnode",
            index=models.Index(fields=["persona", "subject"], name="conceptnode_persona_subject_idx"),
        ),
        migrations.AddIndex(
            model_name="conceptnode",
            index=models.Index(fields=["persona", "-created"], name="conceptnode_persona_created_idx"),
        ),
        migrations.AddConstraint(
            model_name="keywordstrength",
            constraint=models.UniqueConstraint(
                fields=["persona", "keyword", "strength_type"], name="unique_persona_keyword_strength_type"
            ),
        ),
    ]
