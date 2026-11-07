from sqlalchemy.orm import Session, joinedload
from passlib.context import CryptContext

from app.models.usuario import Usuario
from app.models.usuario_rol import UsuarioRol


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def autenticar_usuario(
    db: Session,
    correo: str,
    contrasena: str
):
    usuario = (
        db.query(Usuario)
        .options(
            joinedload(Usuario.roles)
            .joinedload(UsuarioRol.rol)
        )
        .filter(Usuario.Correo == correo)
        .first()
    )

    if not usuario or usuario.Estado != "ACTIVO":
        return None

    contrasena_valida = pwd_context.verify(
        contrasena,
        usuario.Contrasena
    )

    if not contrasena_valida:
        return None

    return usuario


def obtener_rol_activo(usuario: Usuario):
    roles_activos = [
        asignacion.rol
        for asignacion in usuario.roles
        if asignacion.rol is not None
        and asignacion.rol.Estado is True
    ]

    if len(roles_activos) == 0:
        return None


    if len(roles_activos) > 1:
        raise ValueError(
            "El usuario tiene varios roles activos y debe definirse cuál utilizar"
        )

    return roles_activos[0]