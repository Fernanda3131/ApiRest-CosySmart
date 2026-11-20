
import hashlib
from decimal import Decimal
from uuid import uuid4

from app.config.wompi import obtener_configuracion_wompi

"""
Descripción:
    Contiene las funciones auxiliares necesarias para
    preparar las solicitudes de pago de CosySmart mediante
    la integración con Wompi.

Responsabilidades:
    - Generar referencias únicas para los intentos de pago.
    - Convertir los valores monetarios a centavos.
    - Generar firmas de integridad para el checkout.
    - Utilizar la configuración de Wompi definida
      en el entorno del proyecto."""


def generar_referencia_pago(id_orden: int) -> str:
    """
    Genera una referencia única para cada intento de pago.
    """
    identificador = uuid4().hex[:16].upper()

    return f"COSY-{id_orden}-{identificador}"


def convertir_a_centavos(total: Decimal) -> int:
    """
    Convierte el total de la orden a centavos.
    """
    if total <= 0:
        raise ValueError("El valor del pago debe ser mayor que cero.")

    total_centavos = total * Decimal("100")

    if total_centavos != total_centavos.to_integral_value():
        raise ValueError(
            "El total contiene más de dos decimales."
        )

    return int(total_centavos)


def generar_firma_integridad(
    referencia: str,
    monto_centavos: int
) -> str:
    """
    Genera la firma SHA-256 requerida por Wompi Checkout.
    """
    configuracion = obtener_configuracion_wompi()

    cadena = (
        f"{referencia}"
        f"{monto_centavos}"
        f"COP"
        f"{configuracion['WOMPI_INTEGRITY_SECRET']}"
    )

    return hashlib.sha256(
        cadena.encode("utf-8")
    ).hexdigest()
