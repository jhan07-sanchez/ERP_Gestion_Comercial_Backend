# apps/categorias/migrations/0001_initial.py
"""
Migración inicial para la app Categorías.

Usa SeparateDatabaseAndState para registrar el modelo Categoria
en esta app sin crear una tabla nueva (ya existe 'categorias').
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='Categoria',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('nombre', models.CharField(max_length=100, unique=True)),
                        ('descripcion', models.TextField(blank=True, null=True)),
                        ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                        ('fecha_actualizacion', models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        'verbose_name': 'Categoría',
                        'verbose_name_plural': 'Categorías',
                        'db_table': 'categorias',
                    },
                ),
            ],
            database_operations=[],  # No tocar la BD, la tabla ya existe
        ),
    ]
