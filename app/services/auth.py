from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.models.usuario import Usuario


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def autenticar_usuario(
    db: Session,
    correo: str,
    contrasena: str
):
    usuario = db.query(Usuario).filter(
        Usuario.Correo == correo
    ).first()

    if not usuario or usuario.Estado != "ACTIVO":
        return None

    contrasena_valida = pwd_context.verify(
        contrasena,
        usuario.Contrasena
    )

    if not contrasena_valida:
        return None

    return usuario
