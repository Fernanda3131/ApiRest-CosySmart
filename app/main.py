
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.routers import usuarios, auth
from app.config.database import get_db

# Registrar modelos para que SQLAlchemy conozca las relaciones
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.usuario_rol import UsuarioRol


app = FastAPI(
    title="CosySmart API",
    description="API REST para la plataforma CosySmart",
    version="1.0.0"
)


# Registrar routers
app.include_router(auth.router)
app.include_router(usuarios.router)


@app.get("/")
def inicio():
    return {
        "mensaje": "Bienvenido a CosySmart API",
        "estado": "Activo"
    }


@app.get("/conexion")
def verificar_conexion(
    db: Session = Depends(get_db)
):
    try:
        resultado = db.execute(
            text("SELECT DB_NAME() AS base_datos")
        ).mappings().first()

        return {
            "conexion": "Exitosa",
            "base_datos": resultado["base_datos"]
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Error de conexión: {str(error)}"
        )
