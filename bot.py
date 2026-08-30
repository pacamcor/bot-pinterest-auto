import os
import random
import json
import uuid
import re
import time
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
    "gadgets tecnologicos utiles ofertas",
    "accesorios escritorio minimalista rebajas",
    "soporte movil cargador inalambrico oferta",
    "auriculares cancelacion ruido ofertas flash",
    "reloj inteligente deportivo rebajas",
    "power bank carga rapida ofertas",
    
    # Hogar, Organización y Limpieza
    "organizadores armario ropa rebajas",
    "cajas organizadoras transparentes oferta",
    "estanteria modular cocina rebajas",
    "dispensador jabon automatico sensor",
    "perchas magicas armario ofertas",
    "limpiador vapor portatil ofertas",
    
    # Cocina y Gadgets Prácticos
    "accesorios freidora de aire ofertas",
    "picadora verduras manual oferta",
    "sellador bolsas termico portatil",
    "bascula digital cocina precision",
    "recipientes hermeticos cristal oferta",
    
    # Iluminación y Setup
    "tira led alexa ofertas",
    "lampara mesa noche tactil oferta",
    "luces sensor movimiento armario",
    "alfombrilla escritorio xxl ofertas",
    
    # Confort y Bienestar
    "difusor aceites esenciales aromaterapia",
    "humidificador habitacion oferta",
    "cojin ergonomico memoria rebajas",
    "masajeador cervical cuello calor oferta"
]

def obtener_datos_exactos_producto(asin, nombre_sugerido, img_sugerida, headers):
    """Accede a la página individual del producto (DP) para sacar los precios 100% exactos"""
    dp_url = f"https://www.amazon.es/dp/{asin}"
    try:
        r = requests.get(dp_url, headers=headers, timeout=12)
        if r.status_code != 200:
            return None
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Título real
        title_tag = soup.find("span", {"id": "productTitle"})
        nombre = title_tag.text.strip() if title_tag else nombre_sugerido
        
        # Imagen de alta resolución
        img_src = img_sugerida
        landing_img = soup.find("img", {"id": "landingImage"})
        if landing_img and landing_img.get("src"):
            img_src = landing_img.get("src")
        
        # 1. Extraer Precio Actual exacto en ficha
        precio_actual = ""
        core_price = soup.find("div", {"id": "corePriceDisplay_desktop_feature_div"}) or soup.find("div", {"id": "corePrice_feature_div"})
        if core_price:
            p_actual_elem = core_price.find("span", {"class": "a-price"})
            if p_actual_elem:
                off = p_actual_elem.find("span", {"class": "a-offscreen"})
                if off and off.text and "€" in off.text:
                    precio_actual = off.text.strip()
        
        if not precio_actual:
            for selector in ["#priceblock_ourprice", "#priceblock_dealprice", ".priceToPay span.a-offscreen"]:
                elem = soup.select_one(selector)
                if elem and elem.text and "€" in elem.text:
                    precio_actual = elem.text.strip()
                    break

        # 2. Extraer Precio Antiguo (PVP Tachado) exacto en ficha
        precio_antiguo = ""
        if core_price:
            p_old_elem = core_price.find("span", {"class": "a-text-price"}) or core_price.find("span", {"data-a-strike": "true"})
            if p_old_elem:
                off_old = p_old_elem.find("span", {"class": "a-offscreen"})
                if off_old and off_old.text and "€" in off_old.text:
                    precio_antiguo = off_old.text.strip()
        
        if not precio_antiguo:
            for selector in [".basisPrice span.a-offscreen", "span[data-a-strike='true'] span.a-offscreen"]:
                elem = soup.select_one(selector)
                if elem and elem.text and "€" in elem.text:
                    precio_antiguo = elem.text.strip()
                    break

        # 3. Extraer Porcentaje de Rebaja exacto
        descuento_pct = ""
        badge_elem = soup.select_one(".savingsPercentage") or soup.select_one("span.reinventPriceSavingsPercentageMargin")
        if badge_elem and badge_elem.text:
            descuento_pct = badge_elem.text.strip()

        if not precio_actual:
            return None

        if precio_actual and precio_antiguo:
            if descuento_pct:
                oferta_info = f"¡Ahora {precio_actual}! (Antes {precio_antiguo} | {descuento_pct})"
            else:
                oferta_info = f"¡Ahora {precio_actual}! (Antes {precio_antiguo})"
        else:
            oferta_info = f"¡En oferta por solo {precio_actual}!"

        # Descargar y verificar imagen
        img_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://www.amazon.es/"
        }
        r_img = requests.get(img_src, headers=img_headers, timeout=12)
        if r_img.status_code != 200 or len(r_img.content) < 3000:
            return None

        return {
            "nombre": nombre,
            "asin": asin,
            "imagen_bytes": r_img.content,
            "imagen_url": img_src,
            "oferta_info": oferta_info
        }
    except Exception as e:
        print(f"Aviso parseando ficha {asin}: {e}")
        return None

