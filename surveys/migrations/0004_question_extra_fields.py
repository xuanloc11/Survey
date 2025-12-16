from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('surveys', '0003_remove_choice_question_question_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='media_url',
            field=models.TextField(blank=True, default='', verbose_name='Media URL (ảnh/video)'),
        ),
        migrations.AddField(
            model_name='question',
            name='subtitle',
            field=models.TextField(blank=True, default='', verbose_name='Mô tả/Phụ đề'),
        ),
        migrations.AlterField(
            model_name='question',
            name='question_type',
            field=models.CharField(choices=[('text', 'Câu hỏi tự luận'), ('single', 'Chọn một đáp án'), ('multiple', 'Chọn nhiều đáp án'), ('section', 'Tiêu đề/phần'), ('description', 'Mô tả'), ('image', 'Hình ảnh'), ('video', 'Video')], default='single', max_length=20, verbose_name='Loại câu hỏi'),
        ),
    ]

