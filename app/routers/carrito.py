
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config.database import get_db
from app.dependencies import obtener_usuario_actual

from app.models.carrito import Carrito
from app.models.detalle_carrito import DetalleCarrito
from app.models.producto import Producto

from app.schemas.carrito import (
    AgregarProductoCarrito,
    ActualizarCantidadCarrito,
    CarritoRespuesta
)

# Administrador de rutas del modulo carrito
router = APIRouter(
    prefix="/carrito",
    tags=["Carrito"]
)

# Obtener el usuario

def validar_comprador(
    usuario=Depends(obtener_usuario_actual)
):
    roles_usuario = [
        asignacion.rol.Nombre.strip().upper()
        for asignacion in usuario.roles
        if asignacion.rol is not None
        and asignacion.rol.Estado is True
    ]

    if "COMPRADOR" not in roles_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los compradores pueden utilizar el carrito"
        )

    return usuario


def obtener_carrito_activo(
    db: Session,
    id_usuario: int,
    crear: bool = True
):
    carrito = db.query(Carrito).filter(
        Carrito.IdUsuario == id_usuario,
        Carrito.Estado == "ACTIVO"
    ).first()

    if carrito:
        return carrito

    if not crear:
        return None

    fecha_actual = datetime.now()

    carrito = Carrito(
        IdUsuario=id_usuario,
        FechaCreacion=fecha_actual,
        FechaActualizacion=fecha_actual,
        Estado="ACTIVO"
    )

    db.add(carrito)
    db.commit()
    db.refresh(carrito)

    return carrito

def construir_respuesta_carrito(
    db: Session,
    carrito: Carrito
):
    carrito = db.query(Carrito).options(
        joinedload(Carrito.detalles).joinedload(
            DetalleCarrito.producto
        ).selectinload(
            Producto.imagenes
        )
    ).filter(
        Carrito.IdCarrito == carrito.IdCarrito
    ).first()

    detalles_respuesta = []
    total = Decimal("0.00")

    for detalle in carrito.detalles:

        producto = detalle.producto

        precio = Decimal(str(producto.Precio))
        cantidad = detalle.Cantidad

        subtotal = precio * cantidad
        total += subtotal

        imagenes = [
            imagen.RutaImagen
            for imagen in producto.imagenes
        ]

        detalles_respuesta.append({
            "IdDetalleCarrito": detalle.IdDetalleCarrito,
            "Cantidad": cantidad,
            "FechaAgregado": detalle.FechaAgregado,
            "Producto": {
                "IdProducto": producto.IdProducto,
                "Nombre": producto.Nombre,
                "Descripcion": producto.Descripcion,
                "Precio": precio,
                "Stock": producto.Stock,
                "Imagenes": imagenes
            },
            "Subtotal": subtotal
        })

    return {
        "IdCarrito": carrito.IdCarrito,
        "FechaCreacion": carrito.FechaCreacion,
        "FechaActualizacion": carrito.FechaActualizacion,
        "Estado": carrito.Estado,
        "Detalles": detalles_respuesta,
        "Total": total
    }


# Agregar productos al carrito
@router.post(
    "/agregar",
    response_model=CarritoRespuesta,
    status_code=status.HTTP_200_OK
)
def agregar_producto(
    datos: AgregarProductoCarrito,
    db: Session = Depends(get_db),
    usuario=Depends(validar_comprador)
):

    producto = db.query(Producto).filter(
        Producto.IdProducto == datos.IdProducto
    ).first()

    if not producto:
        raise HTTPException(
            status_code=404,
            detail="El producto no existe"
        )

    if producto.Estado != 1:
        raise HTTPException(
            status_code=400,
            detail="El producto no está disponible"
        )

    if producto.Stock <= 0:
        raise HTTPException(
            status_code=400,
            detail="El producto no tiene stock disponible"
        )

    carrito = obtener_carrito_activo(
        db,
        usuario.IdUsuario
    )

    detalle = db.query(DetalleCarrito).filter(
        DetalleCarrito.IdCarrito == carrito.IdCarrito,
        DetalleCarrito.IdProducto == producto.IdProducto
    ).first()

    cantidad_actual = detalle.Cantidad if detalle else 0
    nueva_cantidad = cantidad_actual + datos.Cantidad

    if nueva_cantidad > producto.Stock:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente. Disponible: {producto.Stock}"
        )

    try:
        if detalle:
            detalle.Cantidad = nueva_cantidad
        else:
            detalle = DetalleCarrito(
                IdCarrito=carrito.IdCarrito,
                IdProducto=producto.IdProducto,
                Cantidad=datos.Cantidad,
                FechaAgregado=datetime.now()
            )

            db.add(detalle)

        carrito.FechaActualizacion = datetime.now()

        db.commit()
        db.refresh(carrito)

    except Exception:
        db.rollback()
        raise

    return construir_respuesta_carrito(db, carrito)

