
from pydantic import BaseModel, Field

#  Define los esquemas de validación y serialización de pago

class IniciarPagoSolicitud(BaseModel):
    IdOrden: int = Field(gt=0)
