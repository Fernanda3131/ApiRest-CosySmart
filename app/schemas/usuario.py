
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class UsuarioRespuesta(BaseModel):

    IdUsuario: int
    Nombres: str
    Apellidos: str
    Correo: str

    Telefono: Optional[str] = None
    FotoPerfil: Optional[str] = None

    FechaRegistro: datetime
    UltimoAcceso: Optional[datetime] = None

    Estado: str

    model_config = ConfigDict(
        from_attributes=True
    )
