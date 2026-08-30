import os
import random
import json
import uuid
import re
import requests
import xml.etree.ElementTree as ET
from google import genai

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
AMAZON_TAG = os.environ.get("AMAZON_TAG")
AUTH_COOKIE = os.environ.get("PINTEREST_AUTH")
CSRF_ENV = os.environ.get("PINTEREST_CSRF")

USERNAME = "phantowncontact"
BOARD_SLUG = "ofertas-top"

FEEDS = [
    "https://www.chollometro.com/rss/tendencias",
    "https://www.chollometro.com/rss/nuevos",
    "https://www.chollometro.com/rss/categoria/electronica"
]

def obtener_producto_real():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    
    random.shuffle(FEEDS)
    for feed_url in FEEDS:
        try:
            r = requests.get(feed_url, headers=headers, timeout=10)
            if r.status_code != 200:
                continue
            
            root = ET.fromstring(r.content)
            items = root.findall(".//item")
            random.shuffle(items)
            
            for item in items:
                title = item.find("title").text if item.find("title") is not None else ""
                desc = item.find("description").text if item.find("description") is not None else ""
                
                asin_match = re.search(r'amazon\.es/(?:dp|gp/product)/([A-Z0-9]{10})', desc + " " + title)
                if not asin_match:
                    asin_match = re.search(r'\b([B0-9][A-Z0-9]{9})\b', desc)
                
                img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc)
                imagen_url = img_match.group(1) if img_match else None
                
                if asin_match and imagen_url:
                    asin = asin_match.group(1)
                    nombre_limpio = re.sub(r'\[.*?\]|\(.*?\)', '', title).strip()
                    nombre_limpio = nombre_limpio.split(" - ")[0].strip()
                    return {
                        "nombre": nombre_limpio,
                        "asin": asin,
                        "imagen": imagen_url
                    }
        except Exception as e:
            print(f"Aviso leyendo feed ({feed_url}): {e}")
            continue

    return {
        "nombre": "Echo Dot 5ª generación Altavoz inteligente con Alexa",
        "asin": "B09B8V1LZ3",
        "imagen": "https://images.unsplash.com/photo-1543512214-318c7553f230?auto=format&fit=crop&w=800&q=80"
    }

# 1. Obtener producto
prod = obtener_producto_real()
tag = AMAZON_TAG.strip() if AMAZON_TAG else "tutienda-21"
link_afiliado = f"https://www.amazon.es/dp/{prod['asin']}?tag={tag}"

print(f"-> Producto detectado: {prod['nombre']}")
print(f"-> ASIN real de Amazon: {prod['asin']}")
print(f"-> Enlace generado: {link_afiliado}")

# 2. Generar textos con Gemini
prompt = f"""
Crea para Pinterest sobre el producto '{prod['nombre']}':
1. Un titular persuasivo (máximo 6 palabras).
2. Una descripción persuasiva para compra con hashtags (máximo 25 palabras).
Formato estricto:
TITULAR: [tu titular]
DESCRIPCION: [tu descripcion]
"""

titular = prod["nombre"][:50]
descripcion = f"¡Gran oferta en {prod['nombre']}! Calidad y funcionalidad top. Haz clic para ver el precio en Amazon. #ofertas #compras #amazon"

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
    print(f"Aviso en llamada Gemini: {e}")

print(f"-> Titular final: {titular}")

# 3. Sesión y autenticación
csrf_token = CSRF_ENV.strip() if CSRF_ENV else uuid.uuid4().hex
session = requests.Session()

dominios = [".pinterest.com", "www.pinterest.com", "pinterest.com", ".pinterest.es", "www.pinterest.es", "es.pinterest.com"]
for d in dominios:
    session.cookies.set("_pinterest_sess", AUTH_COOKIE, domain=d)
    session.cookies.set("_auth", "1", domain=d)
    session.cookies.set("csrftoken", csrf_token, domain=d)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": f"https://www.pinterest.es/{USERNAME}/{BOARD_SLUG}/",
    "Origin": "https://www.pinterest.es",
    "X-CSRFToken": csrf_token,
    "X-Requested-With": "XMLHttpRequest"
}

# 4. Obtener ID del tablero
board_url = "https://www.pinterest.es/resource/BoardResource/get/"
board_payload = {
    "options": {
        "slug": BOARD_SLUG,
        "username": USERNAME
    },
    "context": {}
}

board_resp = session.post(board_url, headers={**headers, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, data={"data": json.dumps(board_payload)})
board_id = None

try:
    board_json = board_resp.json()
    board_id = board_json.get("resource_response", {}).get("data", {}).get("id")
except Exception as e:
    print(f"Error parseando tablero: {e}")

if not board_id:
    board_id = "1024920896388540341"

# 5. Descargar imagen y subirla como archivo a Pinterest
img_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
img_data = requests.get(prod["imagen"], headers=img_headers, timeout=10).content

upload_url = "https://www.pinterest.es/upload-image/"
files = {"img": ("image.jpg", img_data, "image/jpeg")}
upload_resp = session.post(upload_url, headers=headers, files=files)

uploaded_image_url = None
try:
    upload_json = upload_resp.json()
    uploaded_image_url = upload_json.get("image_url") or upload_json.get("success")
except Exception:
    pass

# Si no devolvió URL interna de carga, usar la URL directa de la imagen
final_image = uploaded_image_url if uploaded_image_url and isinstance(uploaded_image_url, str) else prod["imagen"]

# 6. Publicar Pin
create_url = "https://www.pinterest.es/resource/PinResource/create/"
payload = {
    "options": {
        "board_id": str(board_id),
        "image_url": final_image,
        "title": titular,
        "description": descripcion,
        "link": link_afiliado
    },
    "context": {}
}

resp = session.post(create_url, headers={**headers, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, data={"data": json.dumps(payload)})

try:
    resp_json = resp.json()
    if "resource_response" in resp_json and "data" in resp_json["resource_response"]:
        pin_id = resp_json["resource_response"]["data"].get("id")
        print(f"¡ÉXITO TOTAL! Pin publicado con ID: {pin_id}")
        print(f"Ver Pin en: https://www.pinterest.es/pin/{pin_id}/")
    else:
        print("Respuesta de Pinterest:")
        print(json.dumps(resp_json, indent=2))
        exit(1)
except Exception:
    print(f"Respuesta raw ({resp.status_code}): {resp.text[:300]}")
    exit(1)
