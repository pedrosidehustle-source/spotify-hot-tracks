# spotify-hot-tracks

Génère des playlists de soirée à partir de **tes** habitudes d'écoute Spotify : croise tes tops d'écoute (4 semaines, 6 mois, long terme) avec tes titres likés, calcule un score par titre, puis répartit les meilleurs en 4 sets (Apéro, Montée, Peak, Fin de nuit) directement dans ton compte.

Version actuelle : **1.3** (2026-10-09). Testé sous Windows 10/11, Python 3.

## Ce que fait le script

1. Lit tes 3 tops d'écoute via l'API Spotify (100 titres max chacun).
2. Lit tous tes titres likés.
3. Score chaque titre : `poids × (100 − rang + 1) / 100` par horizon (long terme ×3, 6 mois ×2, 4 semaines ×1), +1 si liké. Maximum : 7.
4. Optionnel : joint les audio features d'un export [Exportify](https://exportify.net) (`Liked_Songs.csv`) et attribue une phase de soirée :

   | Phase | Règle |
   |---|---|
   | 1. Apéro | énergie < 0,50 |
   | 2. Montée | 0,50 ≤ énergie < 0,65 |
   | 3. Peak | énergie ≥ 0,65 et dansabilité ≥ 0,70 |
   | 4. Fin de nuit | énergie ≥ 0,65 et dansabilité < 0,70 |

5. Construit une playlist **SOIREE (style x bpm)** : les meilleurs scores jusqu'à une durée cible (6 h par défaut), regroupés par famille de style enchaînées dans l'ordre de la soirée, et triés par **BPM corrigé** à l'intérieur de chaque famille.

   | Ordre | Famille | Plage BPM corrigée | Tri |
   |---|---|---|---|
   | 1 | Chill / jazz / soul lente | 70-139 | croissant |
   | 2 | Roots / lovers / rocksteady | 60-119 | croissant |
   | 3 | Funk / soul / disco | 90-179 | croissant |
   | 4 | Pop / chanson / rock | 80-159 | croissant |
   | 5 | Afro / tropical | 85-169 | croissant |
   | 6 | Hip-hop / rap | 70-139 | croissant |
   | 7 | Dancehall / ragga / shatta | 75-149 | croissant |
   | 8 | House / électro | 95-189 | croissant |
   | 9 | Jungle / drum & bass | 160-319 | croissant |
   | 10 | Dub (fin de nuit) | 60-119 | décroissant |

   - **Famille** : celle qui correspond au plus grand nombre de genres Spotify du titre (égalité : la plus dansante). Sans genre : famille devinée via énergie et dansabilité.
   - **BPM corrigé** : Spotify détecte souvent le double ou la moitié du tempo réel (typique en reggae : 75 ou 150 BPM pour le même riddim). Le tempo est ramené par ×2 ou ÷2 dans la plage naturelle de la famille.
   - Dans Spotify : **Mix > Auto, sans Smart Reorder**, pour garder cet ordre.

6. Exporte un CSV scoré (`hot_tracks_AAAAMMJJ_HHMM.csv`, séparateur `;`).
7. Crée dans ton compte, en privé : la playlist maître (tout l'univers scoré), les 4 playlists de set (18 titres max chacune) et la playlist SOIREE.

Pourquoi Exportify : Spotify a fermé l'accès aux audio features (énergie, tempo, dansabilité) pour les nouvelles applications fin 2024. Exportify les fournit encore dans son export CSV.

## Installation (Windows, sans ligne de commande)

1. Télécharge le dépôt (bouton vert **Code** > **Download ZIP**) et dézippe-le, par exemple dans `C:\Outils\`.
2. Crée une application Spotify sur <https://developer.spotify.com/dashboard> :
   - **Redirect URI** : `http://127.0.0.1:8888/callback` (au caractère près)
   - API : coche **Web API**
   - Dans **Settings**, copie le *Client ID* et le *Client secret*.
3. Double-clic sur `INSTALLER.bat` : installe la librairie `spotipy` et crée `credentials.txt`.
   Si Python est introuvable : installe-le depuis <https://python.org> en cochant **Add python.exe to PATH**.
4. Ouvre `credentials.txt` avec le Bloc-notes et remplace les deux `colle_ici`.
5. Optionnel : dépose dans le dossier tes exports Exportify (titres likés, et idéalement la playlist HOT TRACKS après un premier lancement pour couvrir aussi les titres non likés). Tous les CSV Exportify du dossier sont lus.
6. Double-clic sur `LANCER.bat`. Au premier lancement, autorise l'application dans le navigateur.

## Paramètres

En tête de `spotify_hot_tracks.py` : `DUREE_SOIREE_H`, `FAMILLES` (ordre, mots-clés, plages BPM), `PRIORITE_EGALITE`, `FAMILLE_SANS_GENRE`, `TOP_N_PLAYLIST`, `POIDS`, `BONUS_LIKE`, `TAILLE_SET`, `SEUIL_ENERGIE_APERO`, `SEUIL_ENERGIE_MONTEE`, `SEUIL_DANSE_PEAK`, `REMPLIR_SETS_AUTO`, noms des playlists.

Relancer le script remplace le contenu des playlists existantes du même nom. Pour conserver un set retouché à la main, passe `REMPLIR_SETS_AUTO = False`.

## Limites connues

- L'API Spotify donne un **classement**, pas un nombre d'écoutes.
- Seuls les titres présents dans au moins un des 3 tops sont scorés (environ 300 titres maximum).
- La règle de phase repose sur l'énergie : elle sous-classe les titres très dansants à énergie modérée (reggae, dub, dancehall).
- Les titres absents des exports Exportify n'ont pas d'audio features : ils ne sont répartis dans aucun set ni dans la playlist SOIREE.
- Les genres Spotify sont ceux de l'**artiste**, pas du titre : un artiste reggae qui sort un titre house reste classé reggae.
- La correction de BPM est une approximation : un titre hors de toute plage naturelle (ex. UK garage à 135 dans House) peut rester mal placé.

## Historique

| Version | Date | Changement |
|---|---|---|
| 1.3 | 2026-10-09 | Playlist SOIREE (famille de style × BPM corrigé, durée cible), lecture de tous les exports Exportify du dossier, playlist maître étendue à tout l'univers scoré |
| 1.2 | 2026-10-09 | Migration vers les endpoints Web API de février 2026 (`POST /me/playlists`, `/playlists/{id}/items`) : corrige l'erreur 403 à la création des playlists |
| 1.1 | 2026-09-14 | Jointure Exportify, phases de soirée, remplissage automatique des sets |
| 1.0 | 2026-09-14 | Scoring tops × likes, CSV, playlist maître |

## Confidentialité

`credentials.txt`, `.cache_spotify` (jeton d'accès) et tes CSV sont exclus du dépôt par `.gitignore`. Ne les publie jamais.

## Licence

MIT
