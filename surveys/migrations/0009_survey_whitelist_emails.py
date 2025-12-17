from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('surveys', '0008_survey_password'),
    ]

    operations = [
        migrations.AddField(
            model_name='survey',
            name='whitelist_emails',
            field=models.TextField(blank=True, default='', help_text='Nhập danh sách email (mỗi dòng một email) được phép tham gia/export', verbose_name='Danh sách email được phép'),
        ),
    ]

