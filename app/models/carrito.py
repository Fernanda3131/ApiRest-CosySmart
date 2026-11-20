
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.config.database import Base

# Modelo de funcionamiento para el carrito de compras

class Carrito(Base):
    __tablename__ = "Carritos"

    IdCarrito = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    IdUsuario = Column(
        Integer,
        ForeignKey("Usuarios.IdUsuario"),
        nullable=False
    )

    FechaCreacion = Column(
        DateTime,
        nullable=True
    )

    FechaActualizacion = Column(
        DateTime,
        nullable=True
    )

    Estado = Column(
        String(20),
        nullable=True,
        default="ACTIVO"
    )

    usuario = relationship(
        "Usuario"
    )

    detalles = relationship(
        "DetalleCarrito",
        back_populates="carrito",
        cascade="all, delete-orphan"
    )
