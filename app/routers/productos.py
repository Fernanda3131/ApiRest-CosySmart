import uuid
import logging

from pathlib import Path
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    Body,
    status
)

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config.database import get_db
from app.dependencies import obtener_usuario_actual
from app.services.auth import obtener_rol_activo

from app.models.producto import Producto
from app.models.producto_imagen import ProductoImagen
from app.models.categoria import Categoria


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/productos",
    tags=["Productos"]
)


DIRECTORIO_IMAGENES = (
    Path(__file__).resolve().parent.parent
    / "uploads"
    / "productos"
)

DIRECTORIO_IMAGENES.mkdir(
    parents=True,
    exist_ok=True
)


MAX_BYTES = 5 * 1024 * 1024

TIPOS_PERMITIDOS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp"
}

UNIDADES_PESO = {
    "g",
    "kg",
    "toneladas"
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def detectar_tipo_imagen(contenido: bytes):
    if contenido.startswith(b"\xff\xd8\xff"):
        return ".jpg"

    if contenido.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"

    if (
        len(contenido) >= 12
        and contenido[:4] == b"RIFF"
        and contenido[8:12] == b"WEBP"
    ):
        return ".webp"

    return None


def validar_datos_imagen(contenido: bytes, content_type: str):

    if content_type not in TIPOS_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail="Solo se permiten fotografías JPG, PNG o WEBP"
        )

    if not contenido or len(contenido) > MAX_BYTES:
        raise HTTPException(
            status_code=400,
            detail="Cada fotografía debe pesar entre 1 byte y 5 MB"
        )

    extension_real = detectar_tipo_imagen(contenido)

    if not extension_real:
        raise HTTPException(
            status_code=400,
            detail="El contenido de una fotografía no es válido"
        )

    extension_declarada = TIPOS_PERMITIDOS[content_type]

    if extension_real != extension_declarada:
        raise HTTPException(
            status_code=400,
            detail="El formato declarado no coincide con el contenido de la fotografía"
        )

    return extension_real


def validar_acceso_producto(producto, usuario, db):

    rol = obtener_rol_activo(usuario)

    if not rol:
        raise HTTPException(
            status_code=403,
            detail="No tienes un rol autorizado"
        )

    nombre_rol = rol.Nombre.strip().upper()

    if nombre_rol == "ADMINISTRADOR":
        return

    if nombre_rol == "VENDEDOR":

        if producto.IdVendedor != usuario.IdUsuario:
            raise HTTPException(
                status_code=403,
                detail="No puedes modificar productos de otro vendedor"
            )

        return

    raise HTTPException(
        status_code=403,
        detail="No tienes permiso para modificar productos"
    )


def convertir_decimal(valor, campo):

    if valor is None:
        return None

    valor = str(valor).strip()

    if not valor:
        return None

    try:
        numero = Decimal(valor)

        if not numero.is_finite():
            raise InvalidOperation

        return numero

    except (InvalidOperation, ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"El campo {campo} debe ser un número válido"
        )


def obtener_ruta_fisica(ruta_publica):

    nombre_archivo = Path(ruta_publica).name

    ruta = (
        DIRECTORIO_IMAGENES / nombre_archivo
    ).resolve()

    if ruta.parent != DIRECTORIO_IMAGENES.resolve():
        return None

    return ruta


def eliminar_archivos(rutas):

    for ruta in rutas:

        try:

            if ruta and ruta.exists() and ruta.is_file():
                ruta.unlink()

        except OSError:

            logger.exception(
                "No se pudo eliminar el archivo: %s",
                ruta
            )


def eliminar_imagenes_antiguas(rutas_publicas):

    rutas_fisicas = []

    for ruta_publica in rutas_publicas:

        ruta_fisica = obtener_ruta_fisica(ruta_publica)

        if ruta_fisica:
            rutas_fisicas.append(ruta_fisica)

    eliminar_archivos(rutas_fisicas)


def validar_categoria_activa(db, id_categoria):

    categoria = db.query(Categoria).filter(
        Categoria.IdCategoria == id_categoria,
        Categoria.Estado == True
    ).first()

    if not categoria:
        raise HTTPException(
            status_code=400,
            detail="La categoría no existe o está inactiva"
        )

    return categoria


