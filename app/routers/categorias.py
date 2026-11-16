from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.dependencies import obtener_usuario_actual
from app.services.auth import obtener_rol_activo
from app.models.categoria import Categoria
from app.schemas.categoria import CategoriaRespuesta

router = APIRouter(
    prefix="/categorias",
    tags=["Categorías"]
)


@router.get("/", response_model=list[CategoriaRespuesta])
def listar_categorias(
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    rol = obtener_rol_activo(usuario)

    roles_permitidos = ["VENDEDOR", "ADMINISTRADOR"]

    if not rol or rol.Nombre.strip().upper() not in roles_permitidos:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para consultar las categorías"
        )

    categorias = (
        db.query(Categoria)
        .filter(Categoria.Estado == True)
        .order_by(Categoria.Nombre.asc())
        .all()
    )

    return categorias