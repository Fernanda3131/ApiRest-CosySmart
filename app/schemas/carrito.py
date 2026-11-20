
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict

#  Define los esquemas de validación y serialización de carrito de compras

class AgregarProductoCarrito(BaseModel):
    IdProducto: int = Field(gt=0)
    Cantidad: int = Field(gt=0)


class ActualizarCantidadCarrito(BaseModel):
    Cantidad: int = Field(gt=0)


class ProductoCarritoRespuesta(BaseModel):
    IdProducto: int
    Nombre: str
    Descripcion: str | None = None
    Precio: Decimal
    Stock: int
    Imagenes: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DetalleCarritoRespuesta(BaseModel):
    IdDetalleCarrito: int
    Cantidad: int
    FechaAgregado: datetime | None = None
    Producto: ProductoCarritoRespuesta
    Subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class CarritoRespuesta(BaseModel):
    IdCarrito: int
    FechaCreacion: datetime | None = None
    FechaActualizacion: datetime | None = None
    Estado: str | None = None
    Detalles: list[DetalleCarritoRespuesta] = Field(default_factory=list)
    Total: Decimal

    model_config = ConfigDict(from_attributes=True)
