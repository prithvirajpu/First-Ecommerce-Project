# Generated by Django 5.1.7 on 2025-06-09 05:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_app', '0009_remove_brand_status_brand_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
