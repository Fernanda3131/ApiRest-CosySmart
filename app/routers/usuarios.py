
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from datetime import datetime, timezone

from app.config.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import (
    UsuarioCrear,
    UsuarioRespuesta,
    UsuarioActualizar
)
from app.dependencies import obtener_usuario_actual


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"]
)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# REGISTRAR USUARIO
@router.post(
    "/",
    response_model=UsuarioRespuesta,
    status_code=status.HTTP_201_CREATED
)
def crear_usuario(
    usuario: UsuarioCrear,
    db: Session = Depends(get_db)
):
    usuario_existente = db.query(Usuario).filter(
        Usuario.Correo == usuario.Correo
    ).first()

    if usuario_existente:
        raise HTTPException(
            status_code=409,
            detail="El correo electrónico ya está registrado"
        )

    contrasena_hash = pwd_context.hash(usuario.Contrasena)

    nuevo_usuario = Usuario(
        Nombres=usuario.Nombres,
        Apellidos=usuario.Apellidos,
        Correo=usuario.Correo,
        Telefono=usuario.Telefono,
        Contrasena=contrasena_hash,
        FechaRegistro=datetime.now(timezone.utc).replace(tzinfo=None),
        Estado="ACTIVO"
    )

    try:
        db.add(nuevo_usuario)
        db.commit()
        db.refresh(nuevo_usuario)

        return nuevo_usuario

    except Exception as error:
        db.rollback()
        print("ERROR AL REGISTRAR USUARIO:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible registrar el usuario"
        )


# LISTAR USUARIOS ACTIVOS
@router.get("/", response_model=list[UsuarioRespuesta])
def listar_usuarios(
    usuario_actual=Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    usuarios = db.query(Usuario).filter(
        Usuario.Estado == "ACTIVO"
    ).order_by(
        Usuario.IdUsuario.desc()
    ).all()

    return usuarios


# CONSULTAR USUARIO POR ID
@router.get("/{id_usuario}", response_model=UsuarioRespuesta)
def consultar_usuario(
    id_usuario: int,
    usuario_actual=Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    if usuario_actual.IdUsuario != id_usuario:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para consultar este usuario"
        )

    usuario = db.query(Usuario).filter(
        Usuario.IdUsuario == id_usuario,
        Usuario.Estado == "ACTIVO"
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado o desactivado"
        )

    return usuario


# ACTUALIZAR USUARIO
@router.put("/{id_usuario}", response_model=UsuarioRespuesta)
def actualizar_usuario(
    id_usuario: int,
    datos: UsuarioActualizar,
    usuario_actual=Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    if usuario_actual.IdUsuario != id_usuario:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para modificar este usuario"
        )

    usuario = db.query(Usuario).filter(
        Usuario.IdUsuario == id_usuario,
        Usuario.Estado == "ACTIVO"
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado o desactivado"
        )

    cambios = datos.model_dump(exclude_unset=True)

    if "Correo" in cambios:
        correo_existente = db.query(Usuario).filter(
            Usuario.Correo == cambios["Correo"],
            Usuario.IdUsuario != id_usuario
        ).first()

        if correo_existente:
            raise HTTPException(
                status_code=409,
                detail="El correo ya está registrado por otro usuario"
            )

    for campo, valor in cambios.items():
        setattr(usuario, campo, valor)

    try:
        db.commit()
        db.refresh(usuario)

        return usuario

    except Exception as error:
        db.rollback()
        print("ERROR AL ACTUALIZAR USUARIO:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible actualizar el usuario"
        )


# DESACTIVAR USUARIO
@router.patch("/{id_usuario}/estado")
def cambiar_estado_usuario(
    id_usuario: int,
    usuario_actual=Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    if usuario_actual.IdUsuario != id_usuario:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para desactivar este usuario"
        )

    usuario = db.query(Usuario).filter(
        Usuario.IdUsuario == id_usuario
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="Usuario no encontrado"
        )

    if usuario.Estado == "INACTIVO":
        raise HTTPException(
            status_code=400,
            detail="El usuario ya está desactivado"
        )

    try:
        usuario.Estado = "INACTIVO"

        db.commit()
        db.refresh(usuario)

        return {
            "mensaje": "Usuario desactivado correctamente",
            "IdUsuario": usuario.IdUsuario,
            "Estado": usuario.Estado
        }

    except Exception as error:
        db.rollback()
        print("ERROR AL DESACTIVAR USUARIO:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="No fue posible desactivar el usuario"
        )