def obtener_respuesta_producto(producto):

    return {
        "IdProducto": producto.IdProducto,
        "IdVendedor": producto.IdVendedor,
        "IdCategoria": producto.IdCategoria,
        "Nombre": producto.Nombre,
        "Descripcion": producto.Descripcion,
        "Precio": float(producto.Precio),
        "Peso": (
            float(producto.Peso)
            if producto.Peso is not None
            else None
        ),
        "UnidadPeso": producto.UnidadPeso,
        "Alto": (
            float(producto.Alto)
            if producto.Alto is not None
            else None
        ),
        "Ancho": (
            float(producto.Ancho)
            if producto.Ancho is not None
            else None
        ),
        "Profundidad": (
            float(producto.Profundidad)
            if producto.Profundidad is not None
            else None
        ),
        "Color": producto.Color,
        "Stock": producto.Stock,
        "Estado": producto.Estado
    }


class EstadoProductoRequest(BaseModel):
    Estado: int = Field(ge=0, le=1)


# ============================================================
# CREAR PRODUCTO
# ============================================================

@router.post(
    "/",
    status_code=status.HTTP_201_CREATED
)
async def crear_producto(

    Nombre: str = Form(...),
    IdCategoria: int = Form(...),
    Precio: Decimal = Form(...),
    Descripcion: Optional[str] = Form(None),

    Peso: Optional[Decimal] = Form(None),
    UnidadPeso: Optional[str] = Form(None),

    Alto: Optional[Decimal] = Form(None),
    Ancho: Optional[Decimal] = Form(None),
    Profundidad: Optional[Decimal] = Form(None),

    Color: Optional[str] = Form(None),
    Stock: int = Form(0),

    fotos: list[UploadFile] = File(...),

    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):

    archivos_guardados = []
    transaccion_confirmada = False

    try:

        rol = obtener_rol_activo(usuario)

        if not rol or rol.Nombre.strip().upper() != "VENDEDOR":
            raise HTTPException(
                status_code=403,
                detail="Solo los vendedores pueden crear productos"
            )

        if len(fotos) < 1 or len(fotos) > 5:
            raise HTTPException(
                status_code=400,
                detail="Debes seleccionar entre 1 y 5 fotografías"
            )

        nombre = Nombre.strip()

        if not nombre:
            raise HTTPException(
                status_code=400,
                detail="El nombre del producto es obligatorio"
            )

        if len(nombre) > 150:
            raise HTTPException(
                status_code=400,
                detail="El nombre no puede superar 150 caracteres"
            )

        if (
            not Precio.is_finite()
            or Precio <= 0
            or Precio > Decimal("9999999999.99")
        ):
            raise HTTPException(
                status_code=400,
                detail="El precio debe ser positivo y válido"
            )

        if Descripcion is not None:

            Descripcion = Descripcion.strip() or None

            if len(Descripcion or "") > 1000:
                raise HTTPException(
                    status_code=400,
                    detail="La descripción supera los 1000 caracteres"
                )

        if Peso is not None:

            if (
                not Peso.is_finite()
                or Peso <= 0
                or Peso > Decimal("999999999.999")
            ):
                raise HTTPException(
                    status_code=400,
                    detail="El peso debe ser positivo y válido"
                )

            if not UnidadPeso:
                raise HTTPException(
                    status_code=400,
                    detail="Debes seleccionar una unidad de peso"
                )

            UnidadPeso = UnidadPeso.strip().lower()

            if UnidadPeso not in UNIDADES_PESO:
                raise HTTPException(
                    status_code=400,
                    detail="Unidad de peso no válida. Usa g, kg o toneladas"
                )

        else:
            UnidadPeso = None

        dimensiones = {
            "Alto": Alto,
            "Ancho": Ancho,
            "Profundidad": Profundidad
        }

        for campo, valor in dimensiones.items():

            if valor is not None and (
                not valor.is_finite()
                or valor <= 0
                or valor > Decimal("99999999.99")
            ):
                raise HTTPException(
                    status_code=400,
                    detail=f"El campo {campo} debe ser positivo y válido"
                )

        if Color is not None:

            Color = Color.strip() or None

            if Color and len(Color) > 50:
                raise HTTPException(
                    status_code=400,
                    detail="El color no puede superar 50 caracteres"
                )

        if Stock < 0:
            raise HTTPException(
                status_code=400,
                detail="El stock no puede ser negativo"
            )

        validar_categoria_activa(db, IdCategoria)

        producto = Producto(
            IdVendedor=usuario.IdUsuario,
            IdCategoria=IdCategoria,
            Nombre=nombre,
            Descripcion=Descripcion,
            Precio=Precio,
            Peso=Peso,
            UnidadPeso=UnidadPeso,
            Alto=Alto,
            Ancho=Ancho,
            Profundidad=Profundidad,
            Color=Color,
            Stock=Stock,
            Estado=1
        )

        db.add(producto)
        db.flush()

        rutas = []

        for posicion, foto in enumerate(fotos, start=1):

            contenido = await foto.read(MAX_BYTES + 1)

            extension = validar_datos_imagen(
                contenido,
                foto.content_type
            )

            nombre_archivo = f"{uuid.uuid4().hex}{extension}"

            ruta_archivo = DIRECTORIO_IMAGENES / nombre_archivo

            with open(ruta_archivo, "wb") as archivo:
                archivo.write(contenido)

            archivos_guardados.append(ruta_archivo)

            ruta_publica = f"/uploads/productos/{nombre_archivo}"

            imagen = ProductoImagen(
                IdProducto=producto.IdProducto,
                RutaImagen=ruta_publica,
                Orden=posicion
            )

            db.add(imagen)
            rutas.append(ruta_publica)

        db.commit()
        transaccion_confirmada = True

        db.refresh(producto)

        return {
            "mensaje": "Producto creado exitosamente",
            "producto": obtener_respuesta_producto(producto),
            "imagenes": rutas
        }

    except HTTPException:

        db.rollback()

        if not transaccion_confirmada:
            eliminar_archivos(archivos_guardados)

        raise

    except Exception:

        db.rollback()

        if not transaccion_confirmada:
            eliminar_archivos(archivos_guardados)

        logger.exception("Error creando producto")

        raise HTTPException(
            status_code=500,
            detail="No fue posible registrar el producto"
        )

    finally:

        for foto in fotos:
            await foto.close()


