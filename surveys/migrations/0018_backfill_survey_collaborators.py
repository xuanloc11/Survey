from django.db import migrations


def backfill_owner_roles(apps, schema_editor):
    Survey = apps.get_model("surveys", "Survey")
    SurveyCollaborator = apps.get_model("surveys", "SurveyCollaborator")

    # Ensure each existing survey creator has an owner role row
    for survey in Survey.objects.all().only("id", "creator_id"):
        if not survey.creator_id:
            continue
        SurveyCollaborator.objects.get_or_create(
            survey_id=survey.id,
            user_id=survey.creator_id,
            defaults={"role": "owner"},
        )


def noop_reverse(apps, schema_editor):
    # No reverse migration: keep created rows
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("surveys", "0017_surveycollaborator"),
    ]

    operations = [
        migrations.RunPython(backfill_owner_roles, noop_reverse),
    ]


