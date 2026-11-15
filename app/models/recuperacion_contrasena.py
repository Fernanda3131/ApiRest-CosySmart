
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey
)

from app.config.database import Base


class RecuperacionContrasena(Base):

    __tablename__ = "RecuperacionContrasena"

    IdRecuperacion = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    IdUsuario = Column(
        Integer,
        ForeignKey("Usuarios.IdUsuario"),
        nullable=False
    )

    CodigoHash = Column(
        String(64),
        nullable=False
    )

    FechaExpiracion = Column(
        DateTime,
        nullable=False
    )

    Intentos = Column(
        Integer,
        nullable=False,
        default=0
    )

    TokenRestablecimientoHash = Column(
        String(64),
        nullable=True
    )

    TokenExpiracion = Column(
        DateTime,
        nullable=True
    )

    FechaVerificacion = Column(
        DateTime,
        nullable=True
    )

    Usado = Column(
        Boolean,
        nullable=False,
        default=False
    )

    FechaCreacion = Column(
        DateTime,
        nullable=False
    )
