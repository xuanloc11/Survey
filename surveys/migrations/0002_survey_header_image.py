from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('surveys', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='survey',
            name='header_image',
            field=models.ImageField(
                upload_to='survey_headers/',
                blank=True,
                null=True,
                verbose_name='Ảnh tiêu đề'
            ),
        ),
    ]


