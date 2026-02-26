# apps/categorias/apps.py
from django.apps import AppConfig


class CategoriasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.categorias'
    verbose_name = 'Categorías'