# ============================================================
# LISTAR PRODUCTOS
# ============================================================

@router.get("/")
def listar_productos(
    vista: str = Query(...),
    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):

    try:

        rol = obtener_rol_activo(usuario)

        if not rol:
            raise HTTPException(
                status_code=403,
                detail="Rol no autorizado"
            )

        nombre_rol = rol.Nombre.strip().upper()

        consulta = (
            db.query(Producto)
            .options(
                joinedload(Producto.categoria),
                selectinload(Producto.imagenes)
            )
        )

        if vista == "home":

            if nombre_rol not in ["COMPRADOR", "VENDEDOR"]:
                raise HTTPException(
                    403,
                    "No tienes permiso para esta vista"
                )

            consulta = (
                consulta
                .join(Producto.categoria)
                .filter(
                    Producto.Estado == 1,
                    Categoria.Estado == True
                )
                .order_by(Producto.IdProducto.desc())
                .limit(4)
            )

        elif vista == "catalogo":

            if nombre_rol != "COMPRADOR":
                raise HTTPException(
                    403,
                    "No tienes permiso para esta vista"
                )

            consulta = (
                consulta
                .join(Producto.categoria)
                .filter(
                    Producto.Estado == 1,
                    Categoria.Estado == True
                )
                .order_by(Producto.IdProducto.desc())
            )

        elif vista == "mis-productos":

            if nombre_rol != "VENDEDOR":
                raise HTTPException(
                    403,
                    "No tienes permiso para esta vista"
                )

            consulta = (
                consulta
                .filter(
                    Producto.IdVendedor == usuario.IdUsuario
                )
                .order_by(Producto.IdProducto.desc())
            )

        elif vista == "administracion":

            if nombre_rol != "ADMINISTRADOR":
                raise HTTPException(
                    403,
                    "No tienes permiso para esta vista"
                )

            consulta = consulta.order_by(
                Producto.IdProducto.desc()
            )

        else:
            raise HTTPException(
                400,
                "Vista de productos no válida"
            )

        productos = consulta.all()

        resultado = []

        for producto in productos:

            resultado.append({
                "IdProducto": producto.IdProducto,
                "IdVendedor": producto.IdVendedor,
                "IdCategoria": producto.IdCategoria,
                "NombreCategoria": (
                    producto.categoria.Nombre
                    if producto.categoria
                    else None
                ),
                "Nombre": producto.Nombre,
                "Descripcion": producto.Descripcion,
                "Precio": float(producto.Precio),
                "Peso": (
                    float(producto.Peso)
                    if producto.Peso is not None
                    else None
                ),
                "UnidadPeso": producto.UnidadPeso,
                "Alto": (
                    float(producto.Alto)
                    if producto.Alto is not None
                    else None
                ),
                "Ancho": (
                    float(producto.Ancho)
                    if producto.Ancho is not None
                    else None
                ),
                "Profundidad": (
                    float(producto.Profundidad)
                    if producto.Profundidad is not None
                    else None
                ),
                "Color": producto.Color,
                "Stock": producto.Stock,
                "Estado": producto.Estado,
                "imagenes": [
                    imagen.RutaImagen
                    for imagen in producto.imagenes
                ]
            })

        return resultado

    except HTTPException:
        raise

    except Exception:

        logger.exception("Error al listar productos")

        raise HTTPException(
            status_code=500,
            detail="Error interno al consultar los productos"
        )


