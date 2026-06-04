import re
from typing import List, Tuple
from match import MatchCotes, MatchResultat


# ─────────────────────────────────────────────
# UTILITAIRES
# ─────────────────────────────────────────────

def _is_cote(token: str) -> bool:
    """Vérifie si un token est une cote (nombre décimal avec virgule ou point)."""
    return bool(re.fullmatch(r"\d+[,\.]\d+", token.strip()))


def _to_float(token: str) -> float:
    """Convertit une cote string en float (gère virgule et point)."""
    return float(token.strip().replace(",", "."))


def _is_score(token: str) -> bool:
    """Vérifie si un token est un score de match (ex: 2:1, 0:0, 6:0)."""
    return bool(re.fullmatch(r"\d+:\d+", token.strip()))


def _score_to_dash(score: str) -> str:
    """Convertit 2:1 → 2-1."""
    return score.strip().replace(":", "-")


def _compute_resultat(score: str) -> Tuple[str, int]:
    """
    À partir du score (ex: '2-1'), retourne (resultat, total_buts).
    resultat : 'D', 'N', 'E'
    """
    parts = score.split("-")
    buts_dom = int(parts[0])
    buts_ext = int(parts[1])
    total = buts_dom + buts_ext
    if buts_dom > buts_ext:
        resultat = "D"
    elif buts_ext > buts_dom:
        resultat = "E"
    else:
        resultat = "N"
    return resultat, total


def _clean_lines(raw_text: str) -> List[str]:
    """
    Nettoie le texte brut :
    - Supprime les minutes de buts (ex: 2', 15', 82')
    - Supprime les scores de mi-temps (ex: MT: 3:0)
    - Supprime les lignes vides
    """
    lines = raw_text.splitlines()
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Supprimer "MT: ..." (score mi-temps)
        if re.match(r"MT\s*:", line, re.IGNORECASE):
            continue
        # Supprimer les minutes de buts (tokens comme 2', 15', 82', 61'69').
        line = re.sub(r"\d+'", "", line)
        line = re.sub(r"[ \t]+", " ", line).strip()
        if not line:
            continue
        # Ignorer les lignes trop courtes et inutiles (ex: X seul).
        if len(line) == 1 and line.isalpha():
            continue
        cleaned.append(line)
    return cleaned


# ─────────────────────────────────────────────
# PARSER COTES (capture avant match)
# ─────────────────────────────────────────────

def parse_cotes(raw_text: str) -> List[MatchCotes]:
    """
    Parse le texte brut de la capture AVANT match.
    Pattern attendu (répété) :
        Equipe_Dom
        Equipe_Ext
        cote_dom
        cote_nul
        cote_ext
    """
    lines = _clean_lines(raw_text)
    matches = []
    i = 0

    while i < len(lines):
        # On cherche un bloc : 2 noms + 3 cotes
        # Lire jusqu'à trouver 3 cotes consécutives
        if _is_cote(lines[i]):
            i += 1
            continue

        # Collecter les noms jusqu'aux cotes
        noms = []
        j = i
        while j < len(lines) and not _is_cote(lines[j]):
            noms.append(lines[j])
            j += 1

        # Collecter les 3 cotes
        cotes = []
        while j < len(lines) and _is_cote(lines[j]) and len(cotes) < 3:
            cotes.append(_to_float(lines[j]))
            j += 1

        if len(noms) >= 2 and len(cotes) == 3:
            equipe_dom = noms[0].strip()
            equipe_ext = noms[1].strip()
            matches.append(MatchCotes(
                equipe_dom=equipe_dom,
                equipe_ext=equipe_ext,
                cote_dom=cotes[0],
                cote_nul=cotes[1],
                cote_ext=cotes[2]
            ))
            i = j
        else:
            i += 1

    return matches


# ─────────────────────────────────────────────
# PARSER RESULTATS (capture après match)
# ─────────────────────────────────────────────

def parse_resultats(raw_text: str) -> List[MatchResultat]:
    """
    Parse le texte brut de la capture RÉSULTAT.
    Pattern attendu (répété, avec minutes optionnelles déjà supprimées) :
        Equipe_Dom
        score_final   (ex: 6:0)
        Equipe_Ext
    """
    lines = _clean_lines(raw_text)
    matches = []
    i = 0

    while i < len(lines):
        # On cherche les deux principaux patterns :
        # 1) Equipe_Dom
        #    score_final
        #    Equipe_Ext
        # 2) Equipe_Dom
        #    Equipe_Ext
        #    score_final
        if _is_score(lines[i]):
            i += 1
            continue

        # Pattern 1 : nom -> score -> nom
        if i + 2 < len(lines) and _is_score(lines[i + 1]):
            equipe_dom = lines[i].strip()
            score_raw = lines[i + 1].strip()
            equipe_ext = lines[i + 2].strip()
            i += 3
        # Pattern 2 : nom -> nom -> score
        elif i + 2 < len(lines) and not _is_score(lines[i + 1]) and _is_score(lines[i + 2]):
            equipe_dom = lines[i].strip()
            equipe_ext = lines[i + 1].strip()
            score_raw = lines[i + 2].strip()
            i += 3
        else:
            i += 1
            continue

        score = _score_to_dash(score_raw)
        resultat, total_buts = _compute_resultat(score)

        matches.append(MatchResultat(
            equipe_dom=equipe_dom,
            equipe_ext=equipe_ext,
            score=score,
            total_buts=total_buts,
            resultat=resultat
        ))

    return matches


# ─────────────────────────────────────────────
# FUSION cotes + résultats
# ─────────────────────────────────────────────

def fusionner(cotes: List[MatchCotes], resultats: List[MatchResultat]) -> List[dict]:
    """
    Fusionne les deux listes en utilisant les noms des équipes comme clé.
    Correspondance insensible à la casse et aux espaces.
    """
    def normaliser(nom: str) -> str:
        return nom.strip().lower()

    resultats_index = {
        (normaliser(r.equipe_dom), normaliser(r.equipe_ext)): r
        for r in resultats
    }

    fusionnes = []
    for c in cotes:
        key = (normaliser(c.equipe_dom), normaliser(c.equipe_ext))
        r = resultats_index.get(key)
        if r:
            fusionnes.append({
                "equipe_dom": c.equipe_dom,
                "equipe_ext": c.equipe_ext,
                "cote_dom": c.cote_dom,
                "cote_nul": c.cote_nul,
                "cote_ext": c.cote_ext,
                "score": r.score,
                "total_buts": r.total_buts,
                "resultat": r.resultat
            })

    return fusionnes
