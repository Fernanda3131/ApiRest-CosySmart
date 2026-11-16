
import logging
import uuid

from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import Depends
from app.config.database import get_db

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File
)

from app.config.database import get_db

from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.usuario_rol import UsuarioRol

from app.schemas.usuario import (
    UsuarioRespuesta,
    UsuarioRegistroRequest,
    UsuarioCreadoRespuesta,
    UsuarioAdminCrearRequest,
    UsuarioAdminActualizarRequest,
    UsuarioAdminRespuesta,
    UsuarioAdminMensajeRespuesta
)

from app.services.auth import pwd_context
from app.dependencies import requiere_rol, obtener_usuario_actual


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"]
)


# ==========================================================
# CONFIGURACIÓN DE FOTOGRAFÍAS
# ==========================================================

DIRECTORIO_FOTOS = (
    Path(__file__).resolve().parents[1]
    / "uploads"
    / "perfiles"
)

DIRECTORIO_FOTOS.mkdir(parents=True, exist_ok=True)

TAMANO_MAXIMO = 5 * 1024 * 1024


FORMATOS_IMAGEN = {
    "jpeg": {
        "extension": ".jpg",
        "mime": "image/jpeg"
    },
    "png": {
        "extension": ".png",
        "mime": "image/png"
    },
    "webp": {
        "extension": ".webp",
        "mime": "image/webp"
    }
}


# ==========================================================
# FUNCIONES AUXILIARES
# ==========================================================

