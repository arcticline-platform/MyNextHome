# Generated by Django 5.1.3 on 2024-11-27 11:44

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0004_rename_phonnumber_paymentmethods_phone_number_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='payments',
            old_name='is_processing',
            new_name='is_processed',
        ),
        migrations.AlterField(
            model_name='ledger',
            name='transaction_id',
            field=models.UUIDField(default=uuid.UUID('65d69679-072c-424c-a1ff-f12c403dc693'), editable=False, unique=True, verbose_name='Transaction Id'),
        ),
    ]
