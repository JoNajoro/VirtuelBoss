from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from typing import List, Optional

from ocr_service import extract_text_from_image
from parser_service import (
    parse_cotes, parse_resultats, fusionner, construire_liste_equipes
)
from csv_service import ajouter_matches
from match import MatchCotes, MatchResultat

router = APIRouter(prefix="/extraction", tags=["Extraction"])


# ─────────────────────────────────────────────
#  UPLOAD IMAGE (OCR)
# ─────────────────────────────────────────────

@router.post("/cotes", response_model=List[MatchCotes])
async def extraire_cotes(image: UploadFile = File(...)):
    """Capture AVANT match → extrait les cotes via OCR."""
    if not image.content_type.startswith("image/"):
        raise HTTPException(400, "Le fichier doit être une image.")
    image_bytes = await image.read()
    try:
        texte = await extract_text_from_image(image_bytes, image.filename)
    except Exception as e:
        raise HTTPException(500, f"Erreur OCR : {e}")
    equipes = construire_liste_equipes()
    matches = parse_cotes(texte, equipes)
    if not matches:
        raise HTTPException(422, "Aucun match détecté. Vérifiez la qualité de la capture.")
    return matches


@router.post("/resultats", response_model=List[MatchResultat])
async def extraire_resultats(image: UploadFile = File(...)):
    """Capture RÉSULTAT → extrait les scores via OCR."""
    if not image.content_type.startswith("image/"):
        raise HTTPException(400, "Le fichier doit être une image.")
    image_bytes = await image.read()
    try:
        texte = await extract_text_from_image(image_bytes, image.filename)
    except Exception as e:
        raise HTTPException(500, f"Erreur OCR : {e}")
    matches = parse_resultats(texte)
    if not matches:
        raise HTTPException(422, "Aucun résultat détecté.")
    return matches


@router.post("/fusionner-et-sauvegarder")
async def fusionner_et_sauvegarder(
    image_cotes: UploadFile = File(...),
    image_resultats: UploadFile = File(...)
):
    """Upload 2 images → OCR → fusion → sauvegarde CSV."""
    bytes_cotes     = await image_cotes.read()
    bytes_resultats = await image_resultats.read()
    try:
        texte_cotes     = await extract_text_from_image(bytes_cotes, image_cotes.filename)
        texte_resultats = await extract_text_from_image(bytes_resultats, image_resultats.filename)
    except Exception as e:
        raise HTTPException(500, f"Erreur OCR : {e}")

    equipes  = construire_liste_equipes()
    cotes    = parse_cotes(texte_cotes, equipes)
    resultats= parse_resultats(texte_resultats)

    if not cotes:
        raise HTTPException(422, "Aucune cote détectée.")
    if not resultats:
        raise HTTPException(422, "Aucun résultat détecté.")

    fusionnes = fusionner(cotes, resultats)
    if not fusionnes:
        raise HTTPException(422, "Fusion impossible : noms d'équipes non correspondants.")

    nb = ajouter_matches(fusionnes)
    return {"success": True, "matches_fusionnes": len(fusionnes), "matches_ajoutes_csv": nb, "donnees": fusionnes}


# ─────────────────────────────────────────────
#  TEXTE BRUT (sans OCR) — usage principal
# ─────────────────────────────────────────────

@router.post("/texte/cotes", response_model=List[MatchCotes])
async def parser_texte_cotes(payload: dict = Body(...)):
    """
    Parse le texte brut des cotes (copié depuis Google Lens).
    Body: { "texte": "...", "equipes": [...] (optionnel) }
    """
    texte   = payload.get("texte", "").strip()
    equipes = payload.get("equipes", None)
    if not texte:
        raise HTTPException(400, "Le champ 'texte' est requis.")
    if equipes is None:
        equipes = construire_liste_equipes()
    matches = parse_cotes(texte, equipes)
    if not matches:
        raise HTTPException(422, "Aucun match détecté dans le texte.")
    return matches


@router.post("/texte/resultats", response_model=List[MatchResultat])
async def parser_texte_resultats(payload: dict = Body(...)):
    """
    Parse le texte brut des résultats.
    Body: { "texte": "..." }
    """
    texte = payload.get("texte", "").strip()
    if not texte:
        raise HTTPException(400, "Le champ 'texte' est requis.")
    matches = parse_resultats(texte)
    if not matches:
        raise HTTPException(422, "Aucun résultat détecté.")
    return matches


@router.post("/texte/fusionner-et-sauvegarder")
async def fusionner_texte(payload: dict = Body(...)):
    """
    Fusion à partir des 2 textes bruts → sauvegarde CSV.
    Body: { "texte_cotes": "...", "texte_resultats": "..." }
    """
    texte_cotes     = payload.get("texte_cotes", "").strip()
    texte_resultats = payload.get("texte_resultats", "").strip()
    if not texte_cotes or not texte_resultats:
        raise HTTPException(400, "Les deux textes sont requis.")

    equipes   = construire_liste_equipes()
    cotes     = parse_cotes(texte_cotes, equipes)
    resultats = parse_resultats(texte_resultats)

    if not cotes:
        raise HTTPException(422, "Aucune cote détectée.")
    if not resultats:
        raise HTTPException(422, "Aucun résultat détecté.")

    fusionnes = fusionner(cotes, resultats)
    if not fusionnes:
        raise HTTPException(422, "Fusion impossible : noms non correspondants.")

    nb = ajouter_matches(fusionnes)
    return {
        "success": True,
        "matches_fusionnes": len(fusionnes),
        "matches_ajoutes_csv": nb,
        "donnees": fusionnes
    }


# ─────────────────────────────────────────────
#  PREVIEW (sans sauvegarder) — utile pour vérifier avant validation
# ─────────────────────────────────────────────

@router.post("/texte/preview")
async def preview_fusion(payload: dict = Body(...)):
    """
    Prévisualise la fusion sans sauvegarder dans le CSV.
    Body: { "texte_cotes": "...", "texte_resultats": "..." }
    """
    texte_cotes     = payload.get("texte_cotes", "").strip()
    texte_resultats = payload.get("texte_resultats", "").strip()
    if not texte_cotes or not texte_resultats:
        raise HTTPException(400, "Les deux textes sont requis.")

    equipes   = construire_liste_equipes()
    cotes     = parse_cotes(texte_cotes, equipes)
    resultats = parse_resultats(texte_resultats)
    fusionnes = fusionner(cotes, resultats)

    return {
        "cotes_detectees":     len(cotes),
        "resultats_detectes":  len(resultats),
        "matches_fusionnes":   len(fusionnes),
        "non_fusionnes_cotes": [
            {"equipe_dom": c.equipe_dom, "equipe_ext": c.equipe_ext}
            for c in cotes
            if not any(
                f["equipe_dom"].lower() == c.equipe_dom.lower() and
                f["equipe_ext"].lower() == c.equipe_ext.lower()
                for f in fusionnes
            )
        ],
        "donnees": fusionnes
    }
