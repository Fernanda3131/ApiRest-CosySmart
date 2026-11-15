
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.usuario_rol import UsuarioRol

from app.schemas.usuario import (
    UsuarioRespuesta,
    UsuarioRegistroRequest,
    UsuarioCreadoRespuesta
)

from app.services.auth import pwd_context
from app.dependencies import requiere_rol


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"]
)


@router.post(
    "/",
    response_model=UsuarioCreadoRespuesta,
    status_code=status.HTTP_201_CREATED
)
def registrar_usuario(
    datos: UsuarioRegistroRequest,
    db: Session = Depends(get_db)
):

    correo = str(datos.Correo).strip().lower()

    # 1. Comprobar si el correo ya existe
    usuario_existente = (
        db.query(Usuario)
        .filter(Usuario.Correo == correo)
        .first()
    )

    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo electrónico ya se encuentra registrado"
        )

    # 2. Buscar el rol COMPRADOR activo
    rol_comprador = (
        db.query(Rol)
        .filter(
            Rol.Nombre == "COMPRADOR",
            Rol.Estado == 1
        )
        .first()
    )

    if not rol_comprador:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se encontró el rol COMPRADOR activo"
        )

    # 3. Generar hash de contraseña
    contrasena_hash = pwd_context.hash(datos.Contrasena)

    # 4. Crear usuario
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)

    nuevo_usuario = Usuario(
        Nombres=datos.Nombres.strip(),
        Apellidos=datos.Apellidos.strip(),
        Correo=correo,
        Telefono=datos.Telefono,
        Contrasena=contrasena_hash,
        FotoPerfil=datos.FotoPerfil,
        FechaRegistro=ahora,
        Estado="ACTIVO"
    )

    try:
        db.add(nuevo_usuario)

        # Obtener el IdUsuario generado por SQL Server
        db.flush()

        # 5. Asignar rol COMPRADOR
        asignacion = UsuarioRol(
            IdUsuario=nuevo_usuario.IdUsuario,
            IdRol=rol_comprador.IdRol,
            FechaAsignacion=ahora
        )

        db.add(asignacion)

        # Guardar usuario y rol en una misma transacción
        db.commit()
        db.refresh(nuevo_usuario)

    except Exception:
        db.rollback()
        raise

    return {
        "IdUsuario": nuevo_usuario.IdUsuario,
        "Nombres": nuevo_usuario.Nombres,
        "Correo": nuevo_usuario.Correo,
        "Mensaje": "Usuario registrado correctamente"
    }


@router.get(
    "/",
    response_model=list[UsuarioRespuesta]
)
def listar_usuarios(
    usuario_actual=Depends(
        requiere_rol("ADMINISTRADOR")
    ),
    db: Session = Depends(get_db)
):

    usuarios = db.query(Usuario).filter(
        Usuario.Estado == "ACTIVO"
    ).order_by(
        Usuario.IdUsuario.desc()
    ).all()

    return usuarios
