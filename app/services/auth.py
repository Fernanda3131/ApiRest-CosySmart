from sqlalchemy.orm import Session, joinedload
from passlib.context import CryptContext

from app.models.usuario import Usuario
from app.models.usuario_rol import UsuarioRol

""" Descripción:
    Gestiona la lógica de autenticación de los usuarios
    de CosySmart mediante validación de credenciales y
    mecanismos de seguridad basados en JWT.

Responsabilidades:
    - Validar las credenciales proporcionadas por el usuario.
    - Verificar las contraseñas almacenadas mediante bcrypt.
    - Gestionar la autenticación de los usuarios.
    - Generar tokens JWT cuando la autenticación es exitosa.
    - Aplicar las validaciones necesarias para el acceso. """

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
        .filter(Usuario.Correo == correo.strip())
        .first()
    )

    if not usuario:
        return None

    if usuario.Estado != "ACTIVO":
        return None

    try:
        contrasena_valida = pwd_context.verify(
            contrasena,
            usuario.Contrasena
        )
    except (TypeError, ValueError):
        return None

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

    print(f"Usuario autenticado: {usuario.Correo}")

    print(
        "Roles encontrados:",
        [
            {
                "IdRol": rol.IdRol,
                "Nombre": rol.Nombre,
                "Estado": rol.Estado
            }
            for rol in [
                asignacion.rol
                for asignacion in usuario.roles
                if asignacion.rol is not None
            ]
        ]
    )

    print(
        "Roles activos:",
        [rol.Nombre for rol in roles_activos]
    )

    if not roles_activos:
        return None

    if len(roles_activos) > 1:
        raise ValueError(
            "El usuario tiene varios roles activos. "
            "Debe definirse cuál utilizar."
        )

    return roles_activos[0]