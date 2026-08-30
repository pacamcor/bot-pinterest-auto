import os
import random
import json
import uuid
import requests
from google import genai

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
AMAZON_TAG = os.environ.get("AMAZON_TAG")
AUTH_COOKIE = os.environ.get("PINTEREST_AUTH")
CSRF_ENV = os.environ.get("PINTEREST_CSRF")

BOARD_ID = "1024920965106243873"

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
1. Un titular persuasivo (máximo 6 palabras).
2. Una descripción persuasiva para compra con hashtags (máximo 25 palabras).
Formato estricto:
TITULAR: [tu titular]
DESCRIPCION: [tu descripcion]
"""

# Textos por defecto si hay saturación temporal en la API
titular = prod["nombre"][:50]
descripcion = f"Descubre {prod['nombre']}. La mejor opción en calidad y diseño para tu hogar. ¡Encuéntralo en Amazon! #hogar #ofertas"

try:
    client = genai.Client(api_key=GEMINI_KEY)
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )
    if response and response.text:
        res = response.text
        if "TITULAR:" in res and "DESCRIPCION:" in res:
            titular = res.split("TITULAR:")[1].split("DESCRIPCION:")[0].strip()
            descripcion = res.split("DESCRIPCION:")[1].strip()
except Exception as e:
    print(f"Aviso en llamada Gemini (usando texto de respaldo): {e}")

print(f"-> Titular final: {titular}")
print(f"-> Enlace final: {link_afiliado}")

# Inyección del token CSRF en cookies y cabeceras
csrf_token = CSRF_ENV.strip() if CSRF_ENV else uuid.uuid4().hex
session = requests.Session()

dominios = [".pinterest.com", "www.pinterest.com", "pinterest.com", ".pinterest.es", "www.pinterest.es"]
for d in dominios:
    session.cookies.set("_pinterest_sess", AUTH_COOKIE, domain=d)
    session.cookies.set("_auth", "1", domain=d)
    session.cookies.set("csrftoken", csrf_token, domain=d)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.pinterest.com/",
    "Origin": "https://www.pinterest.com",
    "X-CSRFToken": csrf_token,
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
}

# Publicar el Pin en Pinterest
create_url = "https://www.pinterest.com/resource/PinResource/create/"
payload = {
    "options": {
        "board_id": BOARD_ID,
        "image_url": prod["imagen"],
        "title": titular,
        "description": descripcion,
        "link": link_afiliado
    },
    "context": {}
}

resp = session.post(create_url, headers=headers, data={"data": json.dumps(payload)})

try:
    resp_json = resp.json()
    if "resource_response" in resp_json and "data" in resp_json["resource_response"]:
        pin_id = resp_json["resource_response"]["data"].get("id")
        print(f"¡ÉXITO TOTAL! Pin publicado con ID: {pin_id}")
        print(f"Ver Pin en: https://www.pinterest.com/pin/{pin_id}/")
    else:
        print("Respuesta devuelta por Pinterest:")
        print(json.dumps(resp_json, indent=2))
        exit(1)
except Exception:
    print(f"Respuesta raw ({resp.status_code}): {resp.text[:300]}")
    exit(1)
