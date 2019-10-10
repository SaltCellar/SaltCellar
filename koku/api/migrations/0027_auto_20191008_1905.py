# Generated by Django 2.2.4 on 2019-10-08 19:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0026_auto_20191003_2339'),
    ]

    operations = [
        migrations.AddField(
            model_name='sources',
            name='pending_update',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='dataexportrequest',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('waiting', 'Waiting'), ('complete', 'Complete'), ('error', 'Error')], default='pending', max_length=32),
        ),
    ]