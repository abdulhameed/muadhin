# Generated by Django 4.2.6 on 2023-10-28 14:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_remove_userpreferences_location_customuser_country_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='timezone',
            field=models.CharField(default='Africa/Lagos', max_length=100),
        ),
    ]