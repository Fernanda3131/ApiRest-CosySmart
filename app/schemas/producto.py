
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict

#  Define los esquemas de validación y serialización de prodcutos


class ProductoRespuesta(BaseModel):
    IdProducto: int
    IdVendedor: int
    IdCategoria: int
    Nombre: str
    Descripcion: str | None
    Precio: Decimal
    Peso: Decimal | None

    model_config = ConfigDict(from_attributes=True)


class ProductoCreadoRespuesta(BaseModel):
    mensaje: str
    producto: ProductoRespuesta
    imagenes: list[str]
