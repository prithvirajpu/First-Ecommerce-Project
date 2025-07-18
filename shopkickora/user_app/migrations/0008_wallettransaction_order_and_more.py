# Generated by Django 5.2.1 on 2025-07-10 05:44

import django.db.models.deletion
import user_app.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_app', '0007_remove_wallet_created_at_alter_wallet_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='wallettransaction',
            name='order',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='user_app.order'),
        ),
        migrations.AddField(
            model_name='wallettransaction',
            name='transaction_id',
            field=models.CharField(default=user_app.models.generate_transaction_id, editable=False, max_length=50, unique=True),
        ),
    ]
