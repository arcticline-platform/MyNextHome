# Generated by Django 5.1.3 on 2024-11-26 20:21

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0003_alter_ledger_transaction_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='paymentmethods',
            old_name='phonnumber',
            new_name='phone_number',
        ),
        migrations.RenameField(
            model_name='payments',
            old_name='is_complete',
            new_name='is_successful',
        ),
        migrations.RenameField(
            model_name='refunds',
            old_name='is_complete',
            new_name='is_successful',
        ),
        migrations.AddField(
            model_name='payments',
            name='error',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='ledger',
            name='transaction_id',
            field=models.UUIDField(default=uuid.UUID('cb35ec8c-5a5d-4b4e-a225-d487b0373390'), editable=False, unique=True, verbose_name='Transaction Id'),
        ),
    ]
