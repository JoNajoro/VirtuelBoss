import re
import pandas as pd
from typing import List, Tuple, Optional
from match import MatchCotes, MatchResultat


# ══════════════════════════════════════════════
#  UTILITAIRES COMMUNS
# ══════════════════════════════════════════════

def _to_float(token: str) -> float:
    return float(token.strip().replace(",", "."))

def _is_cote(token: str) -> bool:
    return bool(re.fullmatch(r"\d+[,\.]\d+", token.strip()))


def _normalize_team_line(ligne: str) -> str:
    # Remplace uniquement les séparateurs "vs", "v", "contre", etc. ENTRE équipes (avec word boundaries)
    ligne = re.sub(r"\s+(?:vs|contre)(?:\s+|$)", " ", ligne, flags=re.IGNORECASE)
    # Remplace "v" uniquement s'il est entouré d'espaces (séparateur vrai)
    ligne = re.sub(r"\s+v\s+", " ", ligne, flags=re.IGNORECASE)
    # Remplace les tirets/slashes
    ligne = re.sub(r"\s*[-–—/]\s*", " ", ligne)
    return re.sub(r"\s+", " ", ligne).strip()


def _strip_cotes_from_line(ligne: str) -> str:
    return re.sub(r"(?:\s*\d+[.,]\d+)+\s*$", "", ligne).strip()


def _extraire_cotes(ligne: str) -> List[float]:
    return [_to_float(m.group(0)) for m in re.finditer(r"\d+[.,]\d+", ligne)]


def _contains_cote(ligne: str) -> bool:
    return bool(re.search(r"\d+[.,]\d+", ligne))


def _is_score(token: str) -> bool:
    return bool(re.fullmatch(r"\d+:\d+", token.strip()))

def _score_to_dash(score: str) -> str:
    return score.strip().replace(":", "-")

def _compute_resultat(score: str) -> Tuple[str, int]:
    parts = score.split("-")
    a, b = int(parts[0]), int(parts[1])
    total = a + b
    if a > b:   res = "D"
    elif b > a: res = "E"
    else:       res = "N"
    return res, total

