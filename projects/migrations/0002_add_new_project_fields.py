# Generated migration for new project fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='clarity',
            field=models.CharField(blank=True, help_text='Project clarity description', max_length=200),
        ),
        migrations.AddField(
            model_name='project',
            name='timeline',
            field=models.CharField(blank=True, help_text='Project timeline information', max_length=200),
        ),
        migrations.AddField(
            model_name='project',
            name='t_code',
            field=models.CharField(blank=True, help_text='T/code identifier', max_length=50),
        ),
    ]
