---
name: analyse-video
description: Décortique une vidéo à partir d'un lien (YouTube, Facebook, Telegram, Instagram, TikTok…) ou d'un fichier vidéo joint, puis l'explique en français étape par étape pour en discuter ensuite. Utiliser quand Etienne envoie un lien ou un fichier vidéo et demande de la regarder, l'analyser, la résumer, la décortiquer, en tirer les étapes, ou demande « qu'est-ce qu'on voit dans cette vidéo ».
---

# Analyse vidéo

Objectif : « regarder » une vidéo en combinant des images clés et la
transcription de la parole, puis en faire une explication claire, en
français, étape par étape, et ouvrir la discussion avec Etienne.

## 1. Lancer l'extraction

```bash
python3 .claude/skills/analyse-video/scripts/analyse_video.py "<LIEN_OU_FICHIER>" \
  --out "<dossier-scratchpad>/analyse-video/<nom-court>"
```

- `<LIEN_OU_FICHIER>` : le lien donné par Etienne, ou le chemin du fichier
  joint (les pièces jointes sont dans `~/.claude/uploads/…`).
- Mettre la sortie dans le dossier scratchpad de la session (jamais dans le dépôt).
- Options utiles : `--langue fr` si la détection hésite, `--max-images 60`
  pour une longue vidéo (plus de 15 min) ou un tutoriel très visuel,
  `--modele medium` si la transcription est de mauvaise qualité
  (plus lent), `--sans-transcription` pour une vidéo sans parole utile.
- Le script installe lui-même `yt-dlp`, `faster-whisper` et `pillow` au
  besoin. Il faut `ffmpeg`. La transcription d'une vidéo de 10 min prend
  quelques minutes sur CPU : lancer en arrière-plan si c'est long et
  prévenir Etienne.

### Si le téléchargement échoue
- **Session cloud** : YouTube, Facebook et Telegram sont généralement
  bloqués par le réseau. Ne pas insister : demander à Etienne de
  télécharger la vidéo et de la joindre au message, ou d'utiliser
  Claude Code sur son ordinateur, où les liens fonctionnent.
- **Vidéo privée / connexion requise** (Facebook, groupes Telegram) : même
  solution, le fichier joint.

## 2. Regarder et lire

1. Lire `infos.json` s'il existe (titre, auteur, description : la
   description contient souvent des liens et des étapes).
2. Lire `transcription.md` en entier.
3. Ouvrir **chaque** planche `planches/planche_XX.jpg` avec l'outil Read.
   Chaque vignette porte son numéro et son horodatage. Pour un détail
   illisible (texte à l'écran, menu, code), ouvrir l'image individuelle
   `images/img_NNN.jpg`, ou extraire une image précise :
   `ffmpeg -ss <secondes> -i <video> -frames:v 1 -vf scale=1280:-2 detail.jpg`

Ne rien inventer : décrire seulement ce qui est vu ou entendu. Si un
passage est flou ou inaudible, le dire.

## 3. Restituer à Etienne (en français)

Structure de la réponse :

1. **En bref** : 2-3 phrases : de quoi parle la vidéo, qui parle, pour qui.
2. **Les étapes** : liste numérotée, chacune avec son horodatage
   `[mm:ss]`, ce qui est fait ou montré, et les outils, sites, réglages ou
   chiffres mentionnés.
3. **Outils et liens cités** : tableau si plusieurs.
4. **Ce qui manque ou reste flou** : étapes sautées, éléments payants,
   prérequis non dits.
5. **Pour vous** : en quoi ça s'applique (ou pas) à l'activité d'Etienne
   (photographie immobilière, CRM, marketing), et proposer la suite :
   « On applique quelle étape en premier ? » ou proposer de le faire.

Garder la transcription et les planches à portée de main : Etienne va
poser des questions sur des passages précis ; y revenir plutôt que de
répondre de mémoire.
