import os
from dotenv import load_dotenv

load_dotenv()

# Configuración de conexión desarrollada con la pasarela de pagos Wompi


def obtener_configuracion_wompi():
    public_key = os.getenv("WOMPI_PUBLIC_KEY", "").strip()
    private_key = os.getenv("WOMPI_PRIVATE_KEY", "").strip()
    integrity_secret = os.getenv("WOMPI_INTEGRITY_SECRET", "").strip()
    events_secret = os.getenv("WOMPI_EVENTS_SECRET", "").strip()
    base_url = os.getenv(
        "WOMPI_BASE_URL",
        "https://sandbox.wompi.co/v1"
    ).strip()

    credenciales = {
        "WOMPI_PUBLIC_KEY": public_key,
        "WOMPI_PRIVATE_KEY": private_key,
        "WOMPI_INTEGRITY_SECRET": integrity_secret,
        "WOMPI_EVENTS_SECRET": events_secret,
    }

    faltantes = [
        nombre
        for nombre, valor in credenciales.items()
        if not valor
    ]

    if faltantes:
        raise ValueError(
            "Faltan variables de entorno de Wompi: "
            + ", ".join(faltantes)
        )

    prefijos = {
        "WOMPI_PUBLIC_KEY": "pub_test_",
        "WOMPI_PRIVATE_KEY": "prv_test_",
        "WOMPI_INTEGRITY_SECRET": "test_integrity_",
        "WOMPI_EVENTS_SECRET": "test_events_",
    }

    for nombre, prefijo in prefijos.items():
        if not credenciales[nombre].startswith(prefijo):
            raise ValueError(
                f"{nombre} no corresponde a una credencial Sandbox."
            )

    if base_url != "https://sandbox.wompi.co/v1":
        raise ValueError(
            "La URL configurada no corresponde al entorno Sandbox."
        )

    return {
        **credenciales,
        "WOMPI_BASE_URL": base_url,
    }