# ============================================================
# ACTUALIZAR PRODUCTO
# ============================================================

@router.put("/{id_producto}")
async def actualizar_producto(

    id_producto: int,

    Nombre: Optional[str] = Form(None),
    IdCategoria: Optional[int] = Form(None),
    Precio: Optional[str] = Form(None),
    Descripcion: Optional[str] = Form(None),

    Peso: Optional[str] = Form(None),
    UnidadPeso: Optional[str] = Form(None),

    Alto: Optional[str] = Form(None),
    Ancho: Optional[str] = Form(None),
    Profundidad: Optional[str] = Form(None),

    Color: Optional[str] = Form(None),
    Stock: Optional[int] = Form(None),

    # Mismo tipo de parámetro de archivo que en POST.
    # La lista vacía permite actualizar sin reemplazar imágenes.
    fotos: list[UploadFile] = File([]),

    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):

    archivos_nuevos = []
    archivos_antiguos = []
    transaccion_confirmada = False

    try:

        producto = (
            db.query(Producto)
            .options(selectinload(Producto.imagenes))
            .filter(Producto.IdProducto == id_producto)
            .first()
        )

        if not producto:
            raise HTTPException(
                status_code=404,
                detail="El producto no existe"
            )

        validar_acceso_producto(producto, usuario, db)

        if Nombre is not None:

            nombre = Nombre.strip()

            if not nombre:
                raise HTTPException(
                    400,
                    "El nombre es obligatorio"
                )

            if len(nombre) > 150:
                raise HTTPException(
                    400,
                    "El nombre no puede superar 150 caracteres"
                )

            producto.Nombre = nombre

        if IdCategoria is not None:

            validar_categoria_activa(db, IdCategoria)
            producto.IdCategoria = IdCategoria

        if Precio is not None:

            precio = convertir_decimal(Precio, "Precio")

            if (
                precio is None
                or precio <= 0
                or precio > Decimal("9999999999.99")
            ):
                raise HTTPException(
                    400,
                    "El precio debe ser positivo y válido"
                )

            producto.Precio = precio

        if Descripcion is not None:

            descripcion = Descripcion.strip() or None

            if descripcion and len(descripcion) > 1000:
                raise HTTPException(
                    400,
                    "La descripción no puede superar 1000 caracteres"
                )

            producto.Descripcion = descripcion

        if Peso is not None:

            peso = convertir_decimal(Peso, "Peso")

            if peso is not None:

                if (
                    peso <= 0
                    or peso > Decimal("999999999.999")
                ):
                    raise HTTPException(
                        400,
                        "El peso debe ser positivo y válido"
                    )

                producto.Peso = peso

                if UnidadPeso is not None:

                    unidad = UnidadPeso.strip().lower()

                    if unidad not in UNIDADES_PESO:
                        raise HTTPException(
                            400,
                            "Unidad de peso no válida"
                        )

                    producto.UnidadPeso = unidad

                elif producto.UnidadPeso not in UNIDADES_PESO:

                    raise HTTPException(
                        400,
                        "Debes seleccionar una unidad de peso"
                    )

            else:

                producto.Peso = None
                producto.UnidadPeso = None

        elif UnidadPeso is not None:

            if producto.Peso is None:
                raise HTTPException(
                    400,
                    "No puedes asignar una unidad sin especificar el peso"
                )

            unidad = UnidadPeso.strip().lower()

            if unidad not in UNIDADES_PESO:
                raise HTTPException(
                    400,
                    "Unidad de peso no válida"
                )

            producto.UnidadPeso = unidad

        dimensiones = {
            "Alto": Alto,
            "Ancho": Ancho,
            "Profundidad": Profundidad
        }

        for campo, valor in dimensiones.items():

            if valor is not None:

                dimension = convertir_decimal(valor, campo)

                if dimension is not None:

                    if (
                        dimension <= 0
                        or dimension > Decimal("99999999.99")
                    ):
                        raise HTTPException(
                            400,
                            f"El campo {campo} debe ser positivo y válido"
                        )

                setattr(producto, campo, dimension)

        if Color is not None:

            color = Color.strip() or None

            if color and len(color) > 50:
                raise HTTPException(
                    400,
                    "El color no puede superar 50 caracteres"
                )

            producto.Color = color

        if Stock is not None:

            if Stock < 0:
                raise HTTPException(
                    400,
                    "El stock no puede ser negativo"
                )

            producto.Stock = Stock

        # Reemplazar imágenes únicamente cuando se adjunten nuevas.
        if fotos:

            if len(fotos) > 5:
                raise HTTPException(
                    400,
                    "No puedes seleccionar más de 5 fotografías"
                )

            archivos_antiguos = [
                imagen.RutaImagen
                for imagen in producto.imagenes
            ]

            rutas_nuevas = []

            for posicion, foto in enumerate(fotos, start=1):

                contenido = await foto.read(MAX_BYTES + 1)

                extension = validar_datos_imagen(
                    contenido,
                    foto.content_type
                )

                nombre_archivo = f"{uuid.uuid4().hex}{extension}"

                ruta_archivo = (
                    DIRECTORIO_IMAGENES / nombre_archivo
                )

                with open(ruta_archivo, "wb") as archivo:
                    archivo.write(contenido)

                archivos_nuevos.append(ruta_archivo)

                ruta_publica = (
                    f"/uploads/productos/{nombre_archivo}"
                )

                rutas_nuevas.append(
                    ProductoImagen(
                        IdProducto=producto.IdProducto,
                        RutaImagen=ruta_publica,
                        Orden=posicion
                    )
                )

            db.query(ProductoImagen).filter(
                ProductoImagen.IdProducto == id_producto
            ).delete(
                synchronize_session=False
            )

            db.add_all(rutas_nuevas)

        db.commit()
        transaccion_confirmada = True

        db.refresh(producto)

        # Eliminar imágenes anteriores solo después del commit.
        if fotos:
            eliminar_imagenes_antiguas(archivos_antiguos)

        imagenes_actuales = (
            db.query(ProductoImagen)
            .filter(
                ProductoImagen.IdProducto == id_producto
            )
            .order_by(ProductoImagen.Orden)
            .all()
        )

        return {
            "mensaje": "Producto actualizado exitosamente",
            "producto": obtener_respuesta_producto(producto),
            "imagenes": [
                imagen.RutaImagen
                for imagen in imagenes_actuales
            ]
        }

    except HTTPException:

        db.rollback()

        if not transaccion_confirmada:
            eliminar_archivos(archivos_nuevos)

        raise

    except Exception:

        db.rollback()

        if not transaccion_confirmada:
            eliminar_archivos(archivos_nuevos)

        logger.exception("Error actualizando producto")

        raise HTTPException(
            status_code=500,
            detail="No fue posible actualizar el producto"
        )

    finally:

        for foto in fotos:
            await foto.close()


# ============================================================
# ACTIVAR / DESACTIVAR PRODUCTO
# ============================================================

@router.patch("/{id_producto}/estado")
def cambiar_estado_producto(

    id_producto: int,
    datos: EstadoProductoRequest = Body(...),

    usuario=Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):

    try:

        producto = db.query(Producto).filter(
            Producto.IdProducto == id_producto
        ).first()

        if not producto:
            raise HTTPException(
                status_code=404,
                detail="El producto no existe"
            )

        validar_acceso_producto(
            producto,
            usuario,
            db
        )

        producto.Estado = datos.Estado

        db.commit()
        db.refresh(producto)

        mensaje = (
            "Producto activado exitosamente"
            if producto.Estado == 1
            else "Producto inactivado exitosamente"
        )

        return {
            "mensaje": mensaje,
            "IdProducto": producto.IdProducto,
            "Estado": producto.Estado
        }

    except HTTPException:

        db.rollback()
        raise

    except Exception:

        db.rollback()

        logger.exception(
            "Error cambiando estado del producto"
        )

        raise HTTPException(
            status_code=500,
            detail="No fue posible cambiar el estado del producto"
        )