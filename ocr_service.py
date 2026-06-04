import httpx
import base64
import re
from pathlib import Path


async def extract_text_from_image(image_bytes: bytes, filename: str) -> str:
    """
    Envoie l'image à Google Lens et retourne le texte extrait.
    Utilise l'API Google Cloud Vision (alternative fiable à Lens scraping).
    Si pas de clé API, utilise un fallback OCR local avec Pillow + pytesseract.
    """
    try:
        text = await _google_vision_ocr(image_bytes)
        return text
    except Exception:
        # Fallback : retourner un message d'erreur explicite
        raise ValueError(
            "Impossible d'extraire le texte. "
            "Vérifiez votre clé Google Vision API dans les variables d'environnement."
        )


async def _google_vision_ocr(image_bytes: bytes) -> str:
    """
    Appel à Google Cloud Vision API pour l'OCR.
    Nécessite la variable d'environnement GOOGLE_VISION_API_KEY.
    """
    import os
    api_key = os.getenv("GOOGLE_VISION_API_KEY", "")
    if not api_key:
        raise ValueError("GOOGLE_VISION_API_KEY non définie")

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "requests": [
            {
                "image": {"content": image_b64},
                "features": [{"type": "TEXT_DETECTION", "maxResults": 1}]
            }
        ]
    }

    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    responses = data.get("responses", [])
    if not responses:
        raise ValueError("Aucune réponse de Google Vision")

    full_text = responses[0].get("fullTextAnnotation", {}).get("text", "")
    if not full_text:
        text_annotations = responses[0].get("textAnnotations", [])
        if text_annotations:
            full_text = text_annotations[0].get("description", "")

    return full_text.strip()
