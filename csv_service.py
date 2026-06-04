import pandas as pd
from pathlib import Path
from typing import List
import os

CSV_PATH = Path(__file__).parent / "data" / "matches.csv"

COLONNES = ["equipe_dom", "equipe_ext", "cote_dom", "cote_nul", "cote_ext",
            "score", "total_buts", "resultat"]


def _init_csv():
    """Crée le CSV avec les bonnes colonnes s'il n'existe pas."""
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CSV_PATH.exists():
        df = pd.DataFrame(columns=COLONNES)
        df.to_csv(CSV_PATH, index=False)


def lire_csv() -> pd.DataFrame:
    """Retourne le DataFrame complet."""
    _init_csv()
    return pd.read_csv(CSV_PATH)


def ajouter_matches(matches: List[dict]) -> int:
    """
    Ajoute une liste de matchs au CSV.
    Évite les doublons (même equipe_dom + equipe_ext + score).
    Retourne le nombre de lignes réellement ajoutées.
    """
    _init_csv()
    df_existant = pd.read_csv(CSV_PATH)
    df_nouveau = pd.DataFrame(matches, columns=COLONNES)

    # Déduplication : on évite d'ajouter un match déjà présent
    cle = ["equipe_dom", "equipe_ext", "score"]
    df_combined = pd.concat([df_existant, df_nouveau], ignore_index=True)
    avant = len(df_existant)
    df_combined = df_combined.drop_duplicates(subset=cle, keep="first")
    apres = len(df_combined)

    df_combined.to_csv(CSV_PATH, index=False)
    return apres - avant


def supprimer_match(index: int) -> bool:
    """Supprime une ligne par index."""
    _init_csv()
    df = pd.read_csv(CSV_PATH)
    if index < 0 or index >= len(df):
        return False
    df = df.drop(index=index).reset_index(drop=True)
    df.to_csv(CSV_PATH, index=False)
    return True


def vider_csv():
    """Remet le CSV à zéro (garde les colonnes)."""
    df = pd.DataFrame(columns=COLONNES)
    df.to_csv(CSV_PATH, index=False)


def stats_csv() -> dict:
    """Retourne des statistiques basiques sur le CSV."""
    df = lire_csv()
    if df.empty:
        return {"total": 0, "distribution": {}}
    dist = df["resultat"].value_counts().to_dict()
    return {
        "total": len(df),
        "distribution": dist
    }
