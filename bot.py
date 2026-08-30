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
    # Gadgets y Tecnología Viral
    "gadgets tecnologicos utiles",
    "accesorios escritorio minimalista",
    "soporte movil cargador inalambrico",
    "auriculares cancelacion ruido ofertas",
    "reloj inteligente deportivo",
    "power bank carga rapida compacta",
    
    # Hogar, Organización y Limpieza
    "organizadores armario ropa",
    "cajas organizadoras transparentes",
    "estanteria modular cocina",
    "dispensador jabon automatico sensor",
    "perchas magicas espacio armario",
    "limpiador vapor portatil hogar",
    
    # Cocina y Gadgets Prácticos
    "accesorios freidora de aire cuadrados",
    "picadora verduras manual multifuncion",
    "sellador bolsas termico portatil",
    "bascula digital cocina precision",
    "dispensador agua electrico garrafa",
    "recipientes hermeticos cristal cocina",
    
    # Iluminación y Setup
    "tira led habitacion alexa",
    "lampara de pie moderna inteligente",
    "lampara mesa noche tactil calida",
    "luces sensor movimiento armario",
    "alfombrilla escritorio xxl cuero",
    "soporte monitor madera doble",
    
    # Confort y Bienestar
    "difusor aceites esenciales aromaterapia",
    "humidificador ultrasonico habitacion",
    "cojin ergonomico espuma memoria",
    "antifaz para dormir con auriculares bluetooth",
    "masajeador cervical cuello calor",
    "calentador de tazas usb escritorio"
]

def obtener_producto_con_oferta():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    terminos = list(TERMINOS_BUSQUEDA)
    random.shuffle(terminos)
    
    for query in terminos:
        try:
            url = f"https://www.amazon.es/s?k={requests.utils.quote(query)}&s=exact-aware-popularity-rank&pct-off=10-"
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
                
                title_elem = item.find("h2")
                img_elem = item.find("img", {"class": "s-image"})
                
                if not title_elem or not img_elem:
                    continue
                
                nombre = title_elem.text.strip()
                img_src = img_elem.get("src", "")
                
                if not img_src or "m.media-amazon.com" not in img_src:
                    continue
                
                # 1. Extraer Porcentaje de Rebaja (ej. -25%)
                badge_desc = item.find("span", string=re.compile(r'-\d+%'))
                descuento_pct = badge_desc.text.strip() if badge_desc else ""
                
                # 2. Extraer Precio Actual (Oferta)
                precio_actual = ""
                precio_actual_elem = item.find("span", {"class": "a-price"})
                if precio_actual_elem:
                    offscreen = precio_actual_elem.find("span", {"class": "a-offscreen"})
                    if offscreen and offscreen.text:
                        precio_actual = offscreen.text.strip()
                
                # 3. Extraer Precio Antiguo / Recomendado (Tachado)
                precio_antiguo = ""
                precio_tachado_elem = item.find("span", {"class": "a-text-price"})
                if precio_tachado_elem:
                    offscreen_old = precio_tachado_elem.find("span", {"class": "a-offscreen"})
                    if offscreen_old and offscreen_old.text:
                        precio_antiguo = offscreen_old.text.strip()
                
                # Construir frase de oferta atractiva
                if precio_actual and precio_antiguo and descuento_pct:
                    descuento_texto = f"¡Ahora {precio_actual}! (Antes {precio_antiguo} | {descuento_pct})"
                elif precio_actual and precio_antiguo:
                    descuento_texto = f"¡Ahora {precio_actual}! (Antes {precio_antiguo})"
                elif precio_actual and descuento_pct:
                    descuento_texto = f"¡Solo {precio_actual} ({descuento_pct} de descuento)!"
                elif precio_actual:
                    descuento_texto = f"¡En oferta por solo {precio_actual}!"
                else:
                    descuento_texto = "¡Oferta flash por tiempo limitado!"
                
                validos.append({
                    "nombre": nombre,
                    "asin": asin,
                    "imagen": img_src,
                    "oferta_info": descuento_texto,
                    "precio_actual": precio_actual,
                    "precio_antiguo": precio_antiguo
                })
            
            if validos:
                return random.choice(validos[:5])
        except Exception as e:
            print(f"Aviso buscando en Amazon ({query}): {e}")
            continue

    return {
        "nombre": "Blink Mini Cámara de seguridad inteligente compacta",
        "asin": "B07X37DT9M",
        "imagen": "https://m.media-amazon.com/images/I/61pB50c3HRL._AC_SL1000_.jpg",
        "oferta_info": "¡Ahora 22,99 €! (Antes 34,99 € | -34%)",
        "precio_actual": "22,99 €",
        "precio_antiguo": "34,99 €"
    }

# 1. Obtener producto y generar enlace de afiliado con parámetros UTM
prod = obtener_producto_con_oferta()
tag = AMAZON_TAG.strip() if AMAZON_TAG else "tutienda-21"

