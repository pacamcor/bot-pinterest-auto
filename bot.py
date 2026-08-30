import os
import random
import json
import uuid
import re
import requests
from bs4 import BeautifulSoup
from google import genai

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
AMAZON_TAG = os.environ.get("AMAZON_TAG")
AUTH_COOKIE = os.environ.get("PINTEREST_AUTH")
CSRF_ENV = os.environ.get("PINTEREST_CSRF")

USERNAME = "phantowncontact"
BOARD_SLUG = "ofertas-top"

TERMINOS_BUSQUEDA = [
    "gadgets hogar utiles",
    "accesorios escritorio setup",
    "organizadores hogar",
    "lampara led inteligente",
    "freidora de aire accesorios",
    "humificador difusor aromaterapia",
    "soporte movil mesa"
]

def obtener_producto_amazon():
    """Busca productos activos reales directamente en Amazon España."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    terminos = list(TERMINOS_BUSQUEDA)
    random.shuffle(terminos)
    
    for query in terminos:
        try:
            url = f"https://www.amazon.es/s?k={requests.utils.quote(query)}"
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code != 200:
                continue
            
            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.find_all("div", {"data-asin": True})
            
            validos = []
            for item in items:
                asin = item.get("data-asin", "").strip()
                if not asin or len(asin) != 10:
                    continue
                
                # Obtener título e imagen
                title_elem = item.find("h2")
                img_elem = item.find("img", {"class": "s-image"})
                
                if title_elem and img_elem:
                    nombre = title_elem.text.strip()
                    img_src = img_elem.get("src", "")
                    if img_src and "m.media-amazon.com" in img_src:
                        validos.append({
                            "nombre": nombre,
                            "asin": asin,
                            "imagen": img_src
                        })
            
            if validos:
                elegido = random.choice(validos[:8])
                return elegido
        except Exception as e:
            print(f"Aviso buscando en Amazon ({query}): {e}")
            continue

    # Fallback con catálogo de ASINs verificados en Amazon España
    catalogo_garantizado = [
        {
            "nombre": "Echo Pop Altavoz inteligente compacto con Alexa",
            "asin": "B09WNK39JN",
            "imagen": "https://m.media-amazon.com/images/I/61l6e5+U6LL._AC_SL1000_.jpg"
        },
        {
            "nombre": "Fire TV Stick con mando por voz Alexa",
            "asin": "B08C17VSS9",
            "imagen": "https://m.media-amazon.com/images/I/51TjJOTfslL._AC_SL1000_.jpg"
        },
        {
            "nombre": "Blink Mini Cámara de seguridad inteligente compacta",
            "asin": "B07X37DT9M",
            "imagen": "https://m.media-amazon.com/images/I/61pB50c3HRL._AC_SL1000_.jpg"
        }
    ]
    return random.choice(catalogo_garantizado)

# 1. Obtener producto real
prod = obtener_producto_amazon()
tag = AMAZON_TAG.strip() if AMAZON_TAG else "tutienda-21"
link_afiliado = f"https://www.amazon.es/dp/{prod['asin']}?tag={tag}"

print(f"-> Producto detectado: {prod['nombre']}")
print(f"-> ASIN real de Amazon: {prod['asin']}")
print(f"-> Enlace generado: {link_afiliado}")

# 2. Generar textos persuasivos con Gemini
prompt = f"""
Crea para Pinterest sobre el producto '{prod['nombre']}':
1. Un titular persuasivo e irresistible (máximo 6 palabras).
2. Una descripción comercial orientada a compra con hashtags relevantes (máximo 25 palabras).
Formato estricto:
TITULAR: [tu titular]
DESCRIPCION: [tu descripcion]
"""

titular = prod["nombre"][:50]
descripcion = f"Descubre {prod['nombre']}. La mejor opción para tu hogar con envío rápido. ¡Haz clic para ver la oferta en Amazon! #hogar #ofertas #compras"

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

# 3. Sesión con Pinterest
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

# 5. Descargar y subir imagen como archivo directo a Pinterest
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

final_image = uploaded_image_url if uploaded_image_url and isinstance(uploaded_image_url, str) else prod["imagen"]

# 6. Publicar Pin con enlace de afiliado verificado
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
