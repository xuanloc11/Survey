from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('surveys', '0006_question_correct_answers_question_score'),
    ]

    operations = [
        migrations.AddField(
            model_name='survey',
            name='max_responses',
            field=models.PositiveIntegerField(blank=True, help_text='Để trống nếu không giới hạn số lượt làm khảo sát', null=True, verbose_name='Giới hạn số phản hồi'),
        ),
    ]

