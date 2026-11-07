from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.config.database import Base


class UsuarioRol(Base):
    __tablename__ = "UsuarioRoles"

    IdUsuario = Column(
        Integer,
        ForeignKey("Usuarios.IdUsuario"),
        primary_key=True
    )

    IdRol = Column(
        Integer,
        ForeignKey("Roles.IdRol"),
        primary_key=True
    )

    FechaAsignacion = Column(
        DateTime,
        nullable=False
    )

    usuario = relationship(
        "Usuario",
        back_populates="roles"
    )

    rol = relationship(
        "Rol",
        back_populates="usuarios"
    )