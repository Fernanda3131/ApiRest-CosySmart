
from pydantic import BaseModel, Field

#  Define los esquemas de validación y serialización de recuperación de contraseña


class SolicitudRecuperacion(BaseModel):
    correo: str = Field(min_length=5, max_length=150)


class VerificarCodigoRequest(BaseModel):
    correo: str = Field(min_length=5, max_length=150)
    codigo: str = Field(min_length=6, max_length=6)


class RestablecerContrasenaRequest(BaseModel):
    token: str = Field(min_length=20)
    nueva_contrasena: str = Field(min_length=8, max_length=128)
