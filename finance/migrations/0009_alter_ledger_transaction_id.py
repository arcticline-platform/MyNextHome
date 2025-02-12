# Generated by Django 5.1.3 on 2024-12-05 17:16

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0008_alter_ledger_transaction_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ledger',
            name='transaction_id',
            field=models.UUIDField(default=uuid.UUID('fece81a0-018e-46f8-92f7-617067d8ee52'), editable=False, unique=True, verbose_name='Transaction Id'),
        ),
    ]
