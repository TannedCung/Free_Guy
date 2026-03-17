"""Rename ConceptNode indexes to fit the 30-character limit enforced by Django's
system check (models.E034). The old names exceeded 30 characters."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("translator", "0012_spatialmemory_runtimestate_demo_demomovement_conversationparticipant"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="conceptnode",
            old_name="conceptnode_persona_node_type_idx",
            new_name="cn_per_node_type_idx",
        ),
        migrations.RenameIndex(
            model_name="conceptnode",
            old_name="conceptnode_persona_subject_idx",
            new_name="cn_per_subject_idx",
        ),
        migrations.RenameIndex(
            model_name="conceptnode",
            old_name="conceptnode_persona_created_idx",
            new_name="cn_per_created_idx",
        ),
    ]