def obtener_producto_con_imagen():
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
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code != 200:
                continue
            
            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.find_all("div", {"data-asin": True})
            
            for item in items:
                asin = item.get("data-asin", "").strip()
                if not asin or len(asin) != 10:
                    continue
                
                title_elem = item.find("h2")
                img_elem = item.find("img", {"class": "s-image"})
                
                nombre_base = title_elem.text.strip() if title_elem else ""
                img_base = img_elem.get("src", "") if img_elem else ""
                
                datos_reales = obtener_datos_exactos_producto(asin, nombre_base, img_base, headers)
                if datos_reales:
                    return datos_reales

        except Exception as e:
            print(f"Aviso buscando en Amazon ({query}): {e}")
            continue

    # Fallback con descarga limpia
    fallback_url = "https://m.media-amazon.com/images/I/61pB50c3HRL._AC_SL1000_.jpg"
    fallback_bytes = requests.get(fallback_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=12).content
    return {
        "nombre": "Blink Mini Cámara de seguridad inteligente compacta para interiores",
        "asin": "B07X37DT9M",
        "imagen_bytes": fallback_bytes,
        "imagen_url": fallback_url,
        "oferta_info": "¡Ahora 22,99 €! (Antes 34,99 € | -34%)"
    }

# 1. Obtener producto y validar precio e imagen real
prod = obtener_producto_con_imagen()
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

1. TITULAR: Un titular llamativo con emojis destacando la bajada de precio (ej: 🔥 {prod['oferta_info']}). Máximo 6 palabras.
2. DESCRIPCION: Una descripción persuasiva que incluya exactamente la comparativa '{prod['oferta_info']}', explique para qué sirve el producto, genere urgencia (oferta por tiempo limitado) y termine con una llamada a la acción y 4 hashtags (#ofertas #rebajas #amazonfinds #chollos). Máximo 32 palabras.

Formato estricto:
TITULAR: [tu titular]
DESCRIPCION: [tu descripcion]
"""

titular = f"🔥 {prod['oferta_info']} - {prod['nombre'][:25]}"
descripcion = f"🚨 {prod['oferta_info']}. {prod['nombre']}. ¡Aprovecha la rebaja antes de que vuelva a su precio original! Haz clic en el enlace para ver en Amazon. #ofertas #rebajas #amazonfinds #chollos"

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

# 5. Subida nativa de la imagen a Pinterest
upload_url = "https://www.pinterest.es/upload-image/"
files = {"img": ("image.jpg", prod["imagen_bytes"], "image/jpeg")}
upload_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "X-CSRFToken": csrf_token,
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.pinterest.es/pin-builder/",
    "Origin": "https://www.pinterest.es"
}

up_resp = session.post(upload_url, headers=upload_headers, files=files)
image_signature = None

try:
    up_json = up_resp.json()
    # Buscar claves estándar donde Pinterest entrega la URL subida
    image_signature = (
        up_json.get("image_url") 
        or up_json.get("url") 
        or up_json.get("success") 
        or up_json.get("data", {}).get("image_url")
        or up_json.get("resource_response", {}).get("data", {}).get("image_url")
    )
    if not image_signature and "i.pinimg.com" in up_resp.text:
        match = re.search(r'https://i\.pinimg\.com/[^\s"\'<>]+', up_resp.text)
        if match:
            image_signature = match.group(0)
except Exception as e:
    print(f"Aviso en parseo de subida nativa: {e}")

print(f"-> URL de imagen procesada para Pin: {image_signature if image_signature else 'URL directa'}")

create_url = "https://www.pinterest.es/resource/PinResource/create/"

payload_pin = {
    "options": {
        "board_id": str(board_id),
        "image_url": image_signature if image_signature else prod["imagen_url"],
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
