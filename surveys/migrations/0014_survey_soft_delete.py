from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("surveys", "0013_survey_one_response_only"),
    ]

    operations = [
        migrations.AddField(
            model_name="survey",
            name="is_deleted",
            field=models.BooleanField(default=False, verbose_name="Đã xóa (soft delete)"),
        ),
        migrations.AddField(
            model_name="survey",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Thời gian xóa"),
        ),
    ]


