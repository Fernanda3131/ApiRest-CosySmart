
import hashlib
import hmac
import os
import secrets

from datetime import datetime, timedelta, timezone

"""
Descripción:
    Gestiona la lógica de recuperación y restablecimiento
    de contraseñas de los usuarios de CosySmart.

Responsabilidades:
    - Procesar solicitudes de recuperación de contraseña.
    - Verificar la existencia y elegibilidad de la cuenta.
    - Generar mecanismos temporales de verificación,
      cuando corresponda.
    - Validar códigos o tokens de recuperación.
    - Controlar la vigencia y el uso de los mecanismos
      de recuperación.
    - Actualizar la contraseña del usuario.
    - Aplicar hashing seguro antes de almacenar
      la nueva contraseña."""


def obtener_secreto():
    secreto = os.getenv("RESET_CODE_SECRET")

    if not secreto:
        raise RuntimeError(
            "No está configurado RESET_CODE_SECRET"
        )

    return secreto.encode("utf-8")


def calcular_hash(valor: str, tipo: str) -> str:
    contenido = f"{tipo}:{valor}".encode("utf-8")

    return hmac.new(
        obtener_secreto(),
        contenido,
        hashlib.sha256
    ).hexdigest()


def generar_codigo() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def generar_token_recuperacion() -> str:
    return secrets.token_urlsafe(32)


def validar_hash(valor: str, hash_guardado: str, tipo: str) -> bool:
    hash_calculado = calcular_hash(valor, tipo)

    return hmac.compare_digest(
        hash_calculado,
        hash_guardado
    )


def obtener_hora_actual():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def obtener_expiracion_codigo():
    return obtener_hora_actual() + timedelta(minutes=10)


def obtener_expiracion_token():
    return obtener_hora_actual() + timedelta(minutes=5)
