from pydantic import BaseModel, ConfigDict


class CategoriaRespuesta(BaseModel):
    IdCategoria: int
    Nombre: str

    model_config = ConfigDict(from_attributes=True)