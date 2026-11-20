
from sqlalchemy import (
    Column,
    Integer,
    String,
    BigInteger,
    DateTime,
    ForeignKey
)

from app.config.database import Base

#Modelo de Pago Orden para visualizar las ordenes que ya estan listas para un pago

class PagoOrden(Base):
    __tablename__ = "PagosOrden"

    IdPago = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    IdOrden = Column(
        Integer,
        ForeignKey("Ordenes.IdOrden"),
        nullable=False
    )

    Referencia = Column(
        String(100),
        nullable=False
    )

    IdTransaccionWompi = Column(
        String(100),
        nullable=True
    )

    EstadoPago = Column(
        String(30),
        nullable=False,
        default="PENDIENTE"
    )

    MontoCentavos = Column(
        BigInteger,
        nullable=False
    )

    MetodoPago = Column(
        String(30),
        nullable=False
    )

    FechaCreacion = Column(
        DateTime,
        nullable=False
    )

    FechaActualizacion = Column(
        DateTime,
        nullable=True
    )
