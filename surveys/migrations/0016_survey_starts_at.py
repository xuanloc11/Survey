from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("surveys", "0015_disable_quiz_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="survey",
            name="starts_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Bắt đầu vào"),
        ),
    ]


