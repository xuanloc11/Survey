from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('surveys', '0007_survey_max_responses'),
    ]

    operations = [
        migrations.AddField(
            model_name='survey',
            name='password',
            field=models.CharField(blank=True, help_text='Để trống nếu không yêu cầu mật khẩu', max_length=128, verbose_name='Mật khẩu khảo sát'),
        ),
    ]

