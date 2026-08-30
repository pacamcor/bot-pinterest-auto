import os
import random
import requests
from google import genai

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
AMAZON_TAG = os.environ.get("AMAZON_TAG")
AUTH_COOKIE = os.environ.get("PINTEREST_AUTH")

client = genai.Client(api_key=GEMINI_KEY)

# Catálogo de productos
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

# 1. Generar textos con el modelo actualizado
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

print(f"-> Generando Pin: {titular}")

# 2. Configurar sesión de Pinterest con la cookie
session = requests.Session()
session.cookies.set("_pinterest_sess", AUTH_COOKIE, domain=".pinterest.com")
session.cookies.set("_auth", "1", domain=".pinterest.com")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.pinterest.es/",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01"
}

# Obtener tableros del usuario
boards_url = "https://www.pinterest.com/resource/BoardsResource/get/"
params = {"source_url": "/", "data": '{"options":{},"context":{}}'}

r = session.get(boards_url, headers=headers, params=params)
board_id = None

try:
    boards = r.json().get("resource_response", {}).get("data", [])
    if boards:
        board_id = boards[0]["id"]
        print(f"-> Tablero detectado: {boards[0].get('name')} (ID: {board_id})")
except Exception as e:
    print(f"Aviso al detectar tableros: {e}")

# Crear el Pin directamente
create_url = "https://www.pinterest.com/resource/PinResource/create/"
post_data = {
    "options": {
        "board_id": board_id,
        "image_url": prod["imagen"],
        "title": titular,
        "description": descripcion,
        "link": link_afiliado
    },
    "context": {}
}

resp = session.post(create_url, headers=headers, data={"data": str(post_data).replace("'", '"')})

if resp.status_code == 200:
    print("¡Pin publicado con éxito en tu tablero de Pinterest!")
else:
    print(f"Respuesta Pinterest ({resp.status_code}): {resp.text[:200]}")
