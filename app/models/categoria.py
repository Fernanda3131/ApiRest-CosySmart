
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.config.database import Base


class Categoria(Base):
    __tablename__ = "Categorias"

    IdCategoria = Column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    Nombre = Column(
        String(100),
        nullable=False
    )

    Descripcion = Column(
        String(300),
        nullable=True
    )

    Imagen = Column(
        String(500),
        nullable=True
    )

    IdCategoriaPadre = Column(
        Integer,
        ForeignKey("Categorias.IdCategoria"),
        nullable=True
    )

    Estado = Column(
        Boolean,
        nullable=True
    )

    FechaCreacion = Column(
        DateTime,
        nullable=True
    )
