# Generated by Django 5.2.1 on 2025-05-24 17:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parking', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='parkinglot',
            name='maps_link',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='booking',
            name='vehicle_number',
            field=models.CharField(max_length=12),
        ),
    ]
