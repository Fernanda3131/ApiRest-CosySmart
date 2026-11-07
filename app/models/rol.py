from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship

from app.config.database import Base


class Rol(Base):
    __tablename__ = "Roles"

    IdRol = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    Nombre = Column(
        String(60),
        nullable=False
    )

    Descripcion = Column(
        String(400),
        nullable=True
    )

    Estado = Column(
        Boolean,
        nullable=False,
        default=True
    )

    usuarios = relationship(
        "UsuarioRol",
        back_populates="rol"
    )