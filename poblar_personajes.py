import requests
import sqlite3
import json
import os
import time
from collections import Counter

# === CONFIGURACION ===
DB_PATH = "database.db"
CACHE_PATH = "gelbooru_cache.json"
LIMITE_TOTAL_PERSONAJES = 37000  # Puedes cambiarlo a 1000, 5000, etc.
IMAGENES_POR_PERSONAJE = 50

# === FUNCIONES ===

def cargar_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {}

def guardar_cache(cache):
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4)

def actualizar_cache(nombre_personaje, serie, nuevas_imagenes):
    cache = cargar_cache()
    clave = f"{nombre_personaje.lower()}::{serie.lower()}"
    actuales = cache.get(clave, [])

    for url in nuevas_imagenes:
        if url not in actuales:
            actuales.append(url)

    cache[clave] = actuales
    guardar_cache(cache)

def obtener_personajes_populares(limite_total=500):
    personajes = []
    pagina = 1

    while len(personajes) < limite_total:
        print(f"🌐 Consultando personajes populares, página {pagina}...")
        url = f"https://danbooru.donmai.us/tags.json?search[category]=4&search[order]=count&limit=100&page={pagina}"
        respuesta = requests.get(url)

        if respuesta.status_code != 200:
            print("❌ Error buscando personajes populares.")
            break

        tags = respuesta.json()
        if not tags:
            print("⚠️ No hay más personajes disponibles.")
            break

        for tag in tags:
            nombre_tag = tag.get("name", "")
            if nombre_tag:
                personajes.append(nombre_tag)
            if len(personajes) >= limite_total:
                break

        pagina += 1
        time.sleep(1)

    return personajes

def buscar_imagenes_personaje(nombre_tag, maximo=50):
    url = f"https://danbooru.donmai.us/posts.json?tags={nombre_tag}&limit={maximo}"
    respuesta = requests.get(url)
    imagenes = []
    series_detectadas = []

    if respuesta.status_code == 200:
        posts = respuesta.json()
        for post in posts:
            if post.get("file_url"):
                imagenes.append(post["file_url"])
            if post.get("tag_string_copyright"):
                series_tags = post["tag_string_copyright"].split(" ")
                series_detectadas.extend(series_tags)

    return imagenes, series_detectadas

def insertar_personaje(nombre, serie, imagen_url, valor):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO items (nombre, serie, rareza, genero, imagen_url, probabilidad, reclamado, valor)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        nombre.replace("_", " ").title(),
        serie.replace("_", " ").title(),
        "COMUN",
        "Unknown",
        imagen_url,
        0.4,
        0,
        valor
    ))

    conn.commit()
    conn.close()

# === EJECUCION PRINCIPAL ===

print("🚀 Iniciando generación de personajes REALES con paginación...")

personajes = obtener_personajes_populares(LIMITE_TOTAL_PERSONAJES)

for idx, personaje in enumerate(personajes, start=1):
    print(f"🔍 Buscando imágenes para {personaje} ({idx}/{len(personajes)})...")
    imagenes, series_detectadas = buscar_imagenes_personaje(personaje, maximo=IMAGENES_POR_PERSONAJE)

    if imagenes:
        imagen_principal = imagenes[0]
        if series_detectadas:
            conteo_series = Counter(series_detectadas)
            serie_mas_comun = conteo_series.most_common(1)[0][0]
        else:
            serie_mas_comun = "Desconocida"

        valor = 10000 - idx * 5
        valor = max(valor, 500)

        insertar_personaje(personaje, serie_mas_comun, imagen_principal, valor)
        actualizar_cache(personaje.replace("_", " "), serie_mas_comun.replace("_", " "), imagenes)
        print(f"✅ {personaje} agregado a database y galería actualizada.")
    else:
        print(f"⚠️ No se encontraron imágenes para {personaje}.")

    time.sleep(1)

print("🏁 Finalizado. Todos los personajes y galerías actualizadas.")
