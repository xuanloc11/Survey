from django.db import migrations


def disable_quiz_mode(apps, schema_editor):
    Survey = apps.get_model("surveys", "Survey")
    Question = apps.get_model("surveys", "Question")

    # Turn off quiz for all surveys
    Survey.objects.filter(is_quiz=True).update(is_quiz=False)

    # Clear correct answers everywhere (so UI/exports never show quiz data)
    Question.objects.exclude(correct_answers=[]).update(correct_answers=[])


class Migration(migrations.Migration):

    dependencies = [
        ("surveys", "0014_survey_soft_delete"),
    ]

    operations = [
        migrations.RunPython(disable_quiz_mode, migrations.RunPython.noop),
    ]