@router.get(
    "/",
    response_model=CarritoRespuesta
)
def consultar_carrito(
    db: Session = Depends(get_db),
    usuario=Depends(validar_comprador)
):

    carrito = obtener_carrito_activo(
        db,
        usuario.IdUsuario
    )

    return construir_respuesta_carrito(db, carrito)



# Detalles del carrito
@router.patch(
    "/detalles/{id_detalle}",
    response_model=CarritoRespuesta
)
def actualizar_cantidad(
    id_detalle: int,
    datos: ActualizarCantidadCarrito,
    db: Session = Depends(get_db),
    usuario=Depends(validar_comprador)
):

    carrito = obtener_carrito_activo(
        db,
        usuario.IdUsuario
    )

    detalle = db.query(DetalleCarrito).filter(
        DetalleCarrito.IdDetalleCarrito == id_detalle,
        DetalleCarrito.IdCarrito == carrito.IdCarrito
    ).first()

    if not detalle:
        raise HTTPException(
            status_code=404,
            detail="El producto no se encuentra en tu carrito"
        )

    producto = db.query(Producto).filter(
        Producto.IdProducto == detalle.IdProducto
    ).first()

    if not producto or producto.Estado != 1:
        raise HTTPException(
            status_code=400,
            detail="El producto ya no está disponible"
        )

    if datos.Cantidad > producto.Stock:
        raise HTTPException(
            status_code=400,
            detail=f"Stock insuficiente. Disponible: {producto.Stock}"
        )

    try:
        detalle.Cantidad = datos.Cantidad
        carrito.FechaActualizacion = datetime.now()

        db.commit()
        db.refresh(carrito)

    except Exception:
        db.rollback()
        raise

    return construir_respuesta_carrito(db, carrito)

# Borrar Productos
@router.delete(
    "/detalles/{id_detalle}",
    response_model=CarritoRespuesta
)
def eliminar_producto(
    id_detalle: int,
    db: Session = Depends(get_db),
    usuario=Depends(validar_comprador)
):

    carrito = obtener_carrito_activo(
        db,
        usuario.IdUsuario
    )

    detalle = db.query(DetalleCarrito).filter(
        DetalleCarrito.IdDetalleCarrito == id_detalle,
        DetalleCarrito.IdCarrito == carrito.IdCarrito
    ).first()

    if not detalle:
        raise HTTPException(
            status_code=404,
            detail="El producto no se encuentra en tu carrito"
        )

    try:
        db.delete(detalle)

        carrito.FechaActualizacion = datetime.now()

        db.commit()
        db.refresh(carrito)

    except Exception:
        db.rollback()
        raise

    return construir_respuesta_carrito(db, carrito)

@router.delete(
    "/",
    response_model=CarritoRespuesta
)
def vaciar_carrito(
    db: Session = Depends(get_db),
    usuario=Depends(validar_comprador)
):

    carrito = obtener_carrito_activo(
        db,
        usuario.IdUsuario
    )

    try:
        db.query(DetalleCarrito).filter(
            DetalleCarrito.IdCarrito == carrito.IdCarrito
        ).delete(synchronize_session=False)

        carrito.FechaActualizacion = datetime.now()

        db.commit()
        db.refresh(carrito)

    except Exception:
        db.rollback()
        raise

    return construir_respuesta_carrito(db, carrito)
