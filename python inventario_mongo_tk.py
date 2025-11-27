"""
Sistema de Inventario - Proyecto Final

- CRUD de productos()
- Registro de ventas (actualiza stock y muestra total)
- Reportes (stock bajo y valor total del inventario)
- Base de datos: MongoDB
- Interfaz gráfica: Tkinter

NOTA IMPORTANTE:
Antes de ejecutar este programa debes:
1) Instalar pymongo -> pip install pymongo
2) Tener el servidor de MongoDB corriendo en tu máquina.
"""

import tkinter as tk
from tkinter import ttk, messagebox

# Intentamos importar MongoClient.
# Si pymongo no está instalado, no tronamos el programa de inmediato
# para poder mostrar un mensaje más amigable luego.
try:
     from pymongo import MongoClient
except ImportError:
    MongoClient = None  # Variable sentinela: indica que no hay pymongo


# ---------------------- CONFIGURACIÓN DE MONGODB ---------------------- #

def conectar_mongodb():
    """
    Crea y devuelve la colección de productos en MongoDB.

    Separamos esta lógica en una función para que el código sea más fácil
    de leer y para poder reutilizarla si fuera necesario.
    """
    if MongoClient is None:
        # Este error le recuerda al usuario que debe instalar pymongo.
        raise ImportError(
            "La librería 'pymongo' no está instalada. "
            "Instálala con: pip install pymongo"
        )

    # URL de conexión local por defecto.
    # Si tu MongoDB está en otro host/puerto, cámbialo aquí.
    cliente = MongoClient("mongodb://localhost:27017/")

    # Nombre de la base de datos.
    db = cliente["tienda_informatica"]

    # Colección donde guardaremos los productos.
    coleccion = db["productos"]
    return coleccion


# Intentamos establecer la conexión al iniciar el programa.
try:
    coleccion_productos = conectar_mongodb()
except Exception as e:
    print("Error al conectar a MongoDB:", e)
    coleccion_productos = None  # De esta forma podemos checar luego si es None.


# ---------------------- CONSTANTES DEL SISTEMA ------------------------ #

# Lista simple de categorías permitidas.
CATEGORIAS = ["Computadoras", "Smartphones", "Accesorios", "Periféricos"]

# Umbral para considerar "stock bajo".
STOCK_MINIMO = 5


# ----------------- FUNCIONES DE LÓGICA DEL INVENTARIO ----------------- #

def agregar_producto(id_producto, nombre, categoria, precio, cantidad, proveedor):
    """
    Agrega un nuevo producto al inventario en MongoDB.

    Esta función NO toca la interfaz gráfica. Solo se encarga de la lógica
    de negocio (validaciones + guardado en la base de datos).
    """
    if coleccion_productos is None:
        raise RuntimeError("No hay conexión con la base de datos.")

    # Validaciones simples para evitar datos basura
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

    # Aseguramos que el ID sea único en la colección
    existente = coleccion_productos.find_one({"id_producto": id_producto})
    if existente:
        raise ValueError(f"Ya existe un producto con ID {id_producto}.")

    # Documento que se almacenará en MongoDB (diccionario)
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
    """
    Busca productos en la base de datos según el criterio.

    criterio: 'id', 'nombre', 'proveedor', 'categoria'
    valor: dato a buscar (string o número)

    Devuelve una lista de documentos (diccionarios).
    """
    if coleccion_productos is None:
        raise RuntimeError("No hay conexión con la base de datos.")

    filtro = {}

    # Dependiendo del criterio armamos el filtro de MongoDB.
    if criterio == "id":
        filtro["id_producto"] = int(valor)  # Convertimos a int para comparar correctamente.
    elif criterio == "nombre":
        # Usamos $regex para hacer una búsqueda que no distingue mayúsculas/minúsculas.
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
    """
    Modifica los datos de un producto existente.

    nuevos_datos: diccionario con las claves a actualizar, por ejemplo:
        {"nombre": "Nuevo", "precio": 150.0}
    """
    if coleccion_productos is None:
        raise RuntimeError("No hay conexión con la base de datos.")

    resultado = coleccion_productos.update_one(
        {"id_producto": id_producto},
        {"$set": nuevos_datos}
    )
    # matched_count indica cuántos documentos coincidieron con el filtro.
    return resultado.matched_count > 0


