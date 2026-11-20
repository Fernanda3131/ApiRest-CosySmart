
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID

#  Define los esquemas de validación y serialización de biometrica

class DispositivoRegistrar(BaseModel):
    NombreDispositivo: str = Field(
        min_length=2,
        max_length=100
    )

    ClavePublica: str = Field(
        min_length=50,
        max_length=2000
    )

    Algoritmo: str = "ECDSA-P256-SHA256"


class DispositivoRespuesta(BaseModel):
    IdDispositivo: int
    IdUsuario: int
    NombreDispositivo: str
    IdCredencial: UUID
    Algoritmo: str
    BiometriaHabilitada: bool
    Estado: str
    FechaVinculacion: datetime
    UltimoAcceso: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BiometriaDesafioRequest(BaseModel):
    Correo: EmailStr
    IdCredencial: UUID


class DesafioRespuesta(BaseModel):
    ChallengeId: UUID
    Nonce: str
    FechaExpiracion: datetime


class BiometriaVerificar(BaseModel):
    Correo: EmailStr
    IdCredencial: UUID
    ChallengeId: UUID

    Nonce: str = Field(
        min_length=40,
        max_length=100
    )

    Firma: str = Field(
        min_length=40,
        max_length=300
    )


class BiometriaLoginRespuesta(BaseModel):
    mensaje: str
    access_token: str
    token_type: str
    usuario: dict


class DispositivoEstadoActualizar(BaseModel):
    BiometriaHabilitada: bool
