# apps/caja/migrations/0003_metodopago_tipo.py
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("caja", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="metodopago",
            name="tipo",
            field=models.CharField(
                choices=[("CONTADO", "Contado"), ("CREDITO", "Crédito")],
                default="CONTADO",
                max_length=10,
                help_text=(
                    "CONTADO: requiere saldo en caja y genera egreso inmediato. "
                    "CREDITO: no afecta caja y genera una Cuenta por Pagar al proveedor."
                ),
            ),
        ),
        # Actualizar el método CRÉDITO que ya existe en la BD
        migrations.RunSQL(
            sql="UPDATE caja_metodopago SET tipo = 'CREDITO' WHERE nombre = 'CRÉDITO';",
            reverse_sql="UPDATE caja_metodopago SET tipo = 'CONTADO' WHERE nombre = 'CRÉDITO';",
        ),
    ]
