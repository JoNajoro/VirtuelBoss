from pydantic import BaseModel
from typing import Optional


class MatchCotes(BaseModel):
    equipe_dom: str
    equipe_ext: str
    cote_dom: float
    cote_nul: float
    cote_ext: float


class MatchResultat(BaseModel):
    equipe_dom: str
    equipe_ext: str
    score: str          # ex: "2-1"
    total_buts: int
    resultat: str       # "D", "N", "E"


class MatchComplet(BaseModel):
    equipe_dom: str
    equipe_ext: str
    cote_dom: float
    cote_nul: float
    cote_ext: float
    score: str
    total_buts: int
    resultat: str


class PredictionInput(BaseModel):
    cote_dom: float
    cote_nul: float
    cote_ext: float


class PredictionOutput(BaseModel):
    resultat: str           # "Domicile", "Nul", "Extérieur"
    probabilite_dom: float
    probabilite_nul: float
    probabilite_ext: float
    confiance: float


class TrainResponse(BaseModel):
    success: bool
    message: str
    accuracy: Optional[float] = None
    nb_matches: Optional[int] = None
