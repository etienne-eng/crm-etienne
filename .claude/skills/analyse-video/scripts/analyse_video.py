#!/usr/bin/env python3
"""Décortique une vidéo (lien ou fichier) pour que Claude puisse l'analyser.

Étapes :
  1. Télécharge la vidéo si on donne un lien (yt-dlp : YouTube, Facebook,
     Telegram, Instagram, TikTok, etc.).
  2. Extrait des images clés à intervalle régulier et les assemble en
     planches numérotées avec l'horodatage de chaque image.
  3. Transcrit la parole avec Whisper (faster-whisper), langue détectée
     automatiquement.

Sortie (dans --out) :
  video.<ext>          la vidéo (si téléchargée)
  infos.json           titre, auteur, description, durée (si disponible)
  images/              images clés individuelles
  planches/planche_XX.jpg  planches de 6 images avec horodatage
  transcription.md     transcription horodatée
  resume_technique.md  récapitulatif des fichiers produits

Usage :
  python3 analyse_video.py <lien_ou_fichier> [--out DOSSIER]
        [--max-images 36] [--modele small] [--langue fr] [--sans-transcription]
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path


def log(msg):
    print(f"[analyse-video] {msg}", flush=True)


def ensure_python_pkg(module, pip_name):
    try:
        __import__(module)
    except ImportError:
        log(f"Installation de {pip_name}…")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", pip_name],
                       check=True)


def is_url(s):
    return s.startswith("http://") or s.startswith("https://")


def fmt_ts(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def download(url, out_dir):
    ensure_python_pkg("yt_dlp", "yt-dlp")
    log(f"Téléchargement : {url}")
    template = str(out_dir / "video.%(ext)s")
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "bv*[height<=720]+ba/b[height<=720]/bv*+ba/b",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--write-info-json",
        "-o", template,
        url,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stdout[-2000:] + "\n" + res.stderr[-3000:] + "\n")
        log("ÉCHEC du téléchargement. Causes fréquentes : site bloqué par le "
            "réseau (session cloud), vidéo privée ou nécessitant une connexion. "
            "Solution : télécharger la vidéo soi-même et fournir le fichier.")
        sys.exit(2)
    videos = [p for p in out_dir.glob("video.*")
              if p.suffix not in (".json", ".part", ".ytdl")]
    if not videos:
        log("ÉCHEC : aucun fichier vidéo trouvé après le téléchargement.")
        sys.exit(2)
    info_files = list(out_dir.glob("video*.info.json"))
    if info_files:
        raw = json.loads(info_files[0].read_text())
        keep = {k: raw.get(k) for k in (
            "title", "uploader", "channel", "upload_date", "duration",
            "description", "webpage_url", "view_count", "like_count")}
        (out_dir / "infos.json").write_text(
            json.dumps(keep, ensure_ascii=False, indent=2))
        info_files[0].unlink()
    return videos[0]


def probe_duration(video):
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(video)],
        capture_output=True, text=True)
    try:
        return float(res.stdout.strip())
    except ValueError:
        return 0.0


def has_audio(video):
    res = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(video)],
        capture_output=True, text=True)
    return bool(res.stdout.strip())


def extract_frames(video, duration, out_dir, max_images):
    img_dir = out_dir / "images"
    if img_dir.exists():
        shutil.rmtree(img_dir)
    img_dir.mkdir(parents=True)
    if duration <= 0:
        duration = 60.0
    n = max(1, min(max_images, int(math.ceil(duration / 2))))
    interval = duration / n
    log(f"Extraction de {n} images (une toutes les {interval:.1f} s)…")
    frames = []
    for i in range(n):
        t = min(duration - 0.05, i * interval + interval / 2)
        path = img_dir / f"img_{i + 1:03d}.jpg"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video),
             "-frames:v", "1", "-vf", "scale=640:-2", "-q:v", "4",
             "-y", str(path)],
            check=False)
        if path.exists():
            frames.append((t, path))
    return frames


def build_sheets(frames, out_dir, per_sheet=6, cols=3):
    from PIL import Image, ImageDraw, ImageFont

    sheet_dir = out_dir / "planches"
    if sheet_dir.exists():
        shutil.rmtree(sheet_dir)
    sheet_dir.mkdir(parents=True)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    sheets = []
    for s in range(0, len(frames), per_sheet):
        chunk = frames[s:s + per_sheet]
        imgs = [Image.open(p).convert("RGB") for _, p in chunk]
        w = max(i.width for i in imgs)
        h = max(i.height for i in imgs)
        rows = math.ceil(len(imgs) / cols)
        sheet = Image.new("RGB", (cols * w, rows * h), "black")
        draw = ImageDraw.Draw(sheet)
        for k, (img, (t, _)) in enumerate(zip(imgs, chunk)):
            x, y = (k % cols) * w, (k // cols) * h
            sheet.paste(img, (x, y))
            label = f"#{s + k + 1}  {fmt_ts(t)}"
            draw.rectangle([x, y, x + 150, y + 32], fill="black")
            draw.text((x + 6, y + 4), label, fill="yellow", font=font)
        path = sheet_dir / f"planche_{len(sheets) + 1:02d}.jpg"
        sheet.save(path, quality=80)
        sheets.append((chunk[0][0], chunk[-1][0], path))
    return sheets


def transcribe(video, out_dir, model_name, language):
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    ensure_python_pkg("faster_whisper", "faster-whisper")
    from faster_whisper import WhisperModel

    log(f"Transcription (modèle {model_name})… cela peut prendre quelques minutes.")
    import numpy as np

    # Décodage audio par ffmpeg (16 kHz mono) : évite les incompatibilités
    # entre versions de PyAV et faster-whisper.
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(video), "-vn", "-ac", "1",
         "-ar", "16000", "-f", "s16le", "-"],
        capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        audio, language=language, vad_filter=True, beam_size=5)
    lines = [f"# Transcription\n\nLangue détectée : {info.language} "
             f"(confiance {info.language_probability:.0%})\n"]
    count = 0
    for seg in segments:
        lines.append(f"[{fmt_ts(seg.start)} → {fmt_ts(seg.end)}] {seg.text.strip()}")
        count += 1
    if count == 0:
        lines.append("_(Aucune parole détectée.)_")
    path = out_dir / "transcription.md"
    path.write_text("\n".join(lines) + "\n")
    return path, count, info.language


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="Lien de la vidéo ou chemin du fichier")
    ap.add_argument("--out", default="analyse-video-sortie",
                    help="Dossier de sortie")
    ap.add_argument("--max-images", type=int, default=36)
    ap.add_argument("--modele", default="small",
                    help="Modèle Whisper : tiny, base, small, medium")
    ap.add_argument("--langue", default=None,
                    help="Code de langue (fr, en…). Par défaut : détection auto")
    ap.add_argument("--sans-transcription", action="store_true")
    args = ap.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        log("ffmpeg est requis (Mac : brew install ffmpeg ; "
            "Windows : winget install ffmpeg).")
        sys.exit(1)
    ensure_python_pkg("PIL", "pillow")

    out_dir = Path(args.out).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if is_url(args.source):
        video = download(args.source, out_dir)
    else:
        video = Path(args.source).expanduser().resolve()
        if not video.exists():
            log(f"Fichier introuvable : {video}")
            sys.exit(1)

    duration = probe_duration(video)
    log(f"Vidéo : {video.name} — durée {fmt_ts(duration)}")

    frames = extract_frames(video, duration, out_dir, args.max_images)
    sheets = build_sheets(frames, out_dir)

    transcript = None
    if args.sans_transcription:
        log("Transcription ignorée (--sans-transcription).")
    elif not has_audio(video):
        log("La vidéo n'a pas de piste audio : pas de transcription.")
    else:
        transcript, nseg, lang = transcribe(video, out_dir, args.modele, args.langue)
        log(f"Transcription : {nseg} segments, langue {lang}.")

    summary = [
        "# Analyse vidéo — fichiers produits\n",
        f"- Source : {args.source}",
        f"- Vidéo : {video}",
        f"- Durée : {fmt_ts(duration)}",
    ]
    if (out_dir / "infos.json").exists():
        summary.append(f"- Infos (titre, description…) : {out_dir / 'infos.json'}")
    summary.append(f"- Transcription : {transcript or 'aucune'}")
    summary.append(f"- {len(frames)} images clés, {len(sheets)} planches :")
    for a, b, p in sheets:
        summary.append(f"  - {p}  ({fmt_ts(a)} → {fmt_ts(b)})")
    (out_dir / "resume_technique.md").write_text("\n".join(summary) + "\n")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