def _normaliser(nom: str) -> str:
    normalized = re.sub(r"[^\w\s]", "", nom, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip().lower()


def _normalize_team_name(nom: str) -> str:
    return _normalize_team_line(nom)


# ══════════════════════════════════════════════
#  NETTOYAGE BRUIT (logique notebook)
# ══════════════════════════════════════════════

def est_bruit(ligne: str) -> bool:
    """
    Détecte les lignes inutiles :
    - Score mi-temps : MT: 0:0
    - Minutes de buts : 2', 15' 82', ou numéros isolés genre 27, 38
    - Lignes vides
    """
    ligne = ligne.strip()
    if not ligne:
        return True
    # MT: score mi-temps
    if re.match(r"MT\s*:", ligne, re.IGNORECASE):
        return True
    # Minutes de buts : "2'" ou "15' 82'" ou combinaisons
    if re.fullmatch(r"(\d+'\s*)+", ligne):
        return True
    # Numéro isolé (ex: 27, 38 — sans apostrophe mais sur ligne seule)
    if re.fullmatch(r"\d+", ligne):
        return True
    return False

def _nettoyer_nom_equipe(ligne: str) -> str:
    """Supprime les marqueurs de minute associés à un nom d'équipe."""
    return re.sub(r"\s*(?:\d+'\s*)+$", "", ligne).strip()


def nettoyer_lignes(texte: str) -> List[str]:
    """Supprime toutes les lignes bruit du texte brut et nettoie les noms d'équipe."""
    return [_nettoyer_nom_equipe(l.strip()) for l in texte.splitlines()
            if l.strip() and not est_bruit(l)]


# ══════════════════════════════════════════════
#  LISTE D'ÉQUIPES CONNUES
# ══════════════════════════════════════════════

def construire_liste_equipes(df: Optional[pd.DataFrame] = None) -> List[str]:
    """
    Retourne la liste des équipes connues depuis le CSV.
    Triées par longueur décroissante pour éviter les sous-matches.
    """
    from csv_service import lire_csv
    if df is None:
        df = lire_csv()
    if df.empty:
        return []
    equipes = set(df["equipe_dom"]).union(set(df["equipe_ext"]))
    return sorted(equipes, key=len, reverse=True)

def trouver_equipes(ligne: str, equipes: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Cherche exactement 2 équipes dans une ligne de texte.
    Trie par ordre d'apparition dans la ligne.
    """
    trouvees = []
    ligne_norm = _normalize_team_line(ligne).lower()
    for eq in equipes:
        if eq.lower() in ligne_norm:
            trouvees.append(eq)
    if len(trouvees) != 2:
        return None, None
    trouvees.sort(key=lambda x: ligne.lower().find(x.lower()))
    return trouvees[0], trouvees[1]


# ══════════════════════════════════════════════
#  PARSER COTES — 2 formats supportés
# ══════════════════════════════════════════════

def _detecter_format_cotes(lignes: List[str]) -> str:
    """
    Détecte le format du texte de cotes :
    - "inline"  : "Leeds Manchester Red" sur une ligne, puis 3 cotes
    - "separe"  : Leeds / Manchester Red sur lignes séparées, puis 3 cotes
    """
    for i, ligne in enumerate(lignes):
        if _contains_cote(ligne):
            if i > 0:
                avant = lignes[i - 1]
                mots = _normalize_team_line(avant).split()
                if len(mots) >= 3 and not re.search(r"\b(?:vs|v|contre)\b", avant, flags=re.IGNORECASE):
                    return "inline"
            return "separe"
    return "separe"


def _split_inline_teams(ligne: str, equipes: List[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """Essaye de séparer deux équipes sur une ligne inline."""
    ligne = _strip_cotes_from_line(ligne)
    ligne = _normalize_team_line(ligne)
    if equipes is not None:
        ligne_norm = ligne.lower()
        for eq in equipes:
            if _normalize_team_line(eq).lower() == ligne_norm:
                return None, None

    mots = ligne.split()
    if len(mots) < 2:
        return None, None

    meilleure = (None, None)
    meilleur_score = -1
    for split in range(1, len(mots)):
        dom = " ".join(mots[:split]).strip()
        ext = " ".join(mots[split:]).strip()
        if not dom or not ext:
            continue
        if _is_cote(dom) or _is_score(dom) or _is_cote(ext) or _is_score(ext):
            continue
        score = 0
        if dom[0].isupper():
            score += 1
        if ext[0].isupper():
            score += 1
        if len(dom.split()) > 1:
            score += 1
        if len(ext.split()) > 1:
            score += 1
        if score > meilleur_score:
            meilleur_score = score
            meilleure = (dom, ext)
    return meilleure


def _parse_cotes_inline_simple(lignes: List[str], equipes: List[str] = None) -> List[MatchCotes]:
    """Parse un format inline sans liste d'équipes connues."""
    matches = []
    i = 0
    while i < len(lignes):
        ligne = lignes[i]
        if _is_cote(ligne):
            i += 1
            continue

        # Cas où l'équipe et les cotes sont sur la même ligne
        if _contains_cote(ligne) and not _is_cote(ligne):
            dom, ext = _split_inline_teams(ligne, equipes)
            cotes = _extraire_cotes(ligne)
            if dom and ext and len(cotes) >= 3:
                matches.append(MatchCotes(
                    equipe_dom=_normalize_team_name(dom),
                    equipe_ext=_normalize_team_name(ext),
                    cote_dom=cotes[0],
                    cote_nul=cotes[1],
                    cote_ext=cotes[2],
                ))
                i += 1
                continue

        cotes = []
        j = i + 1
        while j < len(lignes) and len(cotes) < 3:
            cotes.extend(_extraire_cotes(lignes[j]))
            j += 1
        if len(cotes) >= 3:
            dom, ext = _split_inline_teams(lignes[i], equipes)
            if dom and ext:
                matches.append(MatchCotes(
                    equipe_dom=_normalize_team_name(dom),
                    equipe_ext=_normalize_team_name(ext),
                    cote_dom=cotes[0],
                    cote_nul=cotes[1],
                    cote_ext=cotes[2],
                ))
                i = j
                continue
        i += 1
    return matches


def parse_cotes(texte: str, equipes: List[str] = None) -> List[MatchCotes]:
    """
    Parse le texte de cotes AVANT match.
    Supporte 2 formats :
      Format inline  → "Leeds Manchester Red\n4,73\n3,84\n1,70"
      Format séparé  → "Leeds\nManchester Red\n4,73\n3,84\n1,70"
    Si equipes est fourni, utilise trouver_equipes() pour les lignes inline.
    """
    lignes = nettoyer_lignes(texte)
    if not lignes:
        return []

    fmt = _detecter_format_cotes(lignes)

    if fmt == "inline":
        if equipes:
            matches = _parse_cotes_inline(lignes, equipes)
            if matches:
                return matches
        matches = _parse_cotes_inline_simple(lignes, equipes)
        if matches:
            return matches
        return _parse_cotes_separe(lignes)

    return _parse_cotes_separe(lignes)

def _parse_cotes_inline(lignes: List[str], equipes: List[str]) -> List[MatchCotes]:
    """
    Format : "Fulham Liverpool\n3,15\n4,07\n2,02"
    Utilise la liste des équipes connues pour identifier dom/ext.
    """
    matches = []
    i = 0
    while i < len(lignes):
        ligne = lignes[i]
        # Chercher une ligne contenant 2 équipes connues
        dom, ext = trouver_equipes(ligne, equipes)
        if dom is not None:
            cotes = []
            j = i + 1
            while j < len(lignes) and len(cotes) < 3:
                cotes.extend(_extraire_cotes(lignes[j]))
                j += 1
            if len(cotes) >= 3:
                matches.append(MatchCotes(
                    equipe_dom=_normalize_team_name(dom),
                    equipe_ext=_normalize_team_name(ext),
                    cote_dom=cotes[0],
                    cote_nul=cotes[1],
                    cote_ext=cotes[2],
                ))
                i = j
                continue
        i += 1
    return matches

def _parse_cotes_separe(lignes: List[str]) -> List[MatchCotes]:
    """
    Format : "Leeds\nManchester Red\n4,73\n3,84\n1,70"
    Détecte les blocs : 2 noms consécutifs + 3 cotes consécutives.
    """
    matches = []
    i = 0
    while i < len(lignes):
        if _is_cote(lignes[i]):
            i += 1
            continue
        # Collecter les noms jusqu'aux cotes
        noms = []
        j = i
        while j < len(lignes) and not _contains_cote(lignes[j]):
            noms.append(lignes[j])
            j += 1
        # Collecter 3 cotes, même si elles sont sur la même ligne ou groupées
        cotes = []
        while j < len(lignes) and len(cotes) < 3:
            cotes.extend(_extraire_cotes(lignes[j]))
            j += 1
        if len(noms) >= 2 and len(cotes) >= 3:
            matches.append(MatchCotes(
                equipe_dom=_normalize_team_name(noms[0]),
                equipe_ext=_normalize_team_name(noms[1]),
                cote_dom=cotes[0],
                cote_nul=cotes[1],
                cote_ext=cotes[2],
            ))
            i = j
        elif len(noms) == 1 and _split_inline_teams(noms[0]) != (None, None) and len(cotes) >= 3:
            dom, ext = _split_inline_teams(noms[0])
            matches.append(MatchCotes(
                equipe_dom=_normalize_team_name(dom),
                equipe_ext=_normalize_team_name(ext),
                cote_dom=cotes[0],
                cote_nul=cotes[1],
                cote_ext=cotes[2],
            ))
            i = j
        else:
            i += 1
    return matches


# ══════════════════════════════════════════════
#  PARSER RÉSULTATS (logique notebook améliorée)
# ══════════════════════════════════════════════

def _nettoyer_nom_equipe(ligne: str) -> str:
    """Supprime les marqueurs de minute associés à un nom d'équipe."""
    return re.sub(r"\s*(?:\d+'\s*)+$", "", ligne).strip()


def parse_resultats(texte: str) -> List[MatchResultat]:
    """
    Parse le texte de résultats après match.
    Utilise la stratégie du notebook :
      → nettoyer le bruit d'abord
      → chercher les scores (X:Y) dans les lignes
      → prendre dom = ligne[i-1], ext = ligne[i+1]
    Robuste aux minutes, numéros isolés, MT, lignes mal ordonnées.
    """
    lignes = nettoyer_lignes(texte)
    matches = []
    i = 0
    while i < len(lignes):
        if _is_score(lignes[i]):
            if i == 0 or i + 1 >= len(lignes):
                i += 1
                continue
            dom = _normalize_team_name(_nettoyer_nom_equipe(lignes[i - 1].strip()))
            score_raw = lignes[i].strip()
            ext = _normalize_team_name(_nettoyer_nom_equipe(lignes[i + 1].strip()))

            if not dom or not ext:
                i += 1
                continue

            # Vérifier que dom et ext ne sont pas eux-mêmes des scores ou cotes
            if _is_score(dom) or _is_cote(dom):
                i += 1
                continue
            if _is_score(ext) or _is_cote(ext):
                i += 1
                continue

            score = _score_to_dash(score_raw)
            resultat, total_buts = _compute_resultat(score)

            matches.append(MatchResultat(
                equipe_dom=dom,
                equipe_ext=ext,
                score=score,
                total_buts=total_buts,
                resultat=resultat,
            ))
            i += 2  # sauter ext pour éviter double lecture
        else:
            i += 1

    return matches


# ══════════════════════════════════════════════
#  FUSION cotes + résultats
# ══════════════════════════════════════════════

def fusionner(cotes: List[MatchCotes], resultats: List[MatchResultat]) -> List[dict]:
    """
    Joint les deux listes sur (equipe_dom, equipe_ext).
    Correspondance insensible à la casse et aux espaces.
    """
    idx = {
        (_normaliser(r.equipe_dom), _normaliser(r.equipe_ext)): r
        for r in resultats
    }
    fusionnes = []
    for c in cotes:
        key = (_normaliser(c.equipe_dom), _normaliser(c.equipe_ext))
        r = idx.get(key)
        if r:
            fusionnes.append({
                "equipe_dom":  c.equipe_dom,
                "equipe_ext":  c.equipe_ext,
                "cote_dom":    c.cote_dom,
                "cote_nul":    c.cote_nul,
                "cote_ext":    c.cote_ext,
                "score":       r.score,
                "total_buts":  r.total_buts,
                "resultat":    r.resultat,
            })
    return fusionnes
