
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict

#  Define los esquemas de validación y serialización de orden 


class CrearOrdenSolicitud(BaseModel):
    NombreDestinatario: str = Field(min_length=2, max_length=150)
    TelefonoDestinatario: str = Field(min_length=7, max_length=20)
    CiudadEntrega: str = Field(min_length=2, max_length=100)
    DireccionEntrega: str = Field(min_length=5, max_length=300)
    NotasEntrega: str | None = Field(default=None, max_length=500)

    MetodoPago: Literal[
        "TARJETA",
        "PSE",
        "CONTRA_ENTREGA"
    ]

    Latitud: Decimal | None = Field(
        default=None,
        ge=-90,
        le=90
    )

    Longitud: Decimal | None = Field(
        default=None,
        ge=-180,
        le=180
    )


class DetalleOrdenRespuesta(BaseModel):
    IdDetalleOrden: int
    IdProducto: int
    NombreProducto: str
    PrecioUnitario: Decimal
    Cantidad: int
    Subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrdenRespuesta(BaseModel):
    IdOrden: int
    IdUsuario: int
    FechaOrden: datetime
    EstadoOrden: str
    EstadoPago: str
    MetodoPago: str
    Subtotal: Decimal
    Total: Decimal

    NombreDestinatario: str
    TelefonoDestinatario: str
    CiudadEntrega: str
    DireccionEntrega: str
    NotasEntrega: str | None = None

    Latitud: Decimal | None = None
    Longitud: Decimal | None = None

    Detalles: list[DetalleOrdenRespuesta] = Field(
        default_factory=list
    )

    model_config = ConfigDict(from_attributes=True)


class EnviarDespachoSolicitud(BaseModel):
    NumeroGuia: str | None = Field(
        default=None,
        max_length=100
    )


class DespachoRespuesta(BaseModel):
    IdDespacho: int
    IdOrden: int
    IdVendedor: int
    EstadoDespacho: str
    FechaEnvio: datetime | None = None
    NumeroGuia: str | None = None

    FechaOrden: datetime
    NombreDestinatario: str
    TelefonoDestinatario: str
    CiudadEntrega: str
    DireccionEntrega: str
    NotasEntrega: str | None = None

    Detalles: list[DetalleOrdenRespuesta] = Field(
        default_factory=list
    )
