
from sqlalchemy import Column, Integer, String, ForeignKey, Numeric
from sqlalchemy.orm import relationship

from app.config.database import Base

# Modelo informativo de Producto

class Producto(Base):
    __tablename__ = "Productos"

    IdProducto = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    IdVendedor = Column(
        Integer,
        ForeignKey("Usuarios.IdUsuario"),
        nullable=False
    )

    IdCategoria = Column(
        Integer,
        ForeignKey("Categorias.IdCategoria"),
        nullable=False
    )

    Nombre = Column(
        String(150),
        nullable=False
    )

    Descripcion = Column(
        String(1000),
        nullable=True
    )

    Precio = Column(
        Numeric(12, 2),
        nullable=False
    )

    # Peso y unidad de medida
    Peso = Column(
        Numeric(12, 3),
        nullable=True
    )

    UnidadPeso = Column(
        String(15),
        nullable=True
    )

    Alto = Column(
        Numeric(10, 2),
        nullable=True
    )

    Ancho = Column(
        Numeric(10, 2),
        nullable=True
    )

    Profundidad = Column(
        Numeric(10, 2),
        nullable=True
    )

    Color = Column(
        String(50),
        nullable=True
    )

    Stock = Column(
        Integer,
        nullable=False,
        default=0
    )
    Estado = Column(
    Integer,
    nullable=False,
    default=1,
    server_default="1"
   )

    # Relaciones
    vendedor = relationship("Usuario")

    categoria = relationship("Categoria")

    imagenes = relationship(
        "ProductoImagen",
        back_populates="producto",
        cascade="all, delete-orphan",
        order_by="ProductoImagen.Orden"
    )
