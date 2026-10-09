# -*- coding: utf-8 -*-
"""
spotify_hot_tracks.py
Version 1.2 - 2026-10-09

Croise tes titres likes et tes tops d'ecoute Spotify (4 semaines / 6 mois / long terme),
calcule un score par titre, exporte un CSV et cree les playlists dans ton compte.

Pre-requis : credentials.txt a cote de ce fichier (voir README.md), spotipy installe (INSTALLER.bat).

v1.1 : si un export Exportify "Liked_Songs.csv" est present a cote du script, ses audio features
(energie, tempo, dansabilite, valence, genres) sont jointes par Track URI, une phase de soiree est
proposee par titre et les 4 playlists de set sont remplies automatiquement.

v1.2 : migration vers les endpoints Web API de fevrier 2026 (les anciens renvoient 403) :
POST /users/{id}/playlists -> POST /me/playlists ; PUT/POST /playlists/{id}/tracks -> /playlists/{id}/items.
"""

VERSION = "1.2"
DATE_VERSION = "2026-10-09"

import sys
import os
import csv
import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except ImportError:
    print("ERREUR : la librairie spotipy n'est pas installee. Lance INSTALLER.bat puis relance.")
    input("Appuie sur Entree pour fermer.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# PARAMETRES (modifiables)
# ---------------------------------------------------------------------------
TOP_N_PLAYLIST = 100                     # nb de titres dans la playlist maitre
POIDS = {                                # poids de chaque horizon d'ecoute
    "long_term": 3.0,                    # ~ historique long
    "medium_term": 2.0,                  # ~ 6 derniers mois
    "short_term": 1.0,                   # ~ 4 dernieres semaines
}
BONUS_LIKE = 1.0                         # bonus si le titre est dans "Titres likes"
NOM_PLAYLIST_MAITRE = "40 ans - HOT TRACKS (score)"
CREER_SETS = True                        # cree les 4 playlists de set
REMPLIR_SETS_AUTO = True                 # les remplit depuis Liked_Songs.csv (sinon vides)
TAILLE_SET = 18                          # nb max de titres par set
NOMS_SETS = {
    "apero":  "40 ans - 1. Apero",
    "montee": "40 ans - 2. Montee",
    "peak":   "40 ans - 3. Peak",
    "fin":    "40 ans - 4. Fin de nuit",
}
# Regles de phase (heuristique, a ajuster a l'oreille) sur les audio features Spotify (0 a 1)
SEUIL_ENERGIE_APERO = 0.50               # energie < seuil          -> apero
SEUIL_ENERGIE_MONTEE = 0.65              # seuil apero <= energie < seuil -> montee
SEUIL_DANSE_PEAK = 0.70                  # energie >= montee et dansabilite >= seuil -> peak, sinon -> fin de nuit
FICHIER_EXPORTIFY = "Liked_Songs.csv"    # export Exportify (optionnel)

# ---------------------------------------------------------------------------
# CONSTANTES TECHNIQUES
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CRED_FILE = os.path.join(BASE_DIR, "credentials.txt")
CACHE_FILE = os.path.join(BASE_DIR, ".cache_spotify")
REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = "user-top-read user-library-read playlist-modify-private playlist-read-private"
LIBELLES = {"short_term": "4 semaines", "medium_term": "6 mois", "long_term": "long terme"}


def entete():
    print("=" * 70)
    print(f"  spotify_hot_tracks  -  version {VERSION}  ({DATE_VERSION})")
    print("=" * 70)
    print()


def lire_credentials():
    if not os.path.exists(CRED_FILE):
        print(f"ERREUR : fichier introuvable : {CRED_FILE}")
        print("Cree-le avec deux lignes : CLIENT_ID=... et CLIENT_SECRET=... (voir README.md)")
        return None, None
    cid, secret = None, None
    with open(CRED_FILE, encoding="utf-8") as f:
        for ligne in f:
            ligne = ligne.strip()
            if ligne.startswith("CLIENT_ID="):
                cid = ligne.split("=", 1)[1].strip()
            elif ligne.startswith("CLIENT_SECRET="):
                secret = ligne.split("=", 1)[1].strip()
    if not cid or not secret or "colle_ici" in (cid + secret):
        print("ERREUR : CLIENT_ID ou CLIENT_SECRET manquant / non renseigne dans credentials.txt")
        return None, None
    return cid, secret


def connexion(cid, secret):
    auth = SpotifyOAuth(
        client_id=cid,
        client_secret=secret,
        redirect_uri=REDIRECT_URI,
        scope=SCOPES,
        cache_path=CACHE_FILE,
        open_browser=True,
    )
    sp = spotipy.Spotify(auth_manager=auth, requests_timeout=30, retries=3)
    me = sp.current_user()
    print(f"Connecte : {me.get('display_name')}  (id : {me['id']})")
    return sp, me["id"]


def recuperer_top(sp, horizon):
    """Retourne la liste des tracks du top pour un horizon (jusqu'a 100)."""
    tracks = []
    for offset in (0, 50):
        try:
            res = sp.current_user_top_tracks(limit=50, offset=offset, time_range=horizon)
        except Exception as e:
            if offset == 0:
                print(f"  ! erreur top {LIBELLES[horizon]} : {e}")
            break
        items = res.get("items", [])
        tracks.extend(items)
        if len(items) < 50:
            break
    print(f"  Top {LIBELLES[horizon]:<12}: {len(tracks)} titres")
    return tracks


def recuperer_likes(sp):
    """Retourne un dict uri -> track pour l'ensemble des titres likes."""
    likes = {}
    offset = 0
    while True:
        res = sp.current_user_saved_tracks(limit=50, offset=offset)
        items = res.get("items", [])
        for it in items:
            t = it.get("track")
            if t and t.get("uri"):
                likes[t["uri"]] = t
        if len(items) < 50:
            break
        offset += 50
        if offset % 500 == 0:
            print(f"  ... {offset} likes lus")
    print(f"  Titres likes       : {len(likes)} titres")
    return likes


def infos_track(t):
    artistes = ", ".join(a["name"] for a in t.get("artists", []))
    album = t.get("album", {}) or {}
    date = album.get("release_date") or ""
    annee = date[:4] if date else ""
    duree_ms = t.get("duration_ms") or 0
    duree = f"{duree_ms // 60000}:{(duree_ms // 1000) % 60:02d}"
    return {
        "titre": t.get("name", ""),
        "artistes": artistes,
        "album": album.get("name", ""),
        "annee": annee,
        "duree": duree,
        "popularite": t.get("popularity", ""),
        "uri": t.get("uri", ""),
    }


def lire_exportify():
    """Lit l'export Exportify s'il existe. Retourne dict uri -> features (ou {})."""
    chemin = os.path.join(BASE_DIR, FICHIER_EXPORTIFY)
    if not os.path.exists(chemin):
        print(f"  Export Exportify   : absent ({FICHIER_EXPORTIFY}) -> pas de phases automatiques")
        return {}
    feats = {}
    with open(chemin, encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            uri = (row.get("Track URI") or "").strip()
            if not uri:
                continue
            try:
                feats[uri] = {
                    "energie": float(row.get("Energy") or 0),
                    "tempo": round(float(row.get("Tempo") or 0)),
                    "danse": float(row.get("Danceability") or 0),
                    "valence": float(row.get("Valence") or 0),
                    "genres": (row.get("Genres") or "").strip(),
                }
            except ValueError:
                continue
    print(f"  Export Exportify   : {len(feats)} titres avec audio features")
    return feats


def phase_de(feat):
    """Attribue une phase de soiree a partir des features. Retourne une cle de NOMS_SETS ou ''."""
    if not feat:
        return ""
    e, d = feat["energie"], feat["danse"]
    if e < SEUIL_ENERGIE_APERO:
        return "apero"
    if e < SEUIL_ENERGIE_MONTEE:
        return "montee"
    return "peak" if d >= SEUIL_DANSE_PEAK else "fin"


def scorer(tops, likes):
    """Construit le tableau scoré. Retourne une liste de dicts triée par score décroissant."""
    table = {}

    def ligne(t):
        uri = t["uri"]
        if uri not in table:
            d = infos_track(t)
            d.update({"score": 0.0, "like": "", "rang_4sem": "", "rang_6mois": "", "rang_long": "",
                      "phase": "", "energie": "", "tempo": "", "danse": "", "valence": "", "genres": ""})
            table[uri] = d
        return table[uri]

    cle_rang = {"short_term": "rang_4sem", "medium_term": "rang_6mois", "long_term": "rang_long"}
    for horizon, tracks in tops.items():
        n = len(tracks)
        for i, t in enumerate(tracks):
            if not t or not t.get("uri"):
                continue
            d = ligne(t)
            d[cle_rang[horizon]] = i + 1
            d["score"] += POIDS[horizon] * (n - i) / n

    for uri, t in likes.items():
        if uri in table:
            table[uri]["like"] = "oui"
            table[uri]["score"] += BONUS_LIKE

    lignes = sorted(table.values(), key=lambda d: d["score"], reverse=True)
    for i, d in enumerate(lignes):
        d["rang"] = i + 1
        d["score"] = round(d["score"], 3)
    return lignes


def enrichir(lignes, feats):
    """Joint les audio features et la phase proposee sur chaque ligne scoree."""
    nb = 0
    for d in lignes:
        f = feats.get(d["uri"])
        if not f:
            continue
        nb += 1
        d.update(f)
        d["phase"] = NOMS_SETS[phase_de(f)].split(" - ")[1] if phase_de(f) else ""
    print(f"Titres scores avec features : {nb}/{len(lignes)}")
    return lignes


def repartir_sets(lignes, feats):
    """Retourne dict cle_phase -> liste d'uris (top score, plafond TAILLE_SET)."""
    sets = {k: [] for k in NOMS_SETS}
    for d in lignes:
        k = phase_de(feats.get(d["uri"]))
        if k and len(sets[k]) < TAILLE_SET:
            sets[k].append(d["uri"])
    return sets


def ecrire_csv(lignes):
    horodatage = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    chemin = os.path.join(BASE_DIR, f"hot_tracks_{horodatage}.csv")
    colonnes = ["rang", "score", "titre", "artistes", "album", "annee", "like", "phase",
                "energie", "tempo", "danse", "valence", "genres",
                "rang_4sem", "rang_6mois", "rang_long", "popularite", "duree", "uri"]
    with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=colonnes, delimiter=";")
        w.writeheader()
        for d in lignes:
            w.writerow({c: d.get(c, "") for c in colonnes})
    print(f"CSV ecrit : {chemin}  ({len(lignes)} lignes)")
    return chemin


def playlists_existantes(sp):
    noms = {}
    offset = 0
    while True:
        res = sp.current_user_playlists(limit=50, offset=offset)
        items = res.get("items", [])
        for p in items:
            noms[p["name"]] = p["id"]
        if len(items) < 50:
            break
        offset += 50
    return noms


def creer_playlist(sp, user_id, nom, description, uris, existantes):
    if nom in existantes:
        pid = existantes[nom]
        print(f"  Playlist deja existante, reutilisee : {nom}")
    else:
        # v1.2 : POST /me/playlists (POST /users/{id}/playlists supprime par Spotify en fev. 2026)
        p = sp._post("me/playlists", payload={"name": nom, "public": False, "description": description})
        pid = p["id"]
        print(f"  Playlist creee : {nom}")
    if uris:
        # v1.2 : /playlists/{id}/items (/tracks supprime par Spotify en fev. 2026)
        sp._put(f"playlists/{pid}/items", payload={"uris": uris[:100]})
        for i in range(100, len(uris), 100):
            sp._post(f"playlists/{pid}/items", payload={"uris": uris[i:i + 100]})
        print(f"    -> {len(uris)} titres charges")
    return pid


def main():
    entete()
    cid, secret = lire_credentials()
    if not cid:
        return 1

    print("Connexion a Spotify (une fenetre navigateur peut s'ouvrir la premiere fois)...")
    sp, user_id = connexion(cid, secret)
    print()

    print("Lecture des donnees :")
    tops = {h: recuperer_top(sp, h) for h in ("long_term", "medium_term", "short_term")}
    likes = recuperer_likes(sp)
    feats = lire_exportify()
    print()

    lignes = scorer(tops, likes)
    lignes = enrichir(lignes, feats)
    nb_likes_dans_top = sum(1 for d in lignes if d["like"] == "oui")
    print(f"Titres scores : {len(lignes)}  (dont {nb_likes_dans_top} likes)")
    print()
    print("Top 15 :")
    for d in lignes[:15]:
        ph = f"  [{d['phase']}]" if d["phase"] else ""
        print(f"  {d['rang']:>3}. {d['score']:>5.2f}  {d['artistes']} - {d['titre']}{ph}")
    print()

    ecrire_csv(lignes)
    print()

    print("Creation des playlists :")
    existantes = playlists_existantes(sp)
    uris = [d["uri"] for d in lignes[:TOP_N_PLAYLIST]]
    desc = f"Top {TOP_N_PLAYLIST} scores likes x ecoutes - genere par spotify_hot_tracks v{VERSION} le {datetime.date.today()}"
    creer_playlist(sp, user_id, NOM_PLAYLIST_MAITRE, desc, uris, existantes)
    if CREER_SETS:
        sets = repartir_sets(lignes, feats) if (REMPLIR_SETS_AUTO and feats) else {k: [] for k in NOMS_SETS}
        for k, nom in NOMS_SETS.items():
            d = "Set propose par energie/dansabilite (Exportify) - a ajuster" if sets[k] else "Set a remplir a la main depuis HOT TRACKS"
            creer_playlist(sp, user_id, nom, d, sets[k], existantes)
        if feats:
            print()
            print("Repartition proposee (sur l'ensemble des titres scores) :")
            compte = {k: 0 for k in NOMS_SETS}
            sans = 0
            for l in lignes:
                k = phase_de(feats.get(l["uri"]))
                if k:
                    compte[k] += 1
                else:
                    sans += 1
            for k, nom in NOMS_SETS.items():
                print(f"  {nom:<28}: {compte[k]:>3} candidats, {len(sets[k])} retenus")
            print(f"  sans features (likes post-export ou non likes) : {sans}")
    print()
    print("Termine.")
    return 0


if __name__ == "__main__":
    code = 0
    try:
        code = main()
    except Exception as e:
        print()
        print(f"ERREUR : {type(e).__name__} : {e}")
        code = 1
    print()
    input("Appuie sur Entree pour fermer.")
    sys.exit(code)
