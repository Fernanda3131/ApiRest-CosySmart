
import uuid

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    Index,
    text
)
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import relationship

from app.config.database import Base


class DispositivoUsuario(Base):
    __tablename__ = "DispositivosUsuario"

    IdDispositivo = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    IdUsuario = Column(
        Integer,
        ForeignKey("Usuarios.IdUsuario"),
        nullable=False
    )

    NombreDispositivo = Column(
        String(100),
        nullable=False
    )

    IdCredencial = Column(
        UNIQUEIDENTIFIER(as_uuid=True),
        nullable=False,
        unique=True,
        default=uuid.uuid4,
        server_default=text("NEWID()")
    )

    ClavePublica = Column(
        Text,
        nullable=False
    )

    Algoritmo = Column(
        String(50),
        nullable=False,
        default="ECDSA-P256-SHA256",
        server_default=text("'ECDSA-P256-SHA256'")
    )

    BiometriaHabilitada = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("1")
    )

    Estado = Column(
        String(20),
        nullable=False,
        default="ACTIVO",
        server_default=text("'ACTIVO'")
    )

    FechaVinculacion = Column(
        DateTime,
        nullable=False,
        server_default=text("SYSDATETIME()")
    )

    UltimoAcceso = Column(
        DateTime,
        nullable=True
    )

    FechaRevocacion = Column(
        DateTime,
        nullable=True
    )

    usuario = relationship(
        "Usuario",
        back_populates="dispositivos"
    )

    desafios = relationship(
        "DesafioBiometrico",
        back_populates="dispositivo"
    )

    __table_args__ = (
        Index("IX_Dispositivos_IdUsuario", "IdUsuario"),
    )
