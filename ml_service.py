import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier

from csv_service import lire_csv
from match import PredictionOutput, TrainResponse

MODEL_PATH = Path(__file__).parent / "data" / "model.pkl"
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

    # Encodage des labels : D=0, E=1, N=2
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)

    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
        if len(set(y_encoded)) > 1 else None
    )

    # Modèle XGBoost
    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42
    )
    model.fit(X_train, y_train)

    # Évaluation
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    # Sauvegarde modèle + encodeur
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(le, ENCODER_PATH)

    return TrainResponse(
        success=True,
        message=f"Modèle entraîné avec succès !",
        accuracy=round(accuracy * 100, 2),
        nb_matches=len(df)
    )


def predire(cote_dom: float, cote_nul: float, cote_ext: float) -> PredictionOutput:
    """
    Prédit le résultat d'un match à partir des cotes.
    """
    if not MODEL_PATH.exists() or not ENCODER_PATH.exists():
        raise FileNotFoundError("Le modèle n'est pas encore entraîné. Veuillez d'abord entraîner.")

    model = joblib.load(MODEL_PATH)
    le = joblib.load(ENCODER_PATH)

    X = np.array([[cote_dom, cote_nul, cote_ext]])
    proba = model.predict_proba(X)[0]
    predicted_class = model.predict(X)[0]

    # Récupérer les labels dans l'ordre de l'encodeur
    classes = le.classes_  # ex: ['D', 'E', 'N']
    proba_dict = {cls: float(p) for cls, p in zip(classes, proba)}

    resultat_code = le.inverse_transform([predicted_class])[0]
    labels = {"D": "Domicile", "N": "Nul", "E": "Extérieur"}
    resultat_label = labels.get(resultat_code, resultat_code)

    return PredictionOutput(
        resultat=resultat_label,
        probabilite_dom=round(proba_dict.get("D", 0.0), 4),
        probabilite_nul=round(proba_dict.get("N", 0.0), 4),
        probabilite_ext=round(proba_dict.get("E", 0.0), 4),
        confiance=round(float(max(proba)), 4)
    )


def modele_existe() -> bool:
    return MODEL_PATH.exists() and ENCODER_PATH.exists()