def obtener_fecha_actual():
    """
    Obtiene la fecha actual en UTC sin información de zona horaria,
    para mantener compatibilidad con columnas DateTime existentes.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def detectar_formato_imagen(contenido: bytes):
    if contenido.startswith(b"\xff\xd8\xff"):
        return "jpeg"

    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"

    if (
        len(contenido) >= 12
        and contenido[:4] == b"RIFF"
        and contenido[8:12] == b"WEBP"
    ):
        return "webp"

    return None


def eliminar_foto_anterior(ruta_foto: str):
    """
    Elimina únicamente fotos anteriores almacenadas
    dentro del directorio de perfiles.
    """

    if not ruta_foto:
        return

    prefijo = "/uploads/perfiles/"

    if not ruta_foto.startswith(prefijo):
        return

    nombre_archivo = ruta_foto[len(prefijo):]

    if (
        not nombre_archivo
        or "/" in nombre_archivo
        or "\\" in nombre_archivo
    ):
        return

    archivo = (DIRECTORIO_FOTOS / nombre_archivo).resolve()

    if archivo.parent != DIRECTORIO_FOTOS.resolve():
        return

    if archivo.is_file():
        try:
            archivo.unlink()
        except OSError:
            logger.exception(
                "No se pudo eliminar la foto anterior: %s",
                archivo
            )


def construir_respuesta_admin(usuario: Usuario) -> dict:
    """
    Construye la respuesta del administrador incluyendo
    los nombres de los roles asignados al usuario.
    """

    roles = [
        relacion.rol.Nombre
        for relacion in usuario.roles
        if relacion.rol is not None
    ]

    return {
        "IdUsuario": usuario.IdUsuario,
        "Nombres": usuario.Nombres,
        "Apellidos": usuario.Apellidos,
        "Correo": usuario.Correo,
        "Telefono": usuario.Telefono,
        "FotoPerfil": usuario.FotoPerfil,
        "FechaRegistro": usuario.FechaRegistro,
        "UltimoAcceso": usuario.UltimoAcceso,
        "Estado": usuario.Estado,
        "Roles": roles
    }


def obtener_roles_activos(
    ids_roles: list[int],
    db: Session
) -> list[Rol]:
    """
    Comprueba que todos los roles solicitados existan,
    estén activos y no estén repetidos.
    """

    ids_unicos = set(ids_roles)

    if len(ids_unicos) != len(ids_roles):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se permiten roles repetidos."
        )

    roles = (
        db.query(Rol)
        .filter(
            Rol.IdRol.in_(ids_unicos),
            Rol.Estado == 1
        )
        .all()
    )

    if len(roles) != len(ids_unicos):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uno o varios roles no existen o están inactivos."
        )

    return roles


def contar_administradores_activos(db: Session) -> int:
    """
    Cuenta los usuarios activos que tienen asignado
    el rol ADMINISTRADOR.
    """

    return (
        db.query(Usuario.IdUsuario)
        .join(
            UsuarioRol,
            Usuario.IdUsuario == UsuarioRol.IdUsuario
        )
        .join(
            Rol,
            UsuarioRol.IdRol == Rol.IdRol
        )
        .filter(
            Usuario.Estado == "ACTIVO",
            Rol.Nombre == "ADMINISTRADOR",
            Rol.Estado == 1
        )
        .distinct()
        .count()
    )


# ==========================================================
# 1. REGISTRO PÚBLICO DE COMPRADORES
# POST /usuarios/
# ==========================================================

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

    usuario_existente = (
        db.query(Usuario)
        .filter(
            func.lower(Usuario.Correo) == correo
        )
        .first()
    )

    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo electrónico ya se encuentra registrado."
        )

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
            detail="No se encontró el rol COMPRADOR activo."
        )

    contrasena_hash = pwd_context.hash(datos.Contrasena)

    ahora = obtener_fecha_actual()

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
        db.flush()

        asignacion = UsuarioRol(
            IdUsuario=nuevo_usuario.IdUsuario,
            IdRol=rol_comprador.IdRol,
            FechaAsignacion=ahora
        )

        db.add(asignacion)

        db.commit()
        db.refresh(nuevo_usuario)

    except Exception:
        db.rollback()
        logger.exception("Error registrando un usuario.")
        raise

    return {
        "IdUsuario": nuevo_usuario.IdUsuario,
        "Nombres": nuevo_usuario.Nombres,
        "Correo": nuevo_usuario.Correo,
        "Mensaje": "Usuario registrado correctamente."
    }


# ==========================================================
# 2. LISTAR USUARIOS
# GET /usuarios/
# ==========================================================

@router.get(
    "/",
    response_model=list[UsuarioAdminRespuesta]
)
def listar_usuarios(
    busqueda: Optional[str] = None,
    estado: Optional[str] = None,
    id_rol: Optional[int] = None,
    usuario_actual=Depends(requiere_rol("ADMINISTRADOR")),
    db: Session = Depends(get_db)
):

    consulta = db.query(Usuario)

    # Filtro por estado
    if estado:
        estado = estado.strip().upper()

        if estado not in ["ACTIVO", "INACTIVO"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El estado debe ser ACTIVO o INACTIVO."
            )

        consulta = consulta.filter(
            Usuario.Estado == estado
        )

    # Filtro por nombre, apellido o correo
    if busqueda and busqueda.strip():
        termino = f"%{busqueda.strip()}%"

        consulta = consulta.filter(
            (Usuario.Nombres.ilike(termino)) |
            (Usuario.Apellidos.ilike(termino)) |
            (Usuario.Correo.ilike(termino))
        )

    # Filtro por rol
    if id_rol is not None:
        consulta = consulta.filter(
            Usuario.IdUsuario.in_(
                db.query(UsuarioRol.IdUsuario)
                .filter(UsuarioRol.IdRol == id_rol)
            )
        )

    usuarios = (
        consulta
        .order_by(Usuario.IdUsuario.desc())
        .all()
    )

    return [
        construir_respuesta_admin(usuario)
        for usuario in usuarios
    ]


# ==========================================================
# 3. CREAR USUARIO DESDE ADMINISTRADOR
# POST /usuarios/admin
# ==========================================================

@router.post(
    "/admin",
    response_model=UsuarioAdminRespuesta,
    status_code=status.HTTP_201_CREATED
)
def crear_usuario_admin(
    datos: UsuarioAdminCrearRequest,
    usuario_actual=Depends(requiere_rol("ADMINISTRADOR")),
    db: Session = Depends(get_db)
):

    correo = str(datos.Correo).strip().lower()

    usuario_existente = (
        db.query(Usuario)
        .filter(
            func.lower(Usuario.Correo) == correo
        )
        .first()
    )

    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un usuario con ese correo."
        )

    roles = obtener_roles_activos(datos.Roles, db)

    ahora = obtener_fecha_actual()

    nuevo_usuario = Usuario(
        Nombres=datos.Nombres.strip(),
        Apellidos=datos.Apellidos.strip(),
        Correo=correo,
        Telefono=datos.Telefono,
        Contrasena=pwd_context.hash(datos.Contrasena),
        FotoPerfil=None,
        FechaRegistro=ahora,
        Estado="ACTIVO"
    )

    try:
        db.add(nuevo_usuario)
        db.flush()

        for rol in roles:
            asignacion = UsuarioRol(
                IdUsuario=nuevo_usuario.IdUsuario,
                IdRol=rol.IdRol,
                FechaAsignacion=ahora
            )

            db.add(asignacion)

        db.commit()
        db.refresh(nuevo_usuario)

    except Exception:
        db.rollback()
        logger.exception("Error creando usuario desde administrador.")
        raise

    return construir_respuesta_admin(nuevo_usuario)


# ==========================================================
# 4. CONSULTAR USUARIO POR ID
# GET /usuarios/{id_usuario}
# ==========================================================

@router.get(
    "/{id_usuario}",
    response_model=UsuarioAdminRespuesta
)
def obtener_usuario_admin(
    id_usuario: int,
    usuario_actual=Depends(requiere_rol("ADMINISTRADOR")),
    db: Session = Depends(get_db)
):

    usuario = (
        db.query(Usuario)
        .filter(Usuario.IdUsuario == id_usuario)
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )

    return construir_respuesta_admin(usuario)


# ==========================================================
# 5. ACTUALIZAR USUARIO Y ROLES
# PUT /usuarios/{id_usuario}
# ==========================================================

@router.put(
    "/{id_usuario}",
    response_model=UsuarioAdminRespuesta
)
def actualizar_usuario_admin(
    id_usuario: int,
    datos: UsuarioAdminActualizarRequest,
    usuario_actual=Depends(requiere_rol("ADMINISTRADOR")),
    db: Session = Depends(get_db)
):

    usuario = (
        db.query(Usuario)
        .filter(Usuario.IdUsuario == id_usuario)
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )

    correo = str(datos.Correo).strip().lower()

    otro_usuario = (
        db.query(Usuario)
        .filter(
            func.lower(Usuario.Correo) == correo,
            Usuario.IdUsuario != id_usuario
        )
        .first()
    )

    if otro_usuario:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ese correo ya está registrado por otro usuario."
        )

    roles_nuevos = obtener_roles_activos(datos.Roles, db)

    # Comprobar si se está retirando el rol ADMINISTRADOR
    tenia_rol_admin = any(
        relacion.rol is not None
        and relacion.rol.Nombre == "ADMINISTRADOR"
        for relacion in usuario.roles
    )

    tendra_rol_admin = any(
        rol.Nombre == "ADMINISTRADOR"
        for rol in roles_nuevos
    )

    if (
        usuario.Estado == "ACTIVO"
        and tenia_rol_admin
        and not tendra_rol_admin
    ):
        if contar_administradores_activos(db) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No puedes retirar el rol del último "
                    "administrador activo."
                )
            )

    try:
        # Actualizar datos personales
        usuario.Nombres = datos.Nombres.strip()
        usuario.Apellidos = datos.Apellidos.strip()
        usuario.Correo = correo
        usuario.Telefono = datos.Telefono

        # Cambiar contraseña solamente si se envió una nueva
        if datos.Contrasena:
            usuario.Contrasena = pwd_context.hash(
                datos.Contrasena
            )

        # Obtener las relaciones actuales
        roles_actuales = {
            relacion.IdRol: relacion
            for relacion in usuario.roles
        }

        ids_roles_nuevos = {
            rol.IdRol
            for rol in roles_nuevos
        }

        # Eliminar relaciones que ya no se necesitan
        for id_rol_actual, relacion in roles_actuales.items():

            if id_rol_actual not in ids_roles_nuevos:
                db.delete(relacion)

        # Crear las relaciones nuevas
        ahora = obtener_fecha_actual()

        for rol in roles_nuevos:

            if rol.IdRol not in roles_actuales:
                nueva_asignacion = UsuarioRol(
                    IdUsuario=usuario.IdUsuario,
                    IdRol=rol.IdRol,
                    FechaAsignacion=ahora
                )

                db.add(nueva_asignacion)

        db.commit()
        db.refresh(usuario)

    except Exception:
        db.rollback()
        logger.exception(
            "Error actualizando el usuario %s",
            id_usuario
        )
        raise

    return construir_respuesta_admin(usuario)


# ==========================================================
# 6. DESACTIVAR USUARIO
# DELETE /usuarios/{id_usuario}
# ==========================================================

@router.delete(
    "/{id_usuario}",
    response_model=UsuarioAdminMensajeRespuesta
)
def desactivar_usuario_admin(
    id_usuario: int,
    usuario_actual=Depends(requiere_rol("ADMINISTRADOR")),
    db: Session = Depends(get_db)
):

    usuario = (
        db.query(Usuario)
        .filter(Usuario.IdUsuario == id_usuario)
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado."
        )

    if usuario.Estado == "INACTIVO":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya se encuentra inactivo."
        )

    # Evitar que el administrador se desactive a sí mismo
    if usuario.IdUsuario == usuario_actual.IdUsuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivar tu propio usuario."
        )

    tiene_rol_admin = any(
        relacion.rol is not None
        and relacion.rol.Nombre == "ADMINISTRADOR"
        for relacion in usuario.roles
    )

    # Proteger al último administrador activo
    if (
        tiene_rol_admin
        and contar_administradores_activos(db) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No puedes desactivar al último "
                "administrador activo."
            )
        )

    try:
        usuario.Estado = "INACTIVO"

        db.commit()

    except Exception:
        db.rollback()
        logger.exception(
            "Error desactivando el usuario %s",
            id_usuario
        )
        raise

    return {
        "IdUsuario": usuario.IdUsuario,
        "Mensaje": "Usuario desactivado correctamente."
    }


# ==========================================================
# 7. ACTUALIZAR FOTO DE PERFIL DEL USUARIO AUTENTICADO
# PUT /usuarios/me/foto
# ==========================================================

@router.put("/me/foto")
def actualizar_foto_perfil(
    foto: UploadFile = File(...),
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """
    Actualiza la foto de perfil del usuario autenticado.
    """

    if usuario.Estado != "ACTIVO":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no está activo."
        )

    contenido = foto.file.read(TAMANO_MAXIMO + 1)

    if not contenido:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo está vacío."
        )

    if len(contenido) > TAMANO_MAXIMO:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="La imagen no puede superar los 5 MB."
        )

    formato = detectar_formato_imagen(contenido)

    if formato not in FORMATOS_IMAGEN:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Formato no permitido. Usa JPG, PNG o WebP."
        )

    configuracion = FORMATOS_IMAGEN[formato]

    nombre_archivo = (
        f"{uuid.uuid4().hex}{configuracion['extension']}"
    )

    ruta_archivo = DIRECTORIO_FOTOS / nombre_archivo

    ruta_anterior = usuario.FotoPerfil

    try:
        with open(ruta_archivo, "wb") as archivo:
            archivo.write(contenido)

        usuario.FotoPerfil = (
            f"/uploads/perfiles/{nombre_archivo}"
        )

        db.commit()
        db.refresh(usuario)

    except Exception:
        db.rollback()

        if ruta_archivo.exists():
            ruta_archivo.unlink()

        logger.exception(
            "Error actualizando foto del usuario %s",
            usuario.IdUsuario
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible guardar la foto de perfil."
        )

    if ruta_anterior and ruta_anterior != usuario.FotoPerfil:
        eliminar_foto_anterior(ruta_anterior)

    return {
        "mensaje": "Foto de perfil actualizada correctamente.",
        "FotoPerfil": usuario.FotoPerfil
    }

@router.get(
    "/roles/activos",
    dependencies=[Depends(requiere_rol("ADMINISTRADOR"))]
)
def listar_roles_activos(db: Session = Depends(get_db)):
    roles = (
        db.query(Rol)
        .filter(Rol.Estado == 1)
        .order_by(Rol.Nombre.asc())
        .all()
    )

    return [
        {
            "IdRol": rol.IdRol,
            "Nombre": rol.Nombre
        }
        for rol in roles
    ]


@router.patch(
    "/{id_usuario}/reactivar",
    dependencies=[Depends(requiere_rol("ADMINISTRADOR"))]
)
def reactivar_usuario(
    id_usuario: int,
    db: Session = Depends(get_db)
):
    usuario = (
        db.query(Usuario)
        .filter(Usuario.IdUsuario == id_usuario)
        .first()
    )

    if not usuario:
        raise HTTPException(
            status_code=404,
            detail="El usuario no existe"
        )

    if usuario.Estado == "ACTIVO":
        return {
            "IdUsuario": usuario.IdUsuario,
            "Mensaje": "El usuario ya se encuentra activo"
        }

    usuario.Estado = "ACTIVO"

    try:
        db.commit()
        db.refresh(usuario)

        return {
            "IdUsuario": usuario.IdUsuario,
            "Mensaje": "Usuario reactivado correctamente"
        }

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No fue posible reactivar el usuario"
        )
