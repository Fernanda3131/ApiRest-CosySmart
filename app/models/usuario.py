from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.config.database import Base


class Usuario(Base):
    __tablename__ = "Usuarios"

    IdUsuario = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    Nombres = Column(String(100), nullable=False)
    Apellidos = Column(String(100), nullable=False)
    Correo = Column(String(150), nullable=False)
    Telefono = Column(String(20), nullable=True)
    Contrasena = Column(String(255), nullable=False)
    FotoPerfil = Column(String(500), nullable=True)
    FechaRegistro = Column(DateTime, nullable=False)
    UltimoAcceso = Column(DateTime, nullable=True)
    Estado = Column(String(20), nullable=False, default="ACTIVO")

    roles = relationship(
        "UsuarioRol",
        back_populates="usuario"
    )