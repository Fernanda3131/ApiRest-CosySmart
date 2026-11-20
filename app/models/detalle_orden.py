
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    ForeignKey
)
from sqlalchemy.orm import relationship

from app.config.database import Base

# Modelo asociado a los productos en el detalle de la orden


class DetalleOrden(Base):
    __tablename__ = "DetallesOrden"

    IdDetalleOrden = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    IdOrden = Column(
        Integer,
        ForeignKey("Ordenes.IdOrden"),
        nullable=False
    )

    IdProducto = Column(
        Integer,
        ForeignKey("Productos.IdProducto"),
        nullable=False
    )

    NombreProducto = Column(
        String(150),
        nullable=False
    )

    PrecioUnitario = Column(
        Numeric(12, 2),
        nullable=False
    )

    Cantidad = Column(
        Integer,
        nullable=False
    )

    Subtotal = Column(
        Numeric(12, 2),
        nullable=False
    )

    orden = relationship(
        "Orden",
        back_populates="detalles"
    )

    producto = relationship("Producto")
