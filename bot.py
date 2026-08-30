import os
import random
import json
import requests
from google import genai

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
AMAZON_TAG = os.environ.get("AMAZON_TAG")
AUTH_COOKIE = os.environ.get("PINTEREST_AUTH")

client = genai.Client(api_key=GEMINI_KEY)

PRODUCTOS = [
    {
        "nombre": "Organizador de escritorio de madera multifuncional",
        "asin": "B08N5WRWNW",
        "imagen": "https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=800&q=80",
    },
    {
        "nombre": "Lámpara LED minimalista con base de carga rápida",
        "asin": "B09X123456",
        "imagen": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=800&q=80",
    },
    {
        "nombre": "Difusor de aceites esenciales ultrasónico con luz cálida",
        "asin": "B07V987654",
        "imagen": "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?auto=format&fit=crop&w=800&q=80",
    }
]

prod = random.choice(PRODUCTOS)
link_afiliado = f"https://www.amazon.es/dp/{prod['asin']}?tag={AMAZON_TAG}"

prompt = f"""
Crea para Pinterest sobre '{prod['nombre']}':
1. Un titular llamativo (máximo 6 palabras).
2. Una descripción persuasiva para compra con hashtags (máximo 25 palabras).
Formato estricto:
TITULAR: [tu titular]
DESCRIPCION: [tu descripcion]
"""

response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=prompt,
)
res = response.text
titular = res.split("TITULAR:")[1].split("DESCRIPCION:")[0].strip()
descripcion = res.split("DESCRIPCION:")[1].strip()

print(f"-> Titular: {titular}")
print(f"-> Enlace: {link_afiliado}")

# Configurar sesión con cookies
session = requests.Session()
session.cookies.set("_pinterest_sess", AUTH_COOKIE, domain=".pinterest.com")
session.cookies.set("_auth", "1", domain=".pinterest.com")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.pinterest.es/",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Origin": "https://www.pinterest.es"
}

# Obtener token CSRF y tableros
init_res = session.get("https://www.pinterest.es/", headers=headers)
csrf = session.cookies.get("csrftoken") or "123456"
headers["X-CSRFToken"] = csrf

boards_url = "https://www.pinterest.com/resource/BoardsResource/get/"
params = {"source_url": "/", "data": '{"options":{},"context":{}}'}
r = session.get(boards_url, headers=headers, params=params)

board_id = None
try:
    data = r.json()
    boards = data.get("resource_response", {}).get("data", [])
    if boards:
        board_id = str(boards[0]["id"])
        print(f"-> Tablero seleccionado: {boards[0].get('name')} (ID: {board_id})")
    else:
        print(f"Respuesta de tableros: {json.dumps(data)[:300]}")
except Exception as e:
    print(f"Error al leer tableros: {e}")

if not board_id:
    print("ERROR: No se encontró ningún tablero disponible en la cuenta.")
    exit(1)

# Publicar el Pin
create_url = "https://www.pinterest.com/resource/PinResource/create/"
payload = {
    "options": {
        "board_id": board_id,
        "image_url": prod["imagen"],
        "title": titular,
        "description": descripcion,
        "link": link_afiliado
    },
    "context": {}
}

resp = session.post(create_url, headers=headers, data={"data": json.dumps(payload)})
resp_json = resp.json()

if "resource_response" in resp_json and "data" in resp_json["resource_response"]:
    pin_id = resp_json["resource_response"]["data"].get("id")
    print(f"¡ÉXITO! Pin publicado correctamente con ID: {pin_id}")
    print(f"Ver Pin en: https://www.pinterest.es/pin/{pin_id}/")
else:
    print("ERROR al crear el pin. Respuesta del servidor:")
    print(json.dumps(resp_json, indent=2))
    exit(1)
