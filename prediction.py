from fastapi import APIRouter, HTTPException
from ml_service import entrainer_modele, predire, modele_existe
from match import PredictionInput, PredictionOutput, TrainResponse

router = APIRouter(prefix="/prediction", tags=["Prédiction"])


@router.post("/entrainer", response_model=TrainResponse)
async def entrainer():
    """
    Lance l'entraînement du modèle XGBoost sur toutes les données du CSV.
    """
    result = entrainer_modele()
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result


@router.post("/predire", response_model=PredictionOutput)
async def predire_match(input: PredictionInput):
    """
    Prédit le résultat d'un match à partir des cotes.
    Le modèle doit être entraîné au préalable.
    """
    if not modele_existe():
        raise HTTPException(
            status_code=400,
            detail="Le modèle n'est pas encore entraîné. Appelez /prediction/entrainer d'abord."
        )
    try:
        result = predire(input.cote_dom, input.cote_nul, input.cote_ext)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statut")
async def statut_modele():
    """Vérifie si le modèle est entraîné et disponible."""
    return {
        "modele_disponible": modele_existe(),
        "message": "Modèle prêt." if modele_existe() else "Aucun modèle entraîné."
    }
