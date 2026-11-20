
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.config.database import Base


# Modelo que representa los productos asociados al carrito

class DetalleCarrito(Base):
    __tablename__ = "DetallesCarrito"

    IdDetalleCarrito = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    IdCarrito = Column(
        Integer,
        ForeignKey("Carritos.IdCarrito"),
        nullable=False
    )

    IdProducto = Column(
        Integer,
        ForeignKey("Productos.IdProducto"),
        nullable=False
    )

    Cantidad = Column(
        Integer,
        nullable=False
    )

    FechaAgregado = Column(
        DateTime,
        nullable=True
    )

    carrito = relationship(
        "Carrito",
        back_populates="detalles"
    )

    producto = relationship(
        "Producto"
    )
