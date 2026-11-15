
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from datetime import datetime
from typing import Optional


class UsuarioRegistroRequest(BaseModel):
    Nombres: str = Field(min_length=1, max_length=100)
    Apellidos: str = Field(min_length=1, max_length=100)
    Correo: EmailStr
    Telefono: Optional[str] = Field(default=None, max_length=20)
    Contrasena: str = Field(min_length=8)
    FotoPerfil: Optional[str] = Field(default=None, max_length=500)


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


class UsuarioCreadoRespuesta(BaseModel):
    IdUsuario: int
    Nombres: str
    Correo: EmailStr
    Mensaje: str