link_afiliado = (
    f"https://www.amazon.es/dp/{prod['asin']}?"
    f"tag={tag}"
    f"&linkCode=ll1"
    f"&language=es_ES"
    f"&utm_source=pinterest"
    f"&utm_medium=social"
    f"&utm_campaign=ofertas_top"
)

print(f"-> Producto detectado: {prod['nombre']}")
print(f"-> ASIN real de Amazon: {prod['asin']}")
print(f"-> Info de oferta: {prod['oferta_info']}")
print(f"-> Enlace generado: {link_afiliado}")

# 2. Generar textos persuasivos con Gemini 3.6 Flash
prompt = f"""
Eres un especialista en ventas y copywriting para Pinterest.
Crea para el producto '{prod['nombre']}' (que tiene esta oferta real de Amazon: {prod['oferta_info']}):

1. TITULAR: Un titular ultra llamativo con emojis destacando el precio de oferta (máximo 6 palabras).
2. DESCRIPCION: Una descripción persuasiva que incluya exactamente la comparativa de precio '{prod['oferta_info']}', explique brevemente la utilidad del producto, genere urgencia (unidades limitadas/oferta flash) y termine con un CTA claro hacia el enlace y 4 hashtags virales (#ofertas #amazonfinds #rebajas #chollos). Máximo 32 palabras.

Formato estricto:
TITULAR: [tu titular]
DESCRIPCION: [tu descripcion]
"""

titular = f"🔥 {prod['oferta_info']} - {prod['nombre'][:25]}"
descripcion = f"🚨 {prod['oferta_info']}. {prod['nombre']}. ¡Aprovecha la rebaja antes de que vuelva a su precio original! Clic en el enlace para ver en Amazon. #ofertas #chollos #amazonfinds #rebajas"

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
    print(f"Aviso en llamada Gemini (usando texto base): {e}")

print(f"-> Titular final: {titular}")
print(f"-> Descripción final: {descripcion}")

# 3. Sesión con Pinterest y cookies
csrf_token = CSRF_ENV.strip() if CSRF_ENV else uuid.uuid4().hex
session = requests.Session()

dominios = [".pinterest.com", "www.pinterest.com", "pinterest.com", ".pinterest.es", "www.pinterest.es", "es.pinterest.com"]
for d in dominios:
    session.cookies.set("_pinterest_sess", AUTH_COOKIE, domain=d)
    session.cookies.set("_auth", "1", domain=d)
    session.cookies.set("csrftoken", csrf_token, domain=d)

base_headers = {
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

board_resp = session.post(
    board_url, 
    headers={**base_headers, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, 
    data={"data": json.dumps(board_payload)}
)
board_id = None

try:
    board_json = board_resp.json()
    board_id = board_json.get("resource_response", {}).get("data", {}).get("id")
except Exception as e:
    print(f"Error parseando tablero: {e}")

if not board_id:
    board_id = "1024920896388540341"

# 5. Descargar imagen y subirla al endpoint nativo de Pinterest
img_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
img_bytes = requests.get(prod["imagen"], headers=img_headers, timeout=10).content

upload_url = "https://www.pinterest.es/upload-image/"
files = {"img": ("image.jpg", img_bytes, "image/jpeg")}
upload_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "X-CSRFToken": csrf_token,
    "X-Requested-With": "XMLHttpRequest",
    "Referer": f"https://www.pinterest.es/{USERNAME}/{BOARD_SLUG}/"
}

up_resp = session.post(upload_url, headers=upload_headers, files=files)
image_signature = None

try:
    up_json = up_resp.json()
    image_signature = up_json.get("image_url") or up_json.get("success") or up_json.get("data", {}).get("image_url")
except Exception as e:
    print(f"Aviso en parseo de subida nativa: {e}")

create_url = "https://www.pinterest.es/resource/PinResource/create/"

payload_pin = {
    "options": {
        "board_id": str(board_id),
        "image_url": image_signature if image_signature else prod["imagen"],
        "title": titular,
        "description": descripcion,
        "link": link_afiliado
    },
    "context": {}
}

resp = session.post(
    create_url, 
    headers={**base_headers, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, 
    data={"data": json.dumps(payload_pin)}
)

pin_id = None
try:
    resp_json = resp.json()
    data = resp_json.get("resource_response", {}).get("data")
    if isinstance(data, dict):
        pin_id = data.get("id")
    elif isinstance(resp_json.get("data"), dict):
        pin_id = resp_json["data"].get("id")
except Exception:
    pass

if pin_id:
    print(f"¡ÉXITO TOTAL! Pin publicado con ID: {pin_id}")
    print(f"Ver Pin en: https://www.pinterest.es/pin/{pin_id}/")
else:
    print(f"Error al publicar (Status {resp.status_code}):")
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text[:400])
    exit(1)
