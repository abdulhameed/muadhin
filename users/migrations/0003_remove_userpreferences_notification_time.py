# Generated by Django 4.2.6 on 2023-10-10 18:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_customuser_city_alter_customuser_timezone_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userpreferences',
            name='notification_time',
        ),
    ]
