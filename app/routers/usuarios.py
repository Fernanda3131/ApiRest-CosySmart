
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.usuario import Usuario
from app.schemas.usuario import UsuarioRespuesta
from app.dependencies import requiere_rol


router = APIRouter(
    prefix="/usuarios",
    tags=["Usuarios"]
)


@router.get(
    "/",
    response_model=list[UsuarioRespuesta]
)
def listar_usuarios(
    usuario_actual=Depends(
        requiere_rol("ADMINISTRADOR")
    ),
    db: Session = Depends(get_db)
):

    usuarios = db.query(Usuario).filter(
        Usuario.Estado == "ACTIVO"
    ).order_by(
        Usuario.IdUsuario.desc()
    ).all()

    return usuarios
