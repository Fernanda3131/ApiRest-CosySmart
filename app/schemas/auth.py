from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    Correo: EmailStr
    Contrasena: str


class UsuarioLoginRespuesta(BaseModel):
    IdUsuario: int
    Nombres: str
    Apellidos: str
    Correo: EmailStr
    FotoPerfil: Optional[str] = None
    Estado: str
    Rol: str


class LoginRespuesta(BaseModel):
    mensaje: str
    access_token: str
    token_type: str
    usuario: UsuarioLoginRespuesta