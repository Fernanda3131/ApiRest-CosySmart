
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.config.database import get_db

from app.models.usuario import Usuario
from app.models.usuario_rol import UsuarioRol
from app.models.dispositivo_usuario import DispositivoUsuario

from app.schemas.biometria import (
    DispositivoRegistrar,
    DispositivoRespuesta,
    BiometriaDesafioRequest,
    DesafioRespuesta,
    BiometriaVerificar,
    BiometriaLoginRespuesta
)

from app.services.biometria import (
    registrar_dispositivo,
    generar_desafio,
    verificar_firma,
    revocar_dispositivo
)

from app.services.auth import obtener_rol_activo

from app.security import crear_access_token
from app.dependencies import obtener_usuario_actual


# Administrador de rutas del modulo de biometrica

router = APIRouter(
    prefix="/biometria",
    tags=["Biometría"]
)


def obtener_usuario_por_correo(db: Session, correo: str):
    return (
        db.query(Usuario)
        .options(
            joinedload(Usuario.roles)
            .joinedload(UsuarioRol.rol)
        )
        .filter(
            Usuario.Correo == correo,
            Usuario.Estado == "ACTIVO"
        )
        .first()
    )

 # Obtener dispositivos asociados 
@router.post(
    "/dispositivos",
    response_model=DispositivoRespuesta,
    status_code=status.HTTP_201_CREATED
)
def registrar_dispositivo_endpoint(
    datos: DispositivoRegistrar,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    dispositivo = registrar_dispositivo(
        db=db,
        id_usuario=usuario.IdUsuario,
        nombre_dispositivo=datos.NombreDispositivo,
        clave_publica=datos.ClavePublica,
        algoritmo=datos.Algoritmo
    )

    return dispositivo


@router.post(
    "/desafio",
    response_model=DesafioRespuesta
)
def solicitar_desafio_endpoint(
    datos: BiometriaDesafioRequest,
    db: Session = Depends(get_db)
):
    usuario = obtener_usuario_por_correo(
        db,
        datos.Correo
    )

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales biométricas no válidas"
        )

    dispositivo = (
        db.query(DispositivoUsuario)
        .filter(
            DispositivoUsuario.IdUsuario == usuario.IdUsuario,
            DispositivoUsuario.IdCredencial == datos.IdCredencial,
            DispositivoUsuario.Estado == "ACTIVO",
            DispositivoUsuario.BiometriaHabilitada == 1
        )
        .first()
    )

    if not dispositivo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales biométricas no válidas"
        )

    desafio = generar_desafio(
        db=db,
        id_usuario=usuario.IdUsuario,
        id_dispositivo=dispositivo.IdDispositivo
    )

    return desafio


@router.post(
    "/verificar",
    response_model=BiometriaLoginRespuesta
)
def verificar_biometria_endpoint(
    datos: BiometriaVerificar,
    db: Session = Depends(get_db)
):
    usuario = obtener_usuario_por_correo(
        db,
        datos.Correo
    )

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación biométrica no válida"
        )

    dispositivo = (
        db.query(DispositivoUsuario)
        .filter(
            DispositivoUsuario.IdUsuario == usuario.IdUsuario,
            DispositivoUsuario.IdCredencial == datos.IdCredencial,
            DispositivoUsuario.Estado == "ACTIVO",
            DispositivoUsuario.BiometriaHabilitada == 1
        )
        .first()
    )

    if not dispositivo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación biométrica no válida"
        )

    dispositivo_verificado = verificar_firma(
        db=db,
        id_usuario=usuario.IdUsuario,
        id_dispositivo=dispositivo.IdDispositivo,
        challenge_id=datos.ChallengeId,
        nonce_base64=datos.Nonce,
        firma_base64=datos.Firma,
        id_credencial=datos.IdCredencial
    )

    try:
        rol = obtener_rol_activo(usuario)

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El usuario tiene varios roles activos"
        )

    if rol is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene un rol activo"
        )

    access_token = crear_access_token({
        "sub": str(usuario.IdUsuario)
    })

    return {
        "mensaje": "Autenticación biométrica exitosa",
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": {
            "IdUsuario": usuario.IdUsuario,
            "Nombres": usuario.Nombres,
            "Apellidos": usuario.Apellidos,
            "Correo": usuario.Correo,
            "FotoPerfil": usuario.FotoPerfil,
            "Estado": usuario.Estado,
            "Rol": rol.Nombre
        }
    }


@router.patch(
    "/dispositivos/{id_dispositivo}/revocar",
    response_model=DispositivoRespuesta
)
def revocar_dispositivo_endpoint(
    id_dispositivo: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(obtener_usuario_actual)
):
    dispositivo = revocar_dispositivo(
        db=db,
        id_usuario=usuario.IdUsuario,
        id_dispositivo=id_dispositivo
    )

    return dispositivo
