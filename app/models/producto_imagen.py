
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.config.database import Base


# Modelo de las imagenes asociadas a un producto en catalogo

class ProductoImagen(Base):
    __tablename__ = "ProductoImagenes"

    IdImagen = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    IdProducto = Column(
        Integer,
        ForeignKey("Productos.IdProducto"),
        nullable=False
    )

    RutaImagen = Column(
        String(500),
        nullable=False
    )

    Orden = Column(
        Integer,
        nullable=False
    )

    producto = relationship(
        "Producto",
        back_populates="imagenes"
    )
