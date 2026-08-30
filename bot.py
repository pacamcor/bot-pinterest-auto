import os
import random
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from google import genai

GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
AMAZON_TAG = os.environ.get("AMAZON_TAG")

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

# Generar textos con IA
prompt = f"""
Crea para Pinterest sobre el producto '{prod['nombre']}':
1. Un titular persuasivo (máximo 6 palabras).
2. Una descripción atractiva para compras con palabras clave (máximo 30 palabras).
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

# Estructura RSS XML para Pinterest
rss = ET.Element("rss", version="2.0")
channel = ET.SubElement(rss, "channel")
ET.SubElement(channel, "title").text = "Catalogo Pinterest Afiliados"
ET.SubElement(channel, "link").text = link_afiliado
ET.SubElement(channel, "description").text = "Feed de productos recomendados"

item = ET.SubElement(channel, "item")
ET.SubElement(item, "title").text = titular
ET.SubElement(item, "link").text = link_afiliado
ET.SubElement(item, "description").text = descripcion
ET.SubElement(item, "enclosure", url=prod["imagen"], type="image/jpeg", length="1024")
ET.SubElement(item, "guid").text = f"{prod['asin']}-{int(datetime.now().timestamp())}"
ET.SubElement(item, "pubDate").text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

tree = ET.ElementTree(rss)
ET.indent(tree, space="  ", level=0)
tree.write("feed.xml", encoding="utf-8", xml_declaration=True)
print(f"Feed generado con éxito para: {titular}")
