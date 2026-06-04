from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

from ocr_service import extract_text_from_image
from parser_service import parse_cotes, parse_resultats, fusionner
from csv_service import ajouter_matches
from match import MatchCotes, MatchResultat

router = APIRouter(prefix="/extraction", tags=["Extraction"])


@router.post("/cotes", response_model=List[MatchCotes])
async def extraire_cotes(image: UploadFile = File(...)):
    """
    Reçoit une image de capture AVANT match.
    Retourne la liste des matchs avec leurs cotes extraites.
    """
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image.")

    image_bytes = await image.read()

    try:
        texte = await extract_text_from_image(image_bytes, image.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur OCR : {str(e)}")

    matches = parse_cotes(texte)

    if not matches:
        raise HTTPException(
            status_code=422,
            detail="Aucun match détecté dans l'image. Vérifiez la qualité de la capture."
        )

    return matches


@router.post("/resultats", response_model=List[MatchResultat])
async def extraire_resultats(image: UploadFile = File(...)):
    """
    Reçoit une image de capture RÉSULTAT.
    Retourne la liste des matchs avec leurs scores.
    """
    if not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Le fichier doit être une image.")

    image_bytes = await image.read()

    try:
        texte = await extract_text_from_image(image_bytes, image.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur OCR : {str(e)}")

    resultats = parse_resultats(texte)

    if not resultats:
        raise HTTPException(
            status_code=422,
            detail="Aucun résultat détecté dans l'image."
        )

    return resultats


@router.post("/fusionner-et-sauvegarder")
async def fusionner_et_sauvegarder(
    image_cotes: UploadFile = File(...),
    image_resultats: UploadFile = File(...)
):
    """
    Reçoit les deux captures (cotes + résultats), fusionne et sauvegarde dans le CSV.
    """
    # Extraction cotes
    bytes_cotes = await image_cotes.read()
    bytes_resultats = await image_resultats.read()

    try:
        texte_cotes = await extract_text_from_image(bytes_cotes, image_cotes.filename)
        texte_resultats = await extract_text_from_image(bytes_resultats, image_resultats.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur OCR : {str(e)}")

    cotes = parse_cotes(texte_cotes)
    resultats = parse_resultats(texte_resultats)

    if not cotes:
        raise HTTPException(status_code=422, detail="Aucune cote détectée.")
    if not resultats:
        raise HTTPException(status_code=422, detail="Aucun résultat détecté.")

    fusionnes = fusionner(cotes, resultats)

    if not fusionnes:
        raise HTTPException(
            status_code=422,
            detail="Impossible de fusionner : les noms d'équipes ne correspondent pas."
        )

    nb_ajoutes = ajouter_matches(fusionnes)

    return {
        "success": True,
        "matches_fusionnes": len(fusionnes),
        "matches_ajoutes_csv": nb_ajoutes,
        "donnees": fusionnes
    }


@router.post("/texte/cotes", response_model=List[MatchCotes])
async def parser_texte_cotes(payload: dict):
    """
    Alternative : envoyer le texte brut directement (sans OCR).
    Utile pour les tests.
    Body: { "texte": "..." }
    """
    texte = payload.get("texte", "")
    if not texte:
        raise HTTPException(status_code=400, detail="Le champ 'texte' est requis.")
    matches = parse_cotes(texte)
    return matches


@router.post("/texte/resultats", response_model=List[MatchResultat])
async def parser_texte_resultats(payload: dict):
    """
    Alternative : envoyer le texte brut directement (sans OCR).
    Body: { "texte": "..." }
    """
    texte = payload.get("texte", "")
    if not texte:
        raise HTTPException(status_code=400, detail="Le champ 'texte' est requis.")
    resultats = parse_resultats(texte)
    return resultats


@router.post("/texte/fusionner-et-sauvegarder")
async def fusionner_texte(payload: dict):
    """
    Fusion à partir de textes bruts (sans OCR).
    Body: { "texte_cotes": "...", "texte_resultats": "..." }
    """
    texte_cotes = payload.get("texte_cotes", "")
    texte_resultats = payload.get("texte_resultats", "")

    if not texte_cotes or not texte_resultats:
        raise HTTPException(status_code=400, detail="Les deux textes sont requis.")

    cotes = parse_cotes(texte_cotes)
    resultats = parse_resultats(texte_resultats)
    fusionnes = fusionner(cotes, resultats)

    if not fusionnes:
        raise HTTPException(status_code=422, detail="Fusion impossible.")

    nb_ajoutes = ajouter_matches(fusionnes)

    return {
        "success": True,
        "matches_fusionnes": len(fusionnes),
        "matches_ajoutes_csv": nb_ajoutes,
        "donnees": fusionnes
    }
