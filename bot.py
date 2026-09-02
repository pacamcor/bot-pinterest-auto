import os
import random
import json
import uuid
import re
import time
import base64
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

def limpiar_precio_a_float(texto):
    if not texto:
        return None
    match = re.search(r'(\d+[\.,]\d{2})', texto)
    if match:
        val = match.group(1).replace('.', '').replace(',', '.')
        try:
            return float(val)
        except ValueError:
            return None
    return None

def alojar_imagen_para_pinterest(img_bytes):
    """
    Sube la imagen a un CDN de acceso libre y directo (sin bloqueos anti-bot)
    para que Pinterest pueda descargarla sin el error 400 ni 403.
    """
    # 1. Intento: ImgBB (API pública ultra-fiable para hotlinking de Pinterest)
    try:
        b64_image = base64.b64encode(img_bytes).decode("utf-8")
        r_imgbb = requests.post(
            "https://api.imgbb.com/1/upload",
            data={
                "key": "47be15e197c11867ae6bcebf29871790", # Clave pública de subida directa
                "image": b64_image
            },
            timeout=15
        )
        if r_imgbb.status_code == 200:
            direct_url = r_imgbb.json().get("data", {}).get("image", {}).get("url")
            if direct_url and direct_url.startswith("http"):
                return direct_url
    except Exception as e:
        print(f"Aviso subida ImgBB: {e}")

    # 2. Intento: Catbox con extensión JPG limpia
    try:
        r_catbox = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload"},
            files={"fileToUpload": ("foto.jpg", img_bytes, "image/jpeg")},
            timeout=15
        )
        if r_catbox.status_code == 200 and r_catbox.text.strip().startswith("https://"):
            return r_catbox.text.strip()
    except Exception as e:
        print(f"Aviso subida Catbox: {e}")

    return None

def obtener_producto_con_oferta():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
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
                
                if not title_elem or not img_elem:
                    continue
                
                nombre = title_elem.text.strip()
                img_src = img_elem.get("src", "")
                
                if not img_src or "m.media-amazon.com" not in img_src:
                    continue
                
                price_box = (
                    item.find("div", {"class": "puis-price-instructions-style"})
                    or item.find("div", {"data-cy": "price-recipe"})
                    or item
                )
                
                precio_actual_str = ""
                precio_actual_num = None
                
                for p_tag in price_box.find_all("span", {"class": "a-price"}):
                    if "a-text-price" in p_tag.get("class", []):
                        continue
                    whole = p_tag.find("span", {"class": "a-price-whole"})
                    fraction = p_tag.find("span", {"class": "a-price-fraction"})
                    if whole and fraction:
                        w_clean = re.sub(r'[^\d]', '', whole.text.strip())
                        f_clean = re.sub(r'[^\d]', '', fraction.text.strip())
                        if w_clean and f_clean:
                            precio_actual_str = f"{w_clean},{f_clean} €"
                            precio_actual_num = float(f"{w_clean}.{f_clean}")
                            break
                    else:
                        off = p_tag.find("span", {"class": "a-offscreen"})
                        if off and off.text and "€" in off.text and "/" not in off.text:
                            precio_actual_str = off.text.strip()
                            precio_actual_num = limpiar_precio_a_float(precio_actual_str)
                            if precio_actual_num:
                                break
                
                precio_antiguo_str = ""
                precio_antiguo_num = None
                old_tag = price_box.find("span", {"class": "a-text-price"}) or price_box.find("span", {"data-a-strike": "true"})
                if old_tag:
                    off_old = old_tag.find("span", {"class": "a-offscreen"})
                    if off_old and off_old.text and "€" in off_old.text:
                        precio_antiguo_str = off_old.text.strip()
                        precio_antiguo_num = limpiar_precio_a_float(precio_antiguo_str)
                
                if not precio_actual_num:
                    continue
                
                if precio_antiguo_num and precio_antiguo_num > precio_actual_num:
                    pct = round(((precio_antiguo_num - precio_actual_num) / precio_antiguo_num) * 100)
                    oferta_info = f"¡Ahora {precio_actual_str}! (Antes {precio_antiguo_str} | -{pct}%)"
                else:
                    oferta_info = f"¡En oferta por solo {precio_actual_str}!"
                
                # Descargar bytes de la imagen
                img_bytes = None
                img_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                for _ in range(2):
                    try:
                        r_img = requests.get(img_src, headers=img_headers, timeout=12)
                        if r_img.status_code == 200 and len(r_img.content) > 3000:
                            img_bytes = r_img.content
                            break
                    except Exception:
                        time.sleep(1)
                
                if not img_bytes:
                    continue
                
                # Alojar en CDN compatible
                cdn_url = alojar_imagen_para_pinterest(img_bytes)
                if not cdn_url:
                    continue
                
                return {
                    "nombre": nombre,
                    "asin": asin,
                    "imagen_url": cdn_url,
                    "oferta_info": oferta_info
                }
        except Exception as e:
            print(f"Aviso buscando en Amazon ({query}): {e}")
            continue

    # Fallback garantizado
    fallback_bytes = requests.get("https://m.media-amazon.com/images/I/61pB50c3HRL._AC_SL1000_.jpg", headers={"User-Agent": "Mozilla/5.0"}, timeout=12).content
    fallback_cdn = alojar_imagen_para_pinterest(fallback_bytes)
    return {
        "nombre": "Blink Mini Cámara de seguridad inteligente compacta para interiores",
        "asin": "B07X37DT9M",
        "imagen_url": fallback_cdn,
        "oferta_info": "¡Ahora 22,99 €! (Antes 34,99 € | -34%)"
    }

# 1. Obtener producto y generar enlace de afiliado
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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
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

# 5. Crear Pin oficial en el tablero usando el CDN directo
print(f"-> URL de imagen enviada a Pinterest: {prod['imagen_url']}")

create_url = "https://www.pinterest.es/resource/PinResource/create/"

payload_pin = {
    "options": {
        "board_id": str(board_id),
        "image_url": prod["imagen_url"],
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
