
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.config.database import Base

# Modelo de despachos asociados al producto en orden

class DespachoOrden(Base):
    __tablename__ = "DespachosOrden"

    IdDespacho = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    IdOrden = Column(
        Integer,
        ForeignKey("Ordenes.IdOrden"),
        nullable=False
    )

    IdVendedor = Column(
        Integer,
        ForeignKey("Usuarios.IdUsuario"),
        nullable=False
    )

    EstadoDespacho = Column(
        String(30),
        nullable=False,
        default="PENDIENTE"
    )

    FechaEnvio = Column(
        DateTime,
        nullable=True
    )

    NumeroGuia = Column(
        String(100),
        nullable=True
    )

    orden = relationship(
        "Orden",
        back_populates="despachos"
    )

    __table_args__ = (
        UniqueConstraint(
            "IdOrden",
            "IdVendedor",
            name="UQ_DespachosOrden_Orden_Vendedor"
        ),
    )
