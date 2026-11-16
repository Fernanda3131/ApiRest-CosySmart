
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.openapi.utils import get_openapi

from app.routers import usuarios, auth
from app.config.database import get_db

from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.usuario_rol import UsuarioRol

from app.routers import recuperacion
from app.routers import biometria
from app.routers import productos
from app.routers import categorias


app = FastAPI(
    title="CosySmart API",
    description="API REST para la plataforma CosySmart",
    version="1.0.0"
)

DIRECTORIO_UPLOADS = Path(__file__).resolve().parent / "uploads"

DIRECTORIO_UPLOADS.mkdir(parents=True, exist_ok=True)


app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(biometria.router)
app.include_router(recuperacion.router)
app.include_router(productos.router)
app.include_router(categorias.router)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes
    )

    esquema_producto = openapi_schema.get(
        "components", {}
    ).get(
        "schemas", {}
    ).get(
        "Body_crear_producto_productos__post"
    )

    if esquema_producto:
        propiedades = esquema_producto.get("properties", {})
        fotos = propiedades.get("fotos")

        if fotos:
            fotos["type"] = "array"
            fotos["items"] = {
                "type": "string",
                "format": "binary"
            }
            fotos.pop("contentMediaType", None)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

app.mount(
    "/uploads",
    StaticFiles(directory=str(DIRECTORIO_UPLOADS)),
    name="uploads"
)


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
