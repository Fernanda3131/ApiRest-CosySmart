
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    Correo: EmailStr
    Contrasena: str


class UsuarioLoginRespuesta(BaseModel):
    IdUsuario: int
    Nombres: str
    Apellidos: str
    Correo: EmailStr
    FotoPerfil: str | None = None
    Estado: str


class LoginRespuesta(BaseModel):
    mensaje: str
    access_token: str
    token_type: str
    usuario: UsuarioLoginRespuesta
