# Generated by Django 4.0.1 on 2022-01-06 13:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('produkcja', '0007_productiondoc_productionposition_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productionposition',
            name='quantity',
        ),
    ]
