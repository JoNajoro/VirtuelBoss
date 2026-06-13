import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, mean_squared_error
from xgboost import XGBClassifier, XGBRegressor

from csv_service import lire_csv
from match import PredictionOutput, TrainResponse

MODEL_PATH = Path(__file__).parent / "data" / "model.pkl"
TOTAL_MODEL_PATH = Path(__file__).parent / "data" / "total_model.pkl"
ENCODER_PATH = Path(__file__).parent / "data" / "encoder.pkl"

# Features utilisées pour la prédiction (cotes uniquement, pas les noms)
FEATURES = ["cote_dom", "cote_nul", "cote_ext"]
TARGET = "resultat"


def entrainer_modele() -> TrainResponse:
    """
    Entraîne un modèle XGBoost sur les données du CSV.
    Retourne les métriques d'entraînement.
    """
    df = lire_csv()

    if df.empty or len(df) < 10:
        return TrainResponse(
            success=False,
            message=f"Pas assez de données pour entraîner ({len(df)} matchs). Minimum : 10."
        )

    X = df[FEATURES].values
    y = df[TARGET].values
    y_total = df["total_buts"].values

    # Encodage des labels : D=0, E=1, N=2
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    # Split train/test une seule fois pour les deux modèles
    X_train, X_test, y_train, y_test, total_train, total_test = train_test_split(
        X, y_encoded, y_total, test_size=0.2, random_state=42,
        stratify=y_encoded if len(set(y_encoded)) > 1 else None
    )

    # Modèle XGBoost pour le résultat
    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42
    )
    model.fit(X_train, y_train)

    # Modèle XGBoost pour le total de buts
    regressor = XGBRegressor(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        objective="reg:squarederror",
        random_state=42
    )
    regressor.fit(X_train, total_train)

    # Évaluation
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    total_pred = regressor.predict(X_test)
    rmse_total = mean_squared_error(total_test, total_pred, squared=False)

    # Sauvegarde modèle + encodeur + régressor
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(regressor, TOTAL_MODEL_PATH)
    joblib.dump(le, ENCODER_PATH)

    return TrainResponse(
        success=True,
        message="Modèle entraîné avec succès !",
        accuracy=round(accuracy * 100, 2),
        nb_matches=len(df),
        rmse_total_buts=round(float(rmse_total), 3)
    )


def _score_suggestions(cote_dom: float, cote_nul: float, cote_ext: float, resultat_code: str, limit: int = 3) -> list:
    df = lire_csv()
    if df.empty:
        return []

    df = df[df["resultat"] == resultat_code].copy()
    if df.empty:
        return []

    current = np.array([cote_dom, cote_nul, cote_ext], dtype=float)
    current_norm = current / current.sum() if current.sum() else current

    odds = df[FEATURES].astype(float).values
    sums = odds.sum(axis=1, keepdims=True)
    odds_norm = np.divide(odds, sums, where=sums != 0)
    distances = np.linalg.norm(odds_norm - current_norm, axis=1)

    df["distance"] = distances
    # fréquence d'apparition du score (dans les matchs de ce type de résultat)
    df["freq"] = df.groupby("score")["score"].transform("count")
    # On souhaite prioriser les scores les plus répétitifs (freq desc),
    # puis ceux dont les cotes sont les plus proches (distance asc).
    df = df.sort_values(by=["freq", "distance", "score"], ascending=[False, True, True])

    ordered_scores = list(dict.fromkeys(df["score"].tolist()))
    return ordered_scores[:limit]


def _primary_and_alternate_scores(cote_dom: float, cote_nul: float, cote_ext: float, proba_dict: dict, predicted_code: str) -> tuple:
    current = np.array([cote_dom, cote_nul, cote_ext], dtype=float)
    current_norm = current / current.sum() if current.sum() else current

    primary_scores = _score_suggestions(cote_dom, cote_nul, cote_ext, predicted_code, limit=3)
    primary_score = primary_scores[0] if primary_scores else None

    other_codes = [code for code, _ in sorted(proba_dict.items(), key=lambda item: item[1], reverse=True) if code != predicted_code]
    alternate_score = None
    for code in other_codes:
        alt_scores = _score_suggestions(cote_dom, cote_nul, cote_ext, code, limit=1)
        if alt_scores:
            alternate_score = alt_scores[0]
            break

    return primary_score, alternate_score


def predire(cote_dom: float, cote_nul: float, cote_ext: float) -> PredictionOutput:
    """
    Prédit le résultat d'un match à partir des cotes.
    """
    if not MODEL_PATH.exists() or not ENCODER_PATH.exists() or not TOTAL_MODEL_PATH.exists():
        raise FileNotFoundError("Le modèle n'est pas encore entraîné. Veuillez d'abord entraîner.")

    model = joblib.load(MODEL_PATH)
    regressor = joblib.load(TOTAL_MODEL_PATH)
    le = joblib.load(ENCODER_PATH)

    X = np.array([[cote_dom, cote_nul, cote_ext]])
    proba = model.predict_proba(X)[0]
    predicted_class = model.predict(X)[0]

    classes = le.classes_
    proba_dict = {cls: float(p) for cls, p in zip(classes, proba)}

    resultat_code = le.inverse_transform([predicted_class])[0]
    labels = {"D": "Domicile", "N": "Nul", "E": "Extérieur"}
    resultat_label = labels.get(resultat_code, resultat_code)

    total_pred = regressor.predict(X)[0]
    total_buts = int(round(float(total_pred)))
    score_suggestions = _score_suggestions(cote_dom, cote_nul, cote_ext, resultat_code, limit=3)

    return PredictionOutput(
        resultat=resultat_label,
        probabilite_dom=round(proba_dict.get("D", 0.0), 4),
        probabilite_nul=round(proba_dict.get("N", 0.0), 4),
        probabilite_ext=round(proba_dict.get("E", 0.0), 4),
        confiance=round(float(max(proba)), 4),
        total_buts=total_buts,
        score_suggestions=score_suggestions
    )


def modele_existe() -> bool:
    return MODEL_PATH.exists() and ENCODER_PATH.exists() and TOTAL_MODEL_PATH.exists()
