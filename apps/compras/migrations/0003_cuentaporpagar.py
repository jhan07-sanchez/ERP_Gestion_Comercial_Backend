# apps/compras/migrations/0003_cuentaporpagar.py
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("compras", "0002_initial"),
        ("proveedores", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CuentaPorPagar",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "monto_total",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                        help_text="Monto original de la deuda",
                    ),
                ),
                (
                    "saldo_pendiente",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                        help_text="Cuánto falta por pagar",
                    ),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("PENDIENTE", "Pendiente"),
                            ("PARCIAL", "Parcial"),
                            ("PAGADO", "Pagado"),
                        ],
                        db_index=True,
                        default="PENDIENTE",
                        max_length=10,
                    ),
                ),
                (
                    "fecha_vencimiento",
                    models.DateField(
                        blank=True, null=True, help_text="Fecha límite de pago"
                    ),
                ),
                ("notas", models.TextField(blank=True, null=True)),
                ("fecha_creacion", models.DateTimeField(auto_now_add=True)),
                ("fecha_actualizacion", models.DateTimeField(auto_now=True)),
                (
                    "compra",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cuentas_por_pagar",
                        to="compras.compra",
                        help_text="Compra que originó esta deuda",
                    ),
                ),
                (
                    "proveedor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cuentas_por_pagar",
                        to="proveedores.proveedor",
                        help_text="Proveedor al que se le debe",
                    ),
                ),
            ],
            options={
                "verbose_name": "Cuenta por Pagar",
                "verbose_name_plural": "Cuentas por Pagar",
                "db_table": "cuentas_por_pagar",
                "ordering": ["-fecha_creacion"],
            },
        ),
        migrations.AddIndex(
            model_name="cuentaporpagar",
            index=models.Index(
                fields=["proveedor", "estado"], name="cpp_proveedor_estado_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="cuentaporpagar",
            index=models.Index(
                fields=["estado", "fecha_vencimiento"],
                name="cpp_estado_vencimiento_idx",
            ),
        ),
    ]
