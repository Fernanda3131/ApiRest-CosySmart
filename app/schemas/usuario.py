from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional
from datetime import datetime


class UsuarioCrear(BaseModel):
    Nombres: str
    Apellidos: str
    Correo: EmailStr
    Telefono: Optional[str] = None
    Contrasena: str

class UsuarioRespuesta(BaseModel):
    IdUsuario: int
    Nombres: str
    Apellidos: str
    Correo: EmailStr
    Telefono: Optional[str] = None
    FotoPerfil: Optional[str] = None
    Estado: str
    FechaRegistro: datetime
    UltimoAcceso: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class UsuarioActualizar(BaseModel):
    Nombres: Optional[str] = None
    Apellidos: Optional[str] = None
    Correo: Optional[EmailStr] = None
    Telefono: Optional[str] = None
    FotoPerfil: Optional[str] = None