def eliminar_producto(id_producto):
    """
    Elimina un producto por su ID.
    """
    if coleccion_productos is None:
        raise RuntimeError("No hay conexión con la base de datos.")

    resultado = coleccion_productos.delete_one({"id_producto": id_producto})
    return resultado.deleted_count > 0


def mostrar_inventario():
    """
    Devuelve una lista con todos los productos del inventario,
    ordenados por ID.
    """
    if coleccion_productos is None:
        raise RuntimeError("No hay conexión con la base de datos.")

    productos = list(coleccion_productos.find().sort("id_producto", 1))
    return productos


def realizar_venta(id_producto, cantidad_vendida):
    """
    Registra una venta:
    - Verifica que exista el producto.
    - Verifica stock suficiente.
    - Descuenta del inventario.
    - Devuelve el total de la venta (precio * cantidad_vendida).
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

    # Actualizamos el stock en la base de datos
    coleccion_productos.update_one(
        {"id_producto": id_producto},
        {"$set": {"cantidad": nuevo_stock}}
    )

    total = cantidad_vendida * prod["precio"]

    # Aquí se podría guardar la venta en otra colección (ventas)
    # para tener historial, pero el requisito mínimo es actualizar inventario.
    return total


def generar_reporte():
    """
    Genera un reporte con:
    - Lista de productos con stock bajo.
    - Valor total del inventario.

    Devuelve (bajo_stock, valor_total)
    """
    if coleccion_productos is None:
        raise RuntimeError("No hay conexión con la base de datos.")

    productos = list(coleccion_productos.find())
    bajo_stock = []
    valor_total = 0.0

    for p in productos:
        # Acumulamos el valor total del inventario
        valor_total += p["cantidad"] * p["precio"]

        # Revisa si el producto está por debajo del STOCK_MINIMO
        if p["cantidad"] < STOCK_MINIMO:
            bajo_stock.append(p)

    return bajo_stock, valor_total


# --------------- VARIABLES GLOBALES DE LA INTERFAZ -------------------- #
# Nota: usar variables globales no es lo más elegante,
# pero para un proyecto escolar mantiene el código simple.

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


# ------------------- FUNCIONES DE LA INTERFAZ TKINTER ----------------- #

def limpiar_formulario():
    """
    Limpia las cajas de texto del formulario de producto.
    """
    entry_id.delete(0, tk.END)
    entry_nombre.delete(0, tk.END)
    combo_categoria.set("")
    entry_precio.delete(0, tk.END)
    entry_cantidad.delete(0, tk.END)
    entry_proveedor.delete(0, tk.END)


def llenar_formulario_desde_tabla(event):
    """
    Se dispara cuando el usuario selecciona una fila de la tabla (Treeview).
    Este tipo de función se llama "manejador de eventos".
    """
    seleccion = tree.selection()
    if not seleccion:
        return

    item_id = seleccion[0]
    # .item(..., "values") devuelve una tupla con los valores de la fila
    datos = tree.item(item_id, "values")

    # Los índices corresponden al orden de las columnas definidas en el Treeview.
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
    """
    Recarga los datos del Treeview.

    Si 'productos' es None, se consultan todos los productos (mostrar_inventario).
    Si se pasa una lista, se muestran solo esos.
    """
    # Borramos las filas actuales
    for fila in tree.get_children():
        tree.delete(fila)

    if productos is None:
        try:
            productos = mostrar_inventario()
        except RuntimeError as e:
            messagebox.showerror("Error", str(e))
            return

    # Insertamos los productos en la tabla
    for p in productos:
        tree.insert(
            "",             # '' indica que la fila no tiene "padre"
            tk.END,         # posición al final
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
    """
    Se ejecuta cuando el usuario presiona el botón "Agregar".
    Lee los datos de las cajas de texto y llama a agregar_producto().
    """
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
        # ValueError es una excepción típica para datos inválidos
        messagebox.showerror("Datos inválidos", str(ve))
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al agregar: {e}")


def boton_modificar():
    """
    Toma los valores de las cajas y actualiza el producto con ese ID.
    """
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
    """
    Elimina el producto cuyo ID esté escrito en la caja correspondiente.
    """
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
    """
    Realiza la búsqueda según el criterio elegido en el combobox
    y el texto ingresado en la caja respectiva.
    """
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
            actualizar_tabla([])  # Dejamos la tabla vacía
    except Exception as e:
        messagebox.showerror("Error", f"Ocurrió un error al buscar: {e}")


def boton_mostrar_todo():
    """
    Muestra todos los productos en la tabla.
    """
    actualizar_tabla()


def boton_realizar_venta():
    """
    Realiza una venta del producto seleccionado en la tabla,
    usando la cantidad indicada en la caja de texto de venta.
    """
    seleccion = tree.selection()
    if not seleccion:
        messagebox.showwarning("Aviso", "Selecciona un producto en la tabla.")
        return

    try:
        cantidad_vendida = int(entry_cantidad_venta.get())
    except ValueError:
        messagebox.showerror("Datos inválidos", "Escribe una cantidad entera para vender.")
        return

    # Tomamos el ID del primer elemento seleccionado
    item_id = seleccion[0]
    datos = tree.item(item_id, "values")
    id_producto = int(datos[0])

    try:
        total = realizar_venta(id_producto, cantidad_vendida)
        label_total_venta.config(text=f"Total de la venta: ${total:.2f}")
        messagebox.showinfo("Venta realizada", f"Venta registrada por ${total:.2f}")
        actualizar_tabla()
    except Exception as e:
        messagebox.showerror("Error", str(e))


def boton_reporte_stock_bajo():
    """
    Muestra en un cuadro de diálogo los productos con stock bajo.
    """
    try:
        bajo_stock, _ = generar_reporte()
        if not bajo_stock:
            messagebox.showinfo("Reporte", "No hay productos con stock bajo.")
            return

        lineas = []
        # Recorremos la lista de productos con stock bajo
        for p in bajo_stock:
            linea = f"ID {p['id_producto']} - {p['nombre']} (stock: {p['cantidad']})"
            lineas.append(linea)

        # Unimos todas las líneas en un solo string, separado por saltos de línea
        mensaje = "\n".join(lineas)
        messagebox.showinfo("Productos con stock bajo", mensaje)
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo generar el reporte: {e}")


def boton_reporte_valor_total():
    """
    Muestra el valor total del inventario en un mensaje emergente.
    """
    try:
        _, valor_total = generar_reporte()
        messagebox.showinfo("Valor del inventario", f"Valor total: ${valor_total:.2f}")
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo calcular el valor del inventario: {e}")


def construir_interfaz():
    """
    Crea todos los elementos de la ventana principal (Tkinter).

    Usamos 'global' para poder acceder a los widgets desde otras funciones.
    Esto no es lo más elegante, pero hace el código más simple para empezar.
    """
    global root
    global entry_id, entry_nombre, combo_categoria, entry_precio, entry_cantidad, entry_proveedor
    global entry_buscar, combo_criterio, entry_cantidad_venta, label_total_venta, tree

    root = tk.Tk()
    root.title("Sistema de Inventario - Tienda de Informática")
    root.geometry("950x600")  # tamaño inicial de la ventana

    # ---------------- Frame de formulario ---------------- #
    frame_form = tk.LabelFrame(root, text="Datos del producto", padx=10, pady=10)
    frame_form.grid(row=0, column=0, padx=10, pady=10, sticky="nw")

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

    # Sub-frame de botones CRUD
    frame_botones = tk.Frame(frame_form)
    frame_botones.grid(row=6, column=0, columnspan=2, pady=10)

    tk.Button(frame_botones, text="Agregar", command=boton_agregar, width=10).grid(row=0, column=0, padx=5)
    tk.Button(frame_botones, text="Modificar", command=boton_modificar, width=10).grid(row=0, column=1, padx=5)
    tk.Button(frame_botones, text="Eliminar", command=boton_eliminar, width=10).grid(row=0, column=2, padx=5)
    tk.Button(frame_botones, text="Limpiar", command=limpiar_formulario, width=10).grid(row=0, column=3, padx=5)

    # ---------------- Frame de búsqueda ---------------- #
    frame_busqueda = tk.LabelFrame(root, text="Búsqueda", padx=10, pady=10)
    frame_busqueda.grid(row=1, column=0, padx=10, pady=5, sticky="nw")

    tk.Label(frame_busqueda, text="Buscar por:").grid(row=0, column=0)
    combo_criterio = ttk.Combobox(frame_busqueda,
                                  values=["ID", "Nombre", "Proveedor", "Categoría"],
                                  state="readonly",
                                  width=12)
    combo_criterio.grid(row=0, column=1, padx=5)

    entry_buscar = tk.Entry(frame_busqueda, width=20)
    entry_buscar.grid(row=0, column=2, padx=5)

    tk.Button(frame_busqueda, text="Buscar", command=boton_buscar, width=10).grid(row=0, column=3, padx=5)
    tk.Button(frame_busqueda, text="Mostrar todo", command=boton_mostrar_todo, width=12).grid(row=0, column=4, padx=5)

    # ---------------- Frame de tabla ---------------- #
    frame_tabla = tk.LabelFrame(root, text="Inventario", padx=10, pady=10)
    frame_tabla.grid(row=0, column=1, rowspan=3, padx=10, pady=10, sticky="nsew")

    columnas = ("id", "nombre", "categoria", "precio", "cantidad", "proveedor")

    # Treeview es un widget tipo tabla de Tkinter (parte de ttk).
    tree = ttk.Treeview(frame_tabla, columns=columnas, show="headings", height=20)

    # Definimos los encabezados de cada columna
    tree.heading("id", text="ID")
    tree.heading("nombre", text="Nombre")
    tree.heading("categoria", text="Categoría")
    tree.heading("precio", text="Precio")
    tree.heading("cantidad", text="Cantidad")
    tree.heading("proveedor", text="Proveedor")

    # Ajustamos el ancho aproximado de cada columna
    tree.column("id", width=50)
    tree.column("nombre", width=150)
    tree.column("categoria", width=100)
    tree.column("precio", width=80)
    tree.column("cantidad", width=80)
    tree.column("proveedor", width=120)

    # Scrollbar vertical para la tabla
    scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)

    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")

    # Vinculamos el evento de selección de fila a la función llenar_formulario_desde_tabla
    tree.bind("<<TreeviewSelect>>", llenar_formulario_desde_tabla)

    # Para que el frame_tabla se expanda junto con la ventana
    frame_tabla.rowconfigure(0, weight=1)
    frame_tabla.columnconfigure(0, weight=1)

    # ---------------- Frame de ventas y reportes ---------------- #
    frame_ventas = tk.LabelFrame(root, text="Ventas y reportes", padx=10, pady=10)
    frame_ventas.grid(row=2, column=0, padx=10, pady=10, sticky="sw")

    tk.Label(frame_ventas, text="Cantidad a vender:").grid(row=0, column=0, sticky="e")
    entry_cantidad_venta = tk.Entry(frame_ventas, width=10)
    entry_cantidad_venta.grid(row=0, column=1, padx=5, pady=2)

    tk.Button(frame_ventas, text="Realizar venta", command=boton_realizar_venta, width=12).grid(row=0, column=2, padx=5)

    label_total_venta = tk.Label(frame_ventas, text="Total de la venta: $0.00")
    label_total_venta.grid(row=1, column=0, columnspan=3, pady=5)

    tk.Button(frame_ventas, text="Stock bajo", command=boton_reporte_stock_bajo, width=12).grid(row=2, column=0, padx=5, pady=5)
    tk.Button(frame_ventas, text="Valor inventario", command=boton_reporte_valor_total, width=14).grid(row=2, column=1, padx=5, pady=5)

    # Cargamos los datos iniciales de la base
    actualizar_tabla()


def menu_principal():
    """
    Función requerida por el proyecto.

    En lugar de un menú de consola, esta función inicia la interfaz gráfica
    y se encarga de mantenerla abierta.

    root.mainloop() es un "bucle de eventos":
    se queda escuchando clicks, teclazos, etc., hasta que cerramos la ventana.
    """
    construir_interfaz()
    root.mainloop()


# Si se ejecuta este archivo directamente (no importado como módulo), se corre el menú principal.
if __name__ == "__main__":
    menu_principal()
