
import base64
import hashlib
import secrets
from uuid import UUID

from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.exceptions import InvalidSignature

from sqlalchemy.orm import Session
from sqlalchemy import update

from fastapi import HTTPException, status

from app.models.dispositivo_usuario import DispositivoUsuario
from app.models.desafio_biometrico import DesafioBiometrico


ALGORITMO_PERMITIDO = "ECDSA-P256-SHA256"
DURACION_DESAFIO_MINUTOS = 2


def fecha_utc():
    """
    Devuelve la fecha UTC sin zona horaria.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def codificar_base64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode("utf-8").rstrip("=")


def decodificar_base64(valor: str) -> bytes:
    try:
        valor += "=" * (-len(valor) % 4)
        return base64.b64decode(
            valor,
            altchars=b"-_",
            validate=True
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El contenido Base64 no es válido"
        )


def validar_clave_publica(clave_publica: str):

    try:
        clave = serialization.load_pem_public_key(
            clave_publica.encode("utf-8")
        )

        if not isinstance(clave, ec.EllipticCurvePublicKey):
            raise ValueError("La clave no es ECDSA")

        if not isinstance(clave.curve, ec.SECP256R1):
            raise ValueError("La curva debe ser P-256")

        return clave

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="La clave pública no es válida para ECDSA P-256"
        )


def registrar_dispositivo(
    db: Session,
    id_usuario: int,
    nombre_dispositivo: str,
    clave_publica: str,
    algoritmo: str
):

    if algoritmo != ALGORITMO_PERMITIDO:
        raise HTTPException(
            status_code=400,
            detail="Algoritmo criptográfico no permitido"
        )

    validar_clave_publica(clave_publica)

    dispositivo = DispositivoUsuario(
        IdUsuario=id_usuario,
        NombreDispositivo=nombre_dispositivo,
        ClavePublica=clave_publica,
        Algoritmo=ALGORITMO_PERMITIDO,
        BiometriaHabilitada=True,
        Estado="ACTIVO"
    )

    try:
        db.add(dispositivo)
        db.commit()
        db.refresh(dispositivo)

        return dispositivo

    except Exception:
        db.rollback()
        raise


def generar_desafio(
    db: Session,
    id_usuario: int,
    id_dispositivo: int
):

    dispositivo = (
        db.query(DispositivoUsuario)
        .filter(
            DispositivoUsuario.IdDispositivo == id_dispositivo,
            DispositivoUsuario.IdUsuario == id_usuario,
            DispositivoUsuario.Estado == "ACTIVO",
            DispositivoUsuario.BiometriaHabilitada == 1
        )
        .first()
    )

    if not dispositivo:
        raise HTTPException(
            status_code=404,
            detail="Dispositivo no encontrado o no autorizado"
        )

    nonce = secrets.token_bytes(32)
    nonce_hash = hashlib.sha256(nonce).digest()

    ahora = fecha_utc()
    expiracion = ahora + timedelta(
        minutes=DURACION_DESAFIO_MINUTOS
    )

    desafio = DesafioBiometrico(
        IdDispositivo=dispositivo.IdDispositivo,
        NonceHash=nonce_hash,
        FechaCreacion=ahora,
        FechaExpiracion=expiracion
    )

    try:
        db.add(desafio)
        db.commit()
        db.refresh(desafio)

    except Exception:
        db.rollback()
        raise

    return {
        "ChallengeId": desafio.ChallengeId,
        "Nonce": codificar_base64(nonce),
        "FechaExpiracion": expiracion
    }


def construir_mensaje_firma(
    challenge_id: UUID,
    id_credencial: UUID,
    nonce: bytes
) -> bytes:
    """
    Construye el mensaje que Android debe firmar.
    """

    partes = [
        b"COSYSMART|BIOMETRIA_LOGIN|V1",
        str(challenge_id).lower().encode("ascii"),
        str(id_credencial).lower().encode("ascii"),
        nonce
    ]

    return b"\n".join(partes)


def verificar_firma(
    db: Session,
    id_usuario: int,
    id_dispositivo: int,
    challenge_id: UUID,
    nonce_base64: str,
    firma_base64: str,
    id_credencial: UUID
):

    dispositivo = (
        db.query(DispositivoUsuario)
        .filter(
            DispositivoUsuario.IdDispositivo == id_dispositivo,
            DispositivoUsuario.IdUsuario == id_usuario,
            DispositivoUsuario.IdCredencial == id_credencial,
            DispositivoUsuario.Estado == "ACTIVO",
            DispositivoUsuario.BiometriaHabilitada == 1
        )
        .first()
    )

    if not dispositivo:
        raise HTTPException(
            status_code=403,
            detail="El dispositivo no está autorizado"
        )

    desafio = (
        db.query(DesafioBiometrico)
        .filter(
            DesafioBiometrico.ChallengeId == challenge_id,
            DesafioBiometrico.IdDispositivo == id_dispositivo,
            DesafioBiometrico.FechaUtilizacion.is_(None)
        )
        .first()
    )

    if not desafio:
        raise HTTPException(
            status_code=401,
            detail="Desafío inexistente o ya utilizado"
        )

    ahora = fecha_utc()

    if desafio.FechaExpiracion <= ahora:
        raise HTTPException(
            status_code=401,
            detail="El desafío ha expirado"
        )

    nonce = decodificar_base64(nonce_base64)
    firma = decodificar_base64(firma_base64)

    if len(nonce) != 32:
        raise HTTPException(
            status_code=400,
            detail="El desafío tiene un formato incorrecto"
        )

    hash_recibido = hashlib.sha256(nonce).digest()

    if not secrets.compare_digest(
        hash_recibido,
        desafio.NonceHash
    ):
        raise HTTPException(
            status_code=401,
            detail="El desafío no coincide"
        )

    mensaje = construir_mensaje_firma(
        challenge_id,
        id_credencial,
        nonce
    )

    clave_publica = validar_clave_publica(
        dispositivo.ClavePublica
    )

    try:
        clave_publica.verify(
            firma,
            mensaje,
            ec.ECDSA(hashes.SHA256())
        )

    except InvalidSignature:
        raise HTTPException(
            status_code=401,
            detail="La firma digital no es válida"
        )

    resultado = db.execute(
        update(DesafioBiometrico)
        .where(
            DesafioBiometrico.IdDesafio == desafio.IdDesafio,
            DesafioBiometrico.FechaUtilizacion.is_(None),
            DesafioBiometrico.FechaExpiracion > ahora
        )
        .values(FechaUtilizacion=ahora)
    )

    if resultado.rowcount != 1:
        db.rollback()
        raise HTTPException(
            status_code=401,
            detail="El desafío ya fue utilizado o expiró"
        )

    dispositivo.UltimoAcceso = ahora

    try:
        db.commit()
        db.refresh(dispositivo)

    except Exception:
        db.rollback()
        raise

    return dispositivo


def revocar_dispositivo(
    db: Session,
    id_usuario: int,
    id_dispositivo: int
):

    dispositivo = (
        db.query(DispositivoUsuario)
        .filter(
            DispositivoUsuario.IdDispositivo == id_dispositivo,
            DispositivoUsuario.IdUsuario == id_usuario,
            DispositivoUsuario.Estado == "ACTIVO"
        )
        .first()
    )

    if not dispositivo:
        raise HTTPException(
            status_code=404,
            detail="Dispositivo no encontrado"
        )

    ahora = fecha_utc()

    dispositivo.Estado = "REVOCADO"
    dispositivo.BiometriaHabilitada = False
    dispositivo.FechaRevocacion = ahora

    try:
        db.commit()
        db.refresh(dispositivo)

    except Exception:
        db.rollback()
        raise

    return dispositivo
