"""
Sistema de Inventario - Proyecto Final

- CRUD de productos
- Registro de ventas (actualiza stock y muestra total)
- Reportes (stock bajo y valor total del inventario)
- Base de datos: MongoDB
- Interfaz gráfica: Tkinter

Funciones extra:
- Pantalla de bienvenida y login (usuario/contraseña) antes de entrar.
- Gestión de usuarios (colección 'usuarios' en MongoDB).
- Barra superior con usuario logeado + botón de cerrar sesión.
- Registro de cada venta en la colección 'ventas' con el usuario que la hizo.
- Historial de ventas con filtros por usuario y fecha.

NOTA IMPORTANTE:
Antes de ejecutar este programa debes:
1) Instalar pymongo -> pip install pymongo
2) Tener el servidor de MongoDB corriendo en tu máquina.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import datetime

try:
    from pymongo import MongoClient
except ImportError:
    MongoClient = None


# ---------------------- CONFIGURACIÓN DE MONGODB ---------------------- #

def conectar_mongodb():
    """Devuelve la colección de productos en MongoDB."""
    if MongoClient is None:
        raise ImportError(
            "La librería 'pymongo' no está instalada. "
            "Instálala con: pip install pymongo"
        )

    cliente = MongoClient("mongodb://localhost:27017/")
    db = cliente["tienda_informatica"]
    return db["productos"]


def conectar_mongodb_usuarios():
    """Devuelve la colección de usuarios en MongoDB."""
    if MongoClient is None:
        raise ImportError(
            "La librería 'pymongo' no está instalada. "
            "Instálala con: pip install pymongo"
        )

    cliente = MongoClient("mongodb://localhost:27017/")
    db = cliente["tienda_informatica"]
    return db["usuarios"]


def conectar_mongodb_ventas():
    """Devuelve la colección de ventas en MongoDB."""
    if MongoClient is None:
        raise ImportError(
            "La librería 'pymongo' no está instalada. "
            "Instálala con: pip install pymongo"
        )

    cliente = MongoClient("mongodb://localhost:27017/")
    db = cliente["tienda_informatica"]
    return db["ventas"]


try:
    coleccion_productos = conectar_mongodb()
except Exception as e:
    print("Error al conectar a MongoDB (productos):", e)
    coleccion_productos = None

try:
    coleccion_usuarios = conectar_mongodb_usuarios()
    if coleccion_usuarios.count_documents({}) == 0:
        coleccion_usuarios.insert_one({
            "username": "admin",
            "password": "admin",
            "creado_por": "sistema"
        })
        print("Usuario por defecto creado: admin / admin")
except Exception as e:
    print("Error al conectar a MongoDB (usuarios):", e)
    coleccion_usuarios = None

try:
    coleccion_ventas = conectar_mongodb_ventas()
except Exception as e:
    print("Error al conectar a MongoDB (ventas):", e)
    coleccion_ventas = None


# ---------------------- CONSTANTES DEL SISTEMA ------------------------ #

CATEGORIAS = ["Computadoras", "Smartphones", "Accesorios", "Periféricos"]
STOCK_MINIMO = 5


# ----------------- FUNCIONES DE LÓGICA DEL INVENTARIO ----------------- #

def agregar_producto(id_producto, nombre, categoria, precio, cantidad, proveedor):
    if coleccion_productos is None:
        raise RuntimeError("No hay conexión con la base de datos.")

    if not nombre:
        raise ValueError("El nombre no puede estar vacío.")
    if categoria not in CATEGORIAS:
        raise ValueError("La categoría no es válida.")
    if precio < 0:
        raise ValueError("El precio no puede ser negativo.")
    if cantidad < 0:
        raise ValueError("La cantidad no puede ser negativa.")
    if not proveedor:
        raise ValueError("El proveedor no puede estar vacío.")

    existente = coleccion_productos.find_one({"id_producto": id_producto})
    if existente:
        raise ValueError(f"Ya existe un producto con ID {id_producto}.")

    documento = {
        "id_producto": id_producto,
        "nombre": nombre,
        "categoria": categoria,
        "precio": precio,
        "cantidad": cantidad,
        "proveedor": proveedor
    }

    coleccion_productos.insert_one(documento)
    return documento


def buscar_producto(criterio, valor):
    if coleccion_productos is None:
        raise RuntimeError("No hay conexión con la base de datos.")

    filtro = {}

    if criterio == "id":
        filtro["id_producto"] = int(valor)
    elif criterio == "nombre":
        filtro["nombre"] = {"$regex": valor, "$options": "i"}
    elif criterio == "proveedor":
        filtro["proveedor"] = {"$regex": valor, "$options": "i"}
    elif criterio == "categoria":
        filtro["categoria"] = valor
    else:
        raise ValueError("Criterio de búsqueda no válido.")

    resultados = list(coleccion_productos.find(filtro).sort("id_producto", 1))
    return resultados


def modificar_producto(id_producto, nuevos_datos):
    if coleccion_productos is None:
        raise RuntimeError("No hay conexión con la base de datos.")

    resultado = coleccion_productos.update_one(
        {"id_producto": id_producto},
        {"$set": nuevos_datos}
    )
    return resultado.matched_count > 0


def eliminar_producto(id_producto):
    if coleccion_productos is None:
        raise RuntimeError("No hay conexión con la base de datos.")

    resultado = coleccion_productos.delete_one({"id_producto": id_producto})
    return resultado.deleted_count > 0


def mostrar_inventario():
    if coleccion_productos is None:
        raise RuntimeError("No hay conexión con la base de datos.")

    productos = list(coleccion_productos.find().sort("id_producto", 1))
    return productos


def realizar_venta(id_producto, cantidad_vendida, usuario=None):
    """
    Registra una venta:
    - Verifica producto y stock.
    - Actualiza inventario.
    - Guarda la venta en la colección 'ventas' con el usuario que la hizo.
    """
    if coleccion_productos is None:
        raise RuntimeError("No hay conexión con la base de datos.")

    prod = coleccion_productos.find_one({"id_producto": id_producto})
    if not prod:
        raise ValueError("No existe un producto con ese ID.")

    stock_actual = prod["cantidad"]
    if cantidad_vendida <= 0:
        raise ValueError("La cantidad vendida debe ser mayor a 0.")
    if stock_actual < cantidad_vendida:
        raise ValueError("No hay stock suficiente.")

    nuevo_stock = stock_actual - cantidad_vendida

    coleccion_productos.update_one(
        {"id_producto": id_producto},
        {"$set": {"cantidad": nuevo_stock}}
    )

    total = cantidad_vendida * prod["precio"]

    if coleccion_ventas is not None:
        doc_venta = {
            "id_producto": id_producto,
            "nombre": prod.get("nombre"),
            "cantidad": cantidad_vendida,
            "precio_unitario": prod.get("precio"),
            "total": total,
            "fecha": datetime.datetime.now(),
            "usuario": usuario,
        }
        try:
            coleccion_ventas.insert_one(doc_venta)
        except Exception as e:
            print("Error registrando venta:", e)

    return total


def generar_reporte():
    if coleccion_productos is None:
        raise RuntimeError("No hay conexión con la base de datos.")

    productos = list(coleccion_productos.find())
    bajo_stock = []
    valor_total = 0.0

    for p in productos:
        valor_total += p["cantidad"] * p["precio"]
        if p["cantidad"] < STOCK_MINIMO:
            bajo_stock.append(p)

    return bajo_stock, valor_total


def obtener_ventas(filtro_usuario=None, fecha_desde=None, fecha_hasta=None):
    """
    Obtiene las ventas desde la colección 'ventas', opcionalmente filtrando por:
    - usuario
    - rango de fechas (datetime.datetime desde/hasta)
    """
    if coleccion_ventas is None:
        raise RuntimeError("No hay conexión con la base de datos de ventas.")

    filtro = {}

    if filtro_usuario:
        filtro["usuario"] = filtro_usuario

    rango_fecha = {}
    if fecha_desde is not None:
        rango_fecha["$gte"] = fecha_desde
    if fecha_hasta is not None:
        rango_fecha["$lte"] = fecha_hasta

    if rango_fecha:
        filtro["fecha"] = rango_fecha

    ventas = list(coleccion_ventas.find(filtro).sort("fecha", -1))
    return ventas


# ----------------- FUNCIONES DE USUARIOS ------------------------------ #

def crear_usuario(username, password, creado_por=None):
    """Crea un usuario nuevo en la colección 'usuarios'."""
    if coleccion_usuarios is None:
        raise RuntimeError("No hay conexión con la base de datos de usuarios.")

    if not username:
        raise ValueError("El nombre de usuario no puede estar vacío.")
    if not password:
        raise ValueError("La contraseña no puede estar vacía.")

    existente = coleccion_usuarios.find_one({"username": username})
    if existente:
        raise ValueError(f"Ya existe un usuario con nombre '{username}'.")

    doc = {
        "username": username,
        "password": password,
        "creado_por": creado_por
    }
    coleccion_usuarios.insert_one(doc)
    return doc


def validar_login(username, password):
    """Valida usuario y contraseña. Devuelve el documento del usuario si es correcto."""
    if coleccion_usuarios is None:
        raise RuntimeError("No hay conexión con la base de datos de usuarios.")

    user = coleccion_usuarios.find_one({
        "username": username,
        "password": password
    })
    return user


# --------------- VARIABLES GLOBALES DE LA INTERFAZ -------------------- #

root = None
entry_id = None
entry_nombre = None
combo_categoria = None
entry_precio = None
entry_cantidad = None
entry_proveedor = None
entry_buscar = None
combo_criterio = None
entry_cantidad_venta = None
label_total_venta = None
tree = None

usuario_actual = None
entry_nuevo_usuario = None
entry_nueva_contrasena = None
label_usuario_actual = None


# ------------------- FUNCIONES DE LA INTERFAZ TKINTER ----------------- #

def limpiar_formulario():
    entry_id.delete(0, tk.END)
    entry_nombre.delete(0, tk.END)
    combo_categoria.set("")
    entry_precio.delete(0, tk.END)
    entry_cantidad.delete(0, tk.END)
    entry_proveedor.delete(0, tk.END)


def llenar_formulario_desde_tabla(event):
    seleccion = tree.selection()
    if not seleccion:
        return

    item_id = seleccion[0]
    datos = tree.item(item_id, "values")

    entry_id.delete(0, tk.END)
    entry_id.insert(0, datos[0])

    entry_nombre.delete(0, tk.END)
    entry_nombre.insert(0, datos[1])

    combo_categoria.set(datos[2])

    entry_precio.delete(0, tk.END)
    entry_precio.insert(0, datos[3])

    entry_cantidad.delete(0, tk.END)
    entry_cantidad.insert(0, datos[4])

    entry_proveedor.delete(0, tk.END)
    entry_proveedor.insert(0, datos[5])


def actualizar_tabla(productos=None):
    for fila in tree.get_children():
        tree.delete(fila)

    if productos is None:
        try:
            productos = mostrar_inventario()
        except RuntimeError as e:
            messagebox.showerror("Error", str(e))
            return

    for p in productos:
        tree.insert(
            "",
            tk.END,
            values=(
                p["id_producto"],
                p["nombre"],
                p["categoria"],
                p["precio"],
                p["cantidad"],
                p["proveedor"],
            ),
        )


def boton_agregar():
    try:
        id_producto = int(entry_id.get())
        nombre = entry_nombre.get()
        categoria = combo_categoria.get()
        precio = float(entry_precio.get())
        cantidad = int(entry_cantidad.get())
        proveedor = entry_proveedor.get()

        agregar_producto(id_producto, nombre, categoria, precio, cantidad, proveedor)

        messagebox.showinfo("Éxito", "Producto agregado correctamente.")
        actualizar_tabla()
        limpiar_formulario()
    except ValueError as ve:
        messagebox.showerror("Datos inválidos", str(ve))
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al agregar: {e}")


def boton_modificar():
    try:
        id_producto = int(entry_id.get())
        nombre = entry_nombre.get()
        categoria = combo_categoria.get()
        precio = float(entry_precio.get())
        cantidad = int(entry_cantidad.get())
        proveedor = entry_proveedor.get()

        nuevos_datos = {
            "nombre": nombre,
            "categoria": categoria,
            "precio": precio,
            "cantidad": cantidad,
            "proveedor": proveedor,
        }

        ok = modificar_producto(id_producto, nuevos_datos)

        if ok:
            messagebox.showinfo("Éxito", "Producto modificado correctamente.")
            actualizar_tabla()
        else:
            messagebox.showwarning("Aviso", "No se encontró un producto con ese ID.")
    except ValueError as ve:
        messagebox.showerror("Datos inválidos", str(ve))
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al modificar: {e}")


def boton_eliminar():
    try:
        id_producto = int(entry_id.get())

        confirmar = messagebox.askyesno(
            "Confirmar",
            f"¿Seguro que deseas eliminar el producto con ID {id_producto}?"
        )
        if not confirmar:
            return

        ok = eliminar_producto(id_producto)
        if ok:
            messagebox.showinfo("Éxito", "Producto eliminado.")
            actualizar_tabla()
            limpiar_formulario()
        else:
            messagebox.showwarning("Aviso", "No se encontró un producto con ese ID.")
    except ValueError:
        messagebox.showerror("Datos inválidos", "Debes escribir un ID numérico.")
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al eliminar: {e}")


def boton_buscar():
    criterio = combo_criterio.get()
    texto = entry_buscar.get()

    if not criterio:
        messagebox.showwarning("Aviso", "Selecciona un criterio de búsqueda.")
        return
    if not texto:
        messagebox.showwarning("Aviso", "Escribe algo para buscar.")
        return

    try:
        if criterio == "ID":
            resultados = buscar_producto("id", texto)
        elif criterio == "Nombre":
            resultados = buscar_producto("nombre", texto)
        elif criterio == "Proveedor":
            resultados = buscar_producto("proveedor", texto)
        elif criterio == "Categoría":
            resultados = buscar_producto("categoria", texto)
        else:
            messagebox.showerror("Error", "Criterio desconocido.")
            return

        if resultados:
            actualizar_tabla(resultados)
        else:
            messagebox.showinfo("Sin resultados", "No se encontraron productos.")
            actualizar_tabla([])
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al buscar: {e}")


def boton_mostrar_todo():
    actualizar_tabla()


def boton_realizar_venta():
    global usuario_actual

    seleccion = tree.selection()
    if not seleccion:
        messagebox.showwarning("Aviso", "Selecciona un producto en la tabla.")
        return

    try:
        cantidad_vendida = int(entry_cantidad_venta.get())
    except ValueError:
        messagebox.showerror("Datos inválidos", "Escribe una cantidad entera para vender.")
        return

    item_id = seleccion[0]
    datos = tree.item(item_id, "values")
    id_producto = int(datos[0])

    try:
        total = realizar_venta(id_producto, cantidad_vendida, usuario_actual)
        label_total_venta.config(text=f"Total de la venta: ${total:.2f}")
        messagebox.showinfo("Venta realizada", f"Venta registrada por ${total:.2f}")
        actualizar_tabla()
    except Exception as e:
        messagebox.showerror("Error", str(e))


def boton_reporte_stock_bajo():
    try:
        bajo_stock, _ = generar_reporte()
        if not bajo_stock:
            messagebox.showinfo("Reporte", "No hay productos con stock bajo.")
            return

        lineas = []
        for p in bajo_stock:
            linea = f"ID {p['id_producto']} - {p['nombre']} (stock: {p['cantidad']})"
            lineas.append(linea)

        mensaje = "\n".join(lineas)
        messagebox.showinfo("Productos con stock bajo", mensaje)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo generar el reporte: {e}")


def boton_reporte_valor_total():
    try:
        _, valor_total = generar_reporte()
        messagebox.showinfo("Valor del inventario", f"Valor total: ${valor_total:.2f}")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo calcular el valor del inventario: {e}")


def abrir_ventana_historial():
    """Muestra historial de ventas con filtros por usuario y rango de fechas."""
    if coleccion_ventas is None:
        messagebox.showerror("Error", "No hay conexión con la base de datos de ventas.")
        return

    ventana = tk.Toplevel(root)
    ventana.title("Historial de ventas")
    ventana.geometry("900x400")

    frame_filtros = tk.LabelFrame(ventana, text="Filtros", padx=10, pady=10)
    frame_filtros.pack(fill="x", padx=10, pady=5)

    tk.Label(frame_filtros, text="Usuario:").grid(row=0, column=0, sticky="e")
    entry_usuario_filtro = tk.Entry(frame_filtros, width=15)
    entry_usuario_filtro.grid(row=0, column=1, padx=5, pady=2)

    tk.Label(frame_filtros, text="Desde (YYYY-MM-DD):").grid(row=0, column=2, sticky="e")
    entry_fecha_desde = tk.Entry(frame_filtros, width=12)
    entry_fecha_desde.grid(row=0, column=3, padx=5, pady=2)

    tk.Label(frame_filtros, text="Hasta (YYYY-MM-DD):").grid(row=0, column=4, sticky="e")
    entry_fecha_hasta = tk.Entry(frame_filtros, width=12)
    entry_fecha_hasta.grid(row=0, column=5, padx=5, pady=2)

    btn_aplicar = tk.Button(frame_filtros, text="Aplicar filtro")
    btn_aplicar.grid(row=0, column=6, padx=10)

    frame_tabla = tk.Frame(ventana)
    frame_tabla.pack(fill="both", expand=True, padx=10, pady=5)

    columnas = ("fecha", "usuario", "id_producto", "nombre", "cantidad", "precio_unitario", "total")
    tree_historial = ttk.Treeview(frame_tabla, columns=columnas, show="headings")

    encabezados = ["Fecha", "Usuario", "ID producto", "Nombre", "Cantidad", "Precio unit.", "Total"]
    for col, text in zip(columnas, encabezados):
        tree_historial.heading(col, text=text)

    tree_historial.column("fecha", width=140)
    tree_historial.column("usuario", width=90)
    tree_historial.column("id_producto", width=80)
    tree_historial.column("nombre", width=150)
    tree_historial.column("cantidad", width=80)
    tree_historial.column("precio_unitario", width=90)
    tree_historial.column("total", width=90)

    scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree_historial.yview)
    tree_historial.configure(yscroll=scrollbar.set)
    tree_historial.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def cargar_ventas():
        filtro_usuario = entry_usuario_filtro.get().strip()
        fecha_desde_str = entry_fecha_desde.get().strip()
        fecha_hasta_str = entry_fecha_hasta.get().strip()

        fecha_desde = None
        fecha_hasta = None

        try:
            if fecha_desde_str:
                fecha_desde = datetime.datetime.strptime(fecha_desde_str, "%Y-%m-%d")
            if fecha_hasta_str:
                fecha_hasta = datetime.datetime.strptime(fecha_hasta_str, "%Y-%m-%d")
                fecha_hasta = fecha_hasta.replace(hour=23, minute=59, second=59)
        except ValueError:
            messagebox.showerror(
                "Formato de fecha incorrecto",
                "Usa el formato YYYY-MM-DD, por ejemplo: 2025-01-31",
                parent=ventana
            )
            return

        try:
            ventas = obtener_ventas(
                filtro_usuario=filtro_usuario or None,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron cargar las ventas: {e}", parent=ventana)
            return

        for fila in tree_historial.get_children():
            tree_historial.delete(fila)

        for v in ventas:
            fecha = v.get("fecha")
            if isinstance(fecha, datetime.datetime):
                fecha_str = fecha.strftime("%Y-%m-%d %H:%M")
            else:
                fecha_str = str(fecha)

            tree_historial.insert(
                "",
                tk.END,
                values=(
                    fecha_str,
                    v.get("usuario", ""),
                    v.get("id_producto", ""),
                    v.get("nombre", ""),
                    v.get("cantidad", ""),
                    v.get("precio_unitario", ""),
                    v.get("total", ""),
                )
            )

    btn_aplicar.config(command=cargar_ventas)
    cargar_ventas()


def boton_registrar_usuario():
    global usuario_actual

    if usuario_actual is None:
        messagebox.showerror("Error", "No hay un usuario autenticado.")
        return

    nuevo_user = entry_nuevo_usuario.get().strip()
    nueva_pass = entry_nueva_contrasena.get().strip()

    if not nuevo_user or not nueva_pass:
        messagebox.showwarning("Campos vacíos", "Debes escribir usuario y contraseña.")
        return

    try:
        crear_usuario(nuevo_user, nueva_pass, creado_por=usuario_actual)
        messagebox.showinfo(
            "Usuario creado",
            f"El usuario '{nuevo_user}' fue creado por '{usuario_actual}'."
        )
        entry_nuevo_usuario.delete(0, tk.END)
        entry_nueva_contrasena.delete(0, tk.END)
    except ValueError as ve:
        messagebox.showerror("Datos inválidos", str(ve))
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo crear el usuario: {e}")


def boton_cerrar_sesion():
    """Cierra sesión y termina el programa."""
    global root
    confirmar = messagebox.askyesno(
        "Cerrar sesión",
        "¿Deseas cerrar sesión y salir del programa?"
    )
    if confirmar:
        root.destroy()


def construir_interfaz():
    global root
    global entry_id, entry_nombre, combo_categoria, entry_precio, entry_cantidad, entry_proveedor
    global entry_buscar, combo_criterio, entry_cantidad_venta, label_total_venta, tree
    global entry_nuevo_usuario, entry_nueva_contrasena, label_usuario_actual
    global usuario_actual

    root = tk.Tk()
    root.title("Sistema de Inventario - Tienda de Informática Proyecto Final Instituto Tecnologico de Morelia")
    root.geometry("950x680")

    frame_sesion = tk.Frame(root, padx=10, pady=5)
    frame_sesion.grid(row=0, column=0, columnspan=2, sticky="ew")

    label_usuario_actual = tk.Label(
        frame_sesion,
        text=f"Usuario actual: {usuario_actual}",
        font=("Arial", 10, "bold")
    )
    label_usuario_actual.pack(side="left")

    btn_cerrar = tk.Button(frame_sesion, text="Cerrar sesión", command=boton_cerrar_sesion)
    btn_cerrar.pack(side="right")

    frame_form = tk.LabelFrame(root, text="Datos del producto", padx=10, pady=10)
    frame_form.grid(row=1, column=0, padx=10, pady=10, sticky="nw")

    tk.Label(frame_form, text="ID producto:").grid(row=0, column=0, sticky="e")
    entry_id = tk.Entry(frame_form, width=10)
    entry_id.grid(row=0, column=1, padx=5, pady=2)

    tk.Label(frame_form, text="Nombre:").grid(row=1, column=0, sticky="e")
    entry_nombre = tk.Entry(frame_form, width=30)
    entry_nombre.grid(row=1, column=1, padx=5, pady=2)

    tk.Label(frame_form, text="Categoría:").grid(row=2, column=0, sticky="e")
    combo_categoria = ttk.Combobox(frame_form, values=CATEGORIAS, state="readonly", width=27)
    combo_categoria.grid(row=2, column=1, padx=5, pady=2)

    tk.Label(frame_form, text="Precio:").grid(row=3, column=0, sticky="e")
    entry_precio = tk.Entry(frame_form, width=10)
    entry_precio.grid(row=3, column=1, padx=5, pady=2, sticky="w")

    tk.Label(frame_form, text="Cantidad:").grid(row=4, column=0, sticky="e")
    entry_cantidad = tk.Entry(frame_form, width=10)
    entry_cantidad.grid(row=4, column=1, padx=5, pady=2, sticky="w")

    tk.Label(frame_form, text="Proveedor:").grid(row=5, column=0, sticky="e")
    entry_proveedor = tk.Entry(frame_form, width=30)
    entry_proveedor.grid(row=5, column=1, padx=5, pady=2)

    frame_botones = tk.Frame(frame_form)
    frame_botones.grid(row=6, column=0, columnspan=2, pady=10)

    tk.Button(frame_botones, text="Agregar", command=boton_agregar, width=10).grid(row=0, column=0, padx=5)
    tk.Button(frame_botones, text="Modificar", command=boton_modificar, width=10).grid(row=0, column=1, padx=5)
    tk.Button(frame_botones, text="Eliminar", command=boton_eliminar, width=10).grid(row=0, column=2, padx=5)
    tk.Button(frame_botones, text="Limpiar", command=limpiar_formulario, width=10).grid(row=0, column=3, padx=5)

    frame_busqueda = tk.LabelFrame(root, text="Búsqueda", padx=10, pady=10)
    frame_busqueda.grid(row=2, column=0, padx=10, pady=5, sticky="nw")

    tk.Label(frame_busqueda, text="Buscar por:").grid(row=0, column=0)
    combo_criterio = ttk.Combobox(
        frame_busqueda,
        values=["ID", "Nombre", "Proveedor", "Categoría"],
        state="readonly",
        width=12
    )
    combo_criterio.grid(row=0, column=1, padx=5)

    entry_buscar = tk.Entry(frame_busqueda, width=20)
    entry_buscar.grid(row=0, column=2, padx=5)

    tk.Button(frame_busqueda, text="Buscar", command=boton_buscar, width=10).grid(row=0, column=3, padx=5)
    tk.Button(frame_busqueda, text="Mostrar todo", command=boton_mostrar_todo, width=12).grid(row=0, column=4, padx=5)

    frame_tabla = tk.LabelFrame(root, text="Inventario", padx=10, pady=10)
    frame_tabla.grid(row=1, column=1, rowspan=3, padx=10, pady=10, sticky="nsew")

    columnas = ("id", "nombre", "categoria", "precio", "cantidad", "proveedor")

    tree = ttk.Treeview(frame_tabla, columns=columnas, show="headings", height=20)

    tree.heading("id", text="ID")
    tree.heading("nombre", text="Nombre")
    tree.heading("categoria", text="Categoría")
    tree.heading("precio", text="Precio")
    tree.heading("cantidad", text="Cantidad")
    tree.heading("proveedor", text="Proveedor")

    tree.column("id", width=50)
    tree.column("nombre", width=150)
    tree.column("categoria", width=100)
    tree.column("precio", width=80)
    tree.column("cantidad", width=80)
    tree.column("proveedor", width=120)

    scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)

    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    tree.bind("<<TreeviewSelect>>", llenar_formulario_desde_tabla)

    frame_tabla.rowconfigure(0, weight=1)
    frame_tabla.columnconfigure(0, weight=1)

    frame_ventas = tk.LabelFrame(root, text="Ventas y reportes", padx=10, pady=10)
    frame_ventas.grid(row=3, column=0, padx=10, pady=10, sticky="sw")

    tk.Label(frame_ventas, text="Cantidad a vender:").grid(row=0, column=0, sticky="e")
    entry_cantidad_venta = tk.Entry(frame_ventas, width=10)
    entry_cantidad_venta.grid(row=0, column=1, padx=5, pady=2)

    tk.Button(frame_ventas, text="Realizar venta", command=boton_realizar_venta, width=12).grid(row=0, column=2, padx=5)

    label_total_venta = tk.Label(frame_ventas, text="Total de la venta: $0.00")
    label_total_venta.grid(row=1, column=0, columnspan=3, pady=5)

    tk.Button(frame_ventas, text="Stock bajo", command=boton_reporte_stock_bajo, width=12).grid(row=2, column=0, padx=5, pady=5)
    tk.Button(frame_ventas, text="Valor inventario", command=boton_reporte_valor_total, width=14).grid(row=2, column=1, padx=5, pady=5)
    tk.Button(
        frame_ventas,
        text="Historial ventas",
        command=abrir_ventana_historial,
        width=14
    ).grid(row=2, column=2, padx=5, pady=5)

    frame_usuarios = tk.LabelFrame(root, text="Gestión de usuarios", padx=10, pady=10)
    frame_usuarios.grid(row=4, column=0, padx=10, pady=10, sticky="sw")

    tk.Label(frame_usuarios, text="Nuevo usuario:").grid(row=1, column=0, sticky="e")
    entry_nuevo_usuario = tk.Entry(frame_usuarios, width=20)
    entry_nuevo_usuario.grid(row=1, column=1, padx=5, pady=2)

    tk.Label(frame_usuarios, text="Nueva contraseña:").grid(row=2, column=0, sticky="e")
    entry_nueva_contrasena = tk.Entry(frame_usuarios, width=20, show="*")
    entry_nueva_contrasena.grid(row=2, column=1, padx=5, pady=2)

    tk.Button(
        frame_usuarios,
        text="Registrar usuario",
        command=boton_registrar_usuario,
        width=16
    ).grid(row=3, column=0, columnspan=2, pady=5)

    actualizar_tabla()


def menu_principal():
    construir_interfaz()
    root.mainloop()


# --- Ventana de bienvenida + login ----------------------------------- #

def mostrar_login():
    """
    Muestra una ventana de bienvenida y pide usuario/contraseña.
    Si el login es correcto, abre la ventana principal.
    """
    global usuario_actual

    login_root = tk.Tk()
    login_root.title("Acceso al Sistema de Inventario")
    login_root.geometry("500x300")

    messagebox.showinfo(
        "Bienvenida",
        "Bienvenido al Sistema de Inventario.\n\nPor favor inicia sesión.",
        parent=login_root
    )

    tk.Label(
        login_root,
        text="Bienvenido al Sistema de Inventario",
        font=("Arial", 11, "bold")
    ).pack(pady=10)

    frame_login = tk.Frame(login_root)
    frame_login.pack(pady=10)

    tk.Label(frame_login, text="Usuario:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
    entry_usuario = tk.Entry(frame_login, width=25)
    entry_usuario.grid(row=0, column=1, padx=5, pady=5)

    tk.Label(frame_login, text="Contraseña:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
    entry_contrasena = tk.Entry(frame_login, width=25, show="*")
    entry_contrasena.grid(row=1, column=1, padx=5, pady=5)

    tk.Label(
        login_root,
        text="Designed by Isaac,Yhosvani,Diana,Marinelly and Ramon (si compila :) )",
        fg="gray"
    ).pack()

    entry_usuario.focus_set()
    login_root.after(100, lambda: entry_usuario.focus_force())

    def intentar_login():
        global usuario_actual

        usuario = entry_usuario.get().strip()
        contrasena = entry_contrasena.get().strip()

        if not usuario or not contrasena:
            messagebox.showwarning("Campos vacíos", "Debes escribir usuario y contraseña.", parent=login_root)
            return

        try:
            user_doc = validar_login(usuario, contrasena)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo validar el usuario: {e}", parent=login_root)
            return

        if user_doc:
            usuario_actual = user_doc["username"]
            messagebox.showinfo("Bienvenido", f"Bienvenido, {usuario_actual}", parent=login_root)
            login_root.destroy()
            menu_principal()
        else:
            messagebox.showerror("Acceso denegado", "Usuario o contraseña incorrectos.", parent=login_root)

    def cerrar_programa():
        login_root.destroy()

    frame_botones_login = tk.Frame(login_root)
    frame_botones_login.pack(pady=10)

    tk.Button(frame_botones_login, text="Ingresar", width=10, command=intentar_login).grid(row=0, column=0, padx=5)
    tk.Button(frame_botones_login, text="Salir", width=10, command=cerrar_programa).grid(row=0, column=1, padx=5)

    login_root.bind("<Return>", lambda event: intentar_login())

    login_root.mainloop()


if __name__ == "__main__":
    mostrar_login()
