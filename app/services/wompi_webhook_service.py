
import hashlib
import hmac

from app.config.wompi import obtener_configuracion_wompi


def obtener_valor_anidado(datos: dict, ruta: str):
    """
    Obtiene un valor usando rutas como transaction.id.
    Las propiedades de Wompi apuntan al objeto data.
    """
    valor = datos

    for parte in ruta.split("."):
        if not isinstance(valor, dict) or parte not in valor:
            raise ValueError(
                f"No se encontró la propiedad del evento: {ruta}"
            )

        valor = valor[parte]

    if valor is None:
        raise ValueError(
            f"La propiedad del evento está vacía: {ruta}"
        )

    return valor


def verificar_firma_evento(evento: dict) -> bool:
    configuracion = obtener_configuracion_wompi()

    firma = evento.get("signature")
    datos = evento.get("data")
    timestamp = evento.get("timestamp")

    if not isinstance(firma, dict):
        return False

    if not isinstance(datos, dict):
        return False

    propiedades = firma.get("properties")
    checksum_recibido = firma.get("checksum")

    if (
        not isinstance(propiedades, list)
        or not propiedades
        or not isinstance(checksum_recibido, str)
    ):
        return False

    if not isinstance(timestamp, (int, str)) or isinstance(timestamp, bool):
        return False

    try:
        valores = "".join(
            str(obtener_valor_anidado(datos, propiedad))
            for propiedad in propiedades
        )

        cadena = (
            valores
            + str(timestamp)
            + configuracion["WOMPI_EVENTS_SECRET"]
        )

        checksum_calculado = hashlib.sha256(
            cadena.encode("utf-8")
        ).hexdigest()

        return hmac.compare_digest(
            checksum_calculado.lower(),
            checksum_recibido.lower()
        )

    except (ValueError, TypeError):
        return False
