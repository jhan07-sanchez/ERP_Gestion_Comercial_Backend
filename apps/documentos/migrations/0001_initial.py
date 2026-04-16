# Generated manually for ERP documentos module

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ventas", "0001_initial"),
        ("compras", "0004_cuentaporpagar"),
    ]

    operations = [
        migrations.CreateModel(
            name="SecuenciaNumeracionDocumento",
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
                ("codigo", models.CharField(db_index=True, max_length=40, unique=True)),
                ("prefijo", models.CharField(default="DOC", max_length=20)),
                ("ultimo_numero", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Secuencia de documento",
                "verbose_name_plural": "Secuencias de documentos",
                "db_table": "documentos_secuencia",
            },
        ),
        migrations.CreateModel(
            name="Documento",
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
                    "tipo",
                    models.CharField(
                        choices=[
                            ("FACTURA_VENTA", "Factura de venta"),
                            ("TICKET_POS", "Ticket POS"),
                            ("FACTURA_COMPRA", "Factura / documento de compra"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                (
                    "estado",
                    models.CharField(
                        choices=[
                            ("EMITIDO", "Emitido"),
                            ("ANULADO", "Anulado"),
                        ],
                        db_index=True,
                        default="EMITIDO",
                        max_length=10,
                    ),
                ),
                (
                    "numero_interno",
                    models.CharField(
                        db_index=True,
                        help_text="Numeración interna ERP (no fiscal hasta integración DIAN).",
                        max_length=40,
                        unique=True,
                    ),
                ),
                (
                    "referencia_operacion",
                    models.CharField(
                        blank=True,
                        help_text="Número de venta o compra origen (ej. número factura venta, COMP-xxx).",
                        max_length=50,
                    ),
                ),
                ("subtotal", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("impuestos", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("total", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                (
                    "numero_fiscal",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                (
                    "prefijo_fiscal",
                    models.CharField(blank=True, max_length=20, null=True),
                ),
                ("resolucion", models.CharField(blank=True, max_length=100, null=True)),
                ("metadata", models.JSONField(blank=True, null=True)),
                ("fecha_emision", models.DateTimeField(auto_now_add=True)),
                (
                    "compra",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="documento_emitido",
                        to="compras.compra",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="documentos_emitidos",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "venta",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="documento_emitido",
                        to="ventas.venta",
                    ),
                ),
            ],
            options={
                "db_table": "documentos_documento",
                "ordering": ["-fecha_emision"],
            },
        ),
        migrations.CreateModel(
            name="DocumentoDetalle",
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
                ("orden", models.PositiveSmallIntegerField(default=0)),
                ("descripcion", models.CharField(max_length=300)),
                (
                    "producto_id",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                ("cantidad", models.DecimalField(decimal_places=4, max_digits=14)),
                ("precio_unitario", models.DecimalField(decimal_places=4, max_digits=14)),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=14)),
                (
                    "documento",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lineas",
                        to="documentos.documento",
                    ),
                ),
            ],
            options={
                "db_table": "documentos_documento_detalle",
                "ordering": ["documento", "orden"],
            },
        ),
        migrations.AddIndex(
            model_name="documento",
            index=models.Index(
                fields=["tipo", "fecha_emision"],
                name="documentos_d_tipo_fe_idx",
            ),
        ),
    ]
