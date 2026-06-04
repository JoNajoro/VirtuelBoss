# Match Predictor

Application de prédiction de matchs basée sur les cotes (XGBoost).

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

Copiez `.env.example` en `.env` et renseignez votre clé Google Vision API :

```bash
cp .env.example .env
```

Obtenez une clé sur : https://console.cloud.google.com/apis/library/vision.googleapis.com

## Lancement

```bash
uvicorn main:app --reload
```

L'application sera disponible sur : http://localhost:8000

## Utilisation

### 1. Collecte de données
- Allez sur http://localhost:8000
- Onglet **Texte brut** : collez directement le texte extrait par Google Lens
- Onglet **Image** : uploadez les captures (nécessite clé Google Vision)
- Les données sont sauvegardées automatiquement dans `backend/data/matches.csv`

### 2. Entraînement
- Allez sur http://localhost:8000/predict
- Cliquez **Entraîner le modèle** (minimum 10 matchs requis)

### 3. Prédiction
- Entrez les 3 cotes d'un match
- Cliquez **Prédire le résultat**

## API

Documentation interactive : http://localhost:8000/docs

### Endpoints principaux

| Méthode | Route | Description |
|---|---|---|
| POST | /extraction/texte/fusionner-et-sauvegarder | Parser textes + sauvegarder CSV |
| POST | /extraction/fusionner-et-sauvegarder | Upload images + OCR + sauvegarder |
| GET | /data/matches | Lister tous les matchs |
| GET | /data/stats | Statistiques CSV |
| DELETE | /data/match/{index} | Supprimer un match |
| GET | /data/export | Télécharger le CSV |
| POST | /prediction/entrainer | Entraîner le modèle |
| POST | /prediction/predire | Prédire un résultat |
| GET | /prediction/statut | Statut du modèle |

## Structure CSV

| Colonne | Description |
|---|---|
| equipe_dom | Nom de l'équipe domicile |
| equipe_ext | Nom de l'équipe extérieure |
| cote_dom | Cote victoire domicile |
| cote_nul | Cote match nul |
| cote_ext | Cote victoire extérieure |
| score | Score final (ex: 2-1) |
| total_buts | Total de buts du match |
| resultat | D (domicile), N (nul), E (extérieur) |
