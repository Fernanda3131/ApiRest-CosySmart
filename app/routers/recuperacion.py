
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.usuario import Usuario
from app.models.recuperacion_contrasena import RecuperacionContrasena

from app.schemas.recuperacion import (
    SolicitudRecuperacion,
    VerificarCodigoRequest,
    RestablecerContrasenaRequest
)

from app.services.correo import enviar_codigo_recuperacion

from app.services.recuperacion import (
    generar_codigo,
    generar_token_recuperacion,
    calcular_hash,
    validar_hash,
    obtener_hora_actual,
    obtener_expiracion_codigo,
    obtener_expiracion_token
)

from app.services.auth import pwd_context


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["Recuperación de contraseña"]
)


MENSAJE_SOLICITUD = (
    "Si el correo está registrado y la cuenta está activa, "
    "recibirás instrucciones para recuperar tu contraseña."
)


@router.post("/recuperar")
async def solicitar_recuperacion(
    datos: SolicitudRecuperacion,
    db: Session = Depends(get_db)
):

    correo = datos.correo.strip().lower()

    usuario = (
        db.query(Usuario)
        .filter(
            Usuario.Correo == correo,
            Usuario.Estado == "ACTIVO"
        )
        .first()
    )

    # Respuesta genérica para no revelar si el correo existe.
    if not usuario:
        return {"mensaje": MENSAJE_SOLICITUD}

    codigo = generar_codigo()

    # Invalidar solicitudes anteriores sin usar.
    solicitudes_anteriores = (
        db.query(RecuperacionContrasena)
        .filter(
            RecuperacionContrasena.IdUsuario == usuario.IdUsuario,
            RecuperacionContrasena.Usado == False
        )
        .all()
    )

    for solicitud in solicitudes_anteriores:
        solicitud.Usado = True

    nueva_solicitud = RecuperacionContrasena(
        IdUsuario=usuario.IdUsuario,
        CodigoHash=calcular_hash(codigo, "codigo"),
        FechaExpiracion=obtener_expiracion_codigo(),
        Intentos=0,
        Usado=False,
        FechaCreacion=obtener_hora_actual()
    )

    db.add(nueva_solicitud)
    db.commit()

    try:
        await enviar_codigo_recuperacion(
            destinatario=usuario.Correo,
            codigo=codigo
        )

    except Exception:
        logger.exception(
            "No se pudo enviar el correo de recuperación."
        )

        nueva_solicitud.Usado = True
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible enviar el correo. Intenta nuevamente."
        )

    return {"mensaje": MENSAJE_SOLICITUD}


@router.post("/verificar-codigo")
def verificar_codigo(
    datos: VerificarCodigoRequest,
    db: Session = Depends(get_db)
):

    correo = datos.correo.strip().lower()

    usuario = (
        db.query(Usuario)
        .filter(
            Usuario.Correo == correo,
            Usuario.Estado == "ACTIVO"
        )
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido o expirado."
        )

    solicitud = (
        db.query(RecuperacionContrasena)
        .filter(
            RecuperacionContrasena.IdUsuario == usuario.IdUsuario,
            RecuperacionContrasena.Usado == False
        )
        .order_by(
            RecuperacionContrasena.FechaCreacion.desc()
        )
        .first()
    )

    ahora = obtener_hora_actual()

    if (
        not solicitud
        or solicitud.FechaExpiracion <= ahora
        or solicitud.Intentos >= 5
        or solicitud.TokenRestablecimientoHash is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido o expirado."
        )

    solicitud.Intentos += 1

    codigo_valido = validar_hash(
        datos.codigo,
        solicitud.CodigoHash,
        "codigo"
    )

    if not codigo_valido:
        if solicitud.Intentos >= 5:
            solicitud.Usado = True

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código inválido o expirado."
        )

    token = generar_token_recuperacion()

    solicitud.TokenRestablecimientoHash = calcular_hash(
        token,
        "token"
    )

    solicitud.TokenExpiracion = obtener_expiracion_token()
    solicitud.FechaVerificacion = ahora

    db.commit()

    return {
        "mensaje": "Código verificado correctamente.",
        "token": token
    }


@router.post("/restablecer-contrasena")
def restablecer_contrasena(
    datos: RestablecerContrasenaRequest,
    db: Session = Depends(get_db)
):

    hash_token = calcular_hash(
        datos.token,
        "token"
    )

    ahora = obtener_hora_actual()

    solicitud = (
        db.query(RecuperacionContrasena)
        .filter(
            RecuperacionContrasena.TokenRestablecimientoHash == hash_token,
            RecuperacionContrasena.Usado == False
        )
        .order_by(
            RecuperacionContrasena.FechaCreacion.desc()
        )
        .first()
    )

    if (
        not solicitud
        or solicitud.TokenExpiracion is None
        or solicitud.TokenExpiracion <= ahora
        or solicitud.FechaVerificacion is None
        or solicitud.Intentos > 5
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El proceso de recuperación no es válido o ha expirado."
        )

    usuario = (
        db.query(Usuario)
        .filter(
            Usuario.IdUsuario == solicitud.IdUsuario,
            Usuario.Estado == "ACTIVO"
        )
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fue posible restablecer la contraseña."
        )

    usuario.Contrasena = pwd_context.hash(
        datos.nueva_contrasena
    )

    solicitud.Usado = True
    solicitud.TokenRestablecimientoHash = None

    db.commit()

    return {
        "mensaje": "La contraseña se ha actualizado correctamente."
    }
