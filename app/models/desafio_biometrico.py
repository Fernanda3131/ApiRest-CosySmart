
import uuid

from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    DateTime,
    ForeignKey,
    LargeBinary,
    Index,
    text
)
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.orm import relationship

from app.config.database import Base

# Modelo asociado a la creación de desafios biometricos, para un flujo correcto de autenticación

class DesafioBiometrico(Base):
    __tablename__ = "DesafiosBiometricos"

    IdDesafio = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )

    IdDispositivo = Column(
        Integer,
        ForeignKey("DispositivosUsuario.IdDispositivo"),
        nullable=False
    )

    ChallengeId = Column(
        UNIQUEIDENTIFIER(as_uuid=True),
        nullable=False,
        unique=True,
        default=uuid.uuid4,
        server_default=text("NEWID()")
    )

    NonceHash = Column(
        LargeBinary(32),
        nullable=False
    )

    FechaCreacion = Column(
        DateTime,
        nullable=False,
        server_default=text("SYSDATETIME()")
    )

    FechaExpiracion = Column(
        DateTime,
        nullable=False
    )

    FechaUtilizacion = Column(
        DateTime,
        nullable=True
    )

    dispositivo = relationship(
        "DispositivoUsuario",
        back_populates="desafios"
    )

    __table_args__ = (
        Index("IX_Desafios_Dispositivo", "IdDispositivo"),
        Index("IX_Desafios_Expiracion", "FechaExpiracion"),
    )
