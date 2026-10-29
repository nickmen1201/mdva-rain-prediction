import csv
import unicodedata

import requests
from bs4 import BeautifulSoup


def quitar_acentos(texto):
    """
    Convierte texto con acentos a su versión sin acentos (ASCII-friendly).
    Ej: "José" → "Jose", "niño" → "nino", "Sebastián" → "Sebastian"
    """
    # Normaliza y elimina marcas diacríticas
    texto_normalizado = unicodedata.normalize("NFD", texto)
    sin_acentos = "".join(c for c in texto_normalizado if unicodedata.category(c) != "Mn")
    # Reemplazos adicionales comunes en español colombiano
    sin_acentos = sin_acentos.replace("ñ", "n").replace("Ñ", "N")
    return sin_acentos


url = "https://www.medellin.gov.co/irj/portal/medellin?NavigationTarget=contenido/11871-Perfiles-Demograficos-por-Comuna-y-Barrios-2016-2020"

response = requests.get(url)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
texto = soup.get_text(separator="\n")

# Limpiamos el texto completo de acentos desde el principio
texto = quitar_acentos(texto)

secciones = texto.split("Perfiles demograficos Por Barrio")[1:]

barrios_data = []

for sec in secciones:
    sec = sec.strip()
    if not sec:
        continue

    lineas = [ln.strip() for ln in sec.split("\n") if ln.strip() != ""]
    if not lineas:
        continue

    encabezado = lineas[0]

    try:
        parte_id, parte_nombre = encabezado.split(" - ", 1)
        id_comuna_raw = parte_id.strip().split()[-1].zfill(2)
        id_comuna = f"MED{id_comuna_raw}"
    except (ValueError, IndexError):
        continue

    for linea in lineas[1:]:
        if linea.startswith("Barrio"):
            try:
                _, cod_y_nombre = linea.split(" ", 1)
                id_barrio_raw, nombre_barrio = cod_y_nombre.split(" - ", 1)

                id_barrio = f"MED{id_barrio_raw.strip()}"
                # ← Aquí quitamos acentos al nombre del barrio
                nombre_barrio_limpio = quitar_acentos(nombre_barrio.strip())

                barrios_data.append({"id_barrio": id_barrio, "Nombre": nombre_barrio_limpio, "id_comuna": id_comuna})
            except ValueError:
                pass

# 🔵 Agregar corregimientos (también sin acentos)
corregimientos = ["San Sebastian de Palmitas", "San Cristobal", "Altavista", "San Antonio de Prado", "Santa Elena"]

for i, nombre in enumerate(corregimientos, start=1):
    id_corregimiento = f"MEDC{str(i).zfill(2)}"
    # ← Quitamos acentos también aquí
    nombre_limpio = quitar_acentos(nombre)

    barrios_data.append(
        {"id_barrio": id_corregimiento, "Nombre": f"Barrios_{nombre_limpio}", "id_comuna": id_corregimiento}
    )

# 📁 Exportar CSV (con encoding utf-8, pero ahora el contenido ya no tiene caracteres problemáticos)
with open("barrios.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id_barrio", "Nombre", "id_comuna"])

    for b in barrios_data:
        writer.writerow([b["id_barrio"], b["Nombre"], b["id_comuna"]])

print(f"Exportados {len(barrios_data)} registros incluyendo corregimientos.")
