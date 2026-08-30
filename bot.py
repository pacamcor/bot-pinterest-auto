import os
import io
import random
import base64
import requests
from PIL import Image, ImageDraw, ImageFont
from google import genai

# Cargar credenciales desde los secretos de GitHub
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
PIN_TOKEN = os.environ.get("PINTEREST_TOKEN")
BOARD_ID = os.environ.get("PINTEREST_BOARD_ID")
AMAZON_TAG = os.environ.get("AMAZON_TAG")

# Cliente moderno de Gemini
client = genai.Client(api_key=GEMINI_KEY)

# Catálogo base de productos
PRODUCTOS = [
    {
        "nombre": "Organizador de escritorio de madera multifuncional",
        "asin": "B08N5WRWNW",
        "imagen": "https://images.unsplash.com/photo-1544816155-12df9643f363?auto=format&fit=crop&w=800&q=80",
        "precio": "19.99€"
    },
    {
        "nombre": "Lámpara LED de escritorio minimalista con carga inalámbrica",
        "asin": "B09X123456",
        "imagen": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?auto=format&fit=crop&w=800&q=80",
        "precio": "29.95€"
    },
    {
        "nombre": "Difusor de aromas ultrasónico con luz cálida",
        "asin": "B07V987654",
        "imagen": "https://images.unsplash.com/photo-1608571423902-eed4a5ad8108?auto=format&fit=crop&w=800&q=80",
        "precio": "24.50€"
    }
]

# 1. Seleccionar un producto al azar
prod = random.choice(PRODUCTOS)
link_afiliado = f"https://www.amazon.es/dp/{prod['asin']}?tag={AMAZON_TAG}"

# 2. Generar textos atractivos con IA
prompt = f"""
Actúa como experto en Pinterest SEO. Para el producto '{prod['nombre']}':
1. Genera un titular persuasivo (máximo 6 palabras).
2. Genera una descripción atractiva con palabras clave (máximo 30 palabras).
Formato estricto:
TITULAR: [tu titular]
DESCRIPCION: [tu descripcion]
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
)
res = response.text
titular = res.split("TITULAR:")[1].split("DESCRIPCION:")[0].strip()
descripcion = res.split("DESCRIPCION:")[1].strip()

# 3. Descargar y componer la imagen del Pin en vertical (1000x1500)
img_bytes = requests.get(prod["imagen"]).content
prod_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

canvas = Image.new("RGB", (1000, 1500), color=(248, 249, 250))
prod_img.thumbnail((800, 800))
canvas.paste(prod_img, ((1000 - prod_img.width) // 2, 450))

draw = ImageDraw.Draw(canvas)
font = ImageFont.load_default()
draw.text((80, 250), titular, fill=(20, 20, 20), font=font)
draw.text((80, 1300), f"Disponible en Amazon: {prod['precio']}", fill=(180, 0, 0), font=font)

buffered = io.BytesIO()
canvas.save(buffered, format="JPEG", quality=90)
img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

# 4. Publicar Pin en Pinterest
headers = {
    "Authorization": f"Bearer {PIN_TOKEN}",
    "Content-Type": "application/json"
}
payload = {
    "board_id": BOARD_ID,
    "title": titular,
    "description": descripcion,
    "link": link_afiliado,
    "media_source": {
        "source_type": "image_base64",
        "content_type": "image/jpeg",
        "data": img_b64
    }
}

r = requests.post("https://api.pinterest.com/v5/pins", headers=headers, json=payload)

if r.status_code in [200, 201]:
    print(f"Éxito: Pin publicado correctamente -> '{titular}'")
else:
    print(f"Error ({r.status_code}): {r.text}")
    exit(1)
