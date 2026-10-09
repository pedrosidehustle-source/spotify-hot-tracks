# spotify-hot-tracks

Génère des playlists de soirée à partir de **tes** habitudes d'écoute Spotify : croise tes tops d'écoute (4 semaines, 6 mois, long terme) avec tes titres likés, calcule un score par titre, puis répartit les meilleurs en 4 sets (Apéro, Montée, Peak, Fin de nuit) directement dans ton compte.

Version actuelle : **1.2** (2026-10-09). Testé sous Windows 10/11, Python 3.

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

5. Exporte un CSV scoré (`hot_tracks_AAAAMMJJ_HHMM.csv`, séparateur `;`).
6. Crée dans ton compte, en privé : une playlist maître (top 100) et 4 playlists de set (18 titres max chacune).

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
5. Optionnel : dépose ton export Exportify des titres likés, renommé `Liked_Songs.csv`, dans le dossier.
6. Double-clic sur `LANCER.bat`. Au premier lancement, autorise l'application dans le navigateur.

## Paramètres

En tête de `spotify_hot_tracks.py` : `TOP_N_PLAYLIST`, `POIDS`, `BONUS_LIKE`, `TAILLE_SET`, `SEUIL_ENERGIE_APERO`, `SEUIL_ENERGIE_MONTEE`, `SEUIL_DANSE_PEAK`, `REMPLIR_SETS_AUTO`, noms des playlists.

Relancer le script remplace le contenu des playlists existantes du même nom. Pour conserver un set retouché à la main, passe `REMPLIR_SETS_AUTO = False`.

## Limites connues

- L'API Spotify donne un **classement**, pas un nombre d'écoutes.
- Seuls les titres présents dans au moins un des 3 tops sont scorés (environ 300 titres maximum).
- La règle de phase repose sur l'énergie : elle sous-classe les titres très dansants à énergie modérée (reggae, dub, dancehall).
- Les titres non likés n'ont pas d'audio features et ne sont répartis dans aucun set.

## Historique

| Version | Date | Changement |
|---|---|---|
| 1.2 | 2026-10-09 | Migration vers les endpoints Web API de février 2026 (`POST /me/playlists`, `/playlists/{id}/items`) : corrige l'erreur 403 à la création des playlists |
| 1.1 | 2026-09-14 | Jointure Exportify, phases de soirée, remplissage automatique des sets |
| 1.0 | 2026-09-14 | Scoring tops × likes, CSV, playlist maître |

## Confidentialité

`credentials.txt`, `.cache_spotify` (jeton d'accès) et tes CSV sont exclus du dépôt par `.gitignore`. Ne les publie jamais.

## Licence

MIT
