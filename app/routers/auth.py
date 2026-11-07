
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.database import get_db

from app.schemas.auth import (
    LoginRequest,
    LoginRespuesta,
    UsuarioLoginRespuesta
)

from app.services.auth import (
    autenticar_usuario,
    obtener_rol_activo
)

from app.security import crear_access_token

from app.dependencies import obtener_usuario_actual


router = APIRouter(
    prefix="/auth",
    tags=["Autenticación"]
)


@router.post(
    "/login",
    response_model=LoginRespuesta,
    status_code=status.HTTP_200_OK
)
def iniciar_sesion(
    datos: LoginRequest,
    db: Session = Depends(get_db)
):

    usuario = autenticar_usuario(
        db=db,
        correo=datos.Correo,
        contrasena=datos.Contrasena
    )

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo electrónico o contraseña incorrectos"
        )

    try:
        rol = obtener_rol_activo(usuario)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error)
        )

    if not rol:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene un rol activo asignado"
        )

    access_token = crear_access_token({
        "sub": str(usuario.IdUsuario)
    })

    return {
        "mensaje": "Inicio de sesión exitoso",
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


@router.get(
    "/me",
    response_model=UsuarioLoginRespuesta
)
def consultar_usuario_autenticado(
    usuario=Depends(obtener_usuario_actual)
):

    try:
        rol = obtener_rol_activo(usuario)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error)
        )

    if not rol:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene un rol activo asignado"
        )

    return {
        "IdUsuario": usuario.IdUsuario,
        "Nombres": usuario.Nombres,
        "Apellidos": usuario.Apellidos,
        "Correo": usuario.Correo,
        "FotoPerfil": usuario.FotoPerfil,
        "Estado": usuario.Estado,
        "Rol": rol.Nombre
    }
