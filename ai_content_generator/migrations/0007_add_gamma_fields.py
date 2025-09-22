# Generated manually for Gamma editor integration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_content_generator', '0006_alter_generatedcontent_conversation'),
    ]

    operations = [
        migrations.AddField(
            model_name='generatedcontent',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='generatedcontent',
            name='content_type',
            field=models.CharField(choices=[('html', 'HTML'), ('gamma', 'Gamma Blocks'), ('scorm', 'SCORM Package')], default='html', max_length=50),
        ),
        migrations.AddField(
            model_name='generatedcontent',
            name='gamma_blocks',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='generatedcontent',
            name='gamma_document',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='generatedcontent',
            name='html_content',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='generatedcontent',
            name='css_content',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='generatedcontent',
            name='js_content',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='generatedcontent',
            name='grapesjs_components',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
