from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Numeric,
    ForeignKey
)
from sqlalchemy.orm import relationship

from app.config.database import Base

# Modelo asociado a Orden de productos solicitados por el cliente
class Orden(Base):
    __tablename__ = "Ordenes"

    IdOrden = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    IdUsuario = Column(
        Integer,
        ForeignKey("Usuarios.IdUsuario"),
        nullable=False
    )

    FechaOrden = Column(
        DateTime,
        nullable=False
    )

    EstadoOrden = Column(
        String(30),
        nullable=False,
        default="PENDIENTE"
    )

    EstadoPago = Column(
        String(30),
        nullable=False,
        default="PENDIENTE"
    )


    MetodoPago = Column(
        String(30),
        nullable=False
    )

    Subtotal = Column(
        Numeric(12, 2),
        nullable=False
    )

    Total = Column(
        Numeric(12, 2),
        nullable=False
    )

    NombreDestinatario = Column(
        String(150),
        nullable=False
    )

    TelefonoDestinatario = Column(
        String(20),
        nullable=False
    )

    CiudadEntrega = Column(
        String(100),
        nullable=False
    )

    DireccionEntrega = Column(
        String(300),
        nullable=False
    )

    NotasEntrega = Column(
        String(500),
        nullable=True
    )

    Latitud = Column(
        Numeric(10, 7),
        nullable=True
    )

    Longitud = Column(
        Numeric(10, 7),
        nullable=True
    )

    usuario = relationship(
        "Usuario",
        back_populates="ordenes"
    )

    detalles = relationship(
        "DetalleOrden",
        back_populates="orden",
        cascade="all, delete-orphan"
    )

    despachos = relationship(
        "DespachoOrden",
        back_populates="orden",
        cascade="all, delete-orphan"
    )