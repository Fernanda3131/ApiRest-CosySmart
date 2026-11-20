from pydantic import BaseModel, ConfigDict

#  Define los esquemas de validación y serialización de categorias de productos

class CategoriaRespuesta(BaseModel):
    IdCategoria: int
    Nombre: str

    model_config = ConfigDict(from_attributes=True)