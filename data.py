from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import pandas as pd

from csv_service import (
    lire_csv, supprimer_match, vider_csv, stats_csv, CSV_PATH
)

router = APIRouter(prefix="/data", tags=["Données CSV"])


@router.get("/matches")
async def get_matches():
    """Retourne tous les matchs du CSV."""
    df = lire_csv()
    return {
        "total": len(df),
        "matches": df.to_dict(orient="records")
    }


@router.get("/stats")
async def get_stats():
    """Retourne des statistiques sur les données."""
    return stats_csv()


@router.delete("/match/{index}")
async def supprimer(index: int):
    """Supprime un match par son index."""
    ok = supprimer_match(index)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Index {index} introuvable.")
    return {"success": True, "message": f"Match {index} supprimé."}


@router.delete("/vider")
async def vider():
    """Vide entièrement le CSV (remet à zéro)."""
    vider_csv()
    return {"success": True, "message": "CSV vidé."}


@router.get("/export")
async def exporter_csv():
    """Télécharge le fichier CSV."""
    if not CSV_PATH.exists():
        raise HTTPException(status_code=404, detail="Aucun fichier CSV disponible.")
    return FileResponse(
        path=str(CSV_PATH),
        media_type="text/csv",
        filename="matches.csv"
    )
