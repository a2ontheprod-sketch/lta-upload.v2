"""LTA // UPLOAD local audio, artwork, metadata, configuration and rendering core.
No external accounts are accessed by this module.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageOps, ImageDraw, ImageFont

APP_NAME = 'LTA // UPLOAD'
APP_DIR = Path(os.environ.get('APPDATA') or Path.home() / '.config') / 'LTA_UPLOAD'
APP_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = APP_DIR / 'settings.json'
JOURNAL_PATH = APP_DIR / 'uploads.sqlite3'
ARTISTS_PATH = APP_DIR / 'artists.json'
DEFAULT_ART_PATH = APP_DIR / 'default_artwork.jpg'
PINK = '#F8BBD0'

DEFAULTS = {
    'instagram': '@listentoaarxn', 'email': '', 'output_dir': str(Path.home() / 'Videos' / 'LTA Upload'),
    'artwork': str(DEFAULT_ART_PATH), 'pexels_key_saved': False,
    'oauth_client_path': '', 'artist1': 'Fimiguerrero', 'artist2': 'Lancey Foux',
    'genre': '', 'mood': '', 'free': True, 'res': '1920x1080',
    'visibility': 'Private', 'beatstars_licence_note': '', 'title_template': '{artist1} x {artist2} Type Beat - "{name}"',
}
ARTISTS = {
 'fimiguerrero': {'genre': 'UK underground rap', 'related': ['UK alternative rap']},
 'lancey foux': {'genre': 'UK alternative rap', 'related': ['UK underground rap']},
 'ken carson': {'genre': 'rage', 'related': ['alternative trap']},
 'destroy lonely': {'genre': 'alternative trap', 'related': ['rage']},
 'osamason': {'genre': 'rage', 'related': ['underground rap']},
 'che': {'genre': 'underground rap', 'related': ['rage']},
 'fakemink': {'genre': 'UK underground rap', 'related': []},
 'esdeekid': {'genre': 'UK underground rap', 'related': []},
 'rico ace': {'genre': 'UK underground rap', 'related': []},
 'nettspend': {'genre': 'underground rap', 'related': []},
 'jim legxacy': {'genre': 'UK alternative rap', 'related': []},
}


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    os.replace(temporary, path)


def settings():
    data = DEFAULTS.copy()
    if CONFIG_PATH.exists():
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
            data.update({k:v for k,v in raw.items() if k in DEFAULTS})
        except (OSError, ValueError):
            pass
    if not ARTISTS_PATH.exists():
        save_json(ARTISTS_PATH, ARTISTS)
    if not DEFAULT_ART_PATH.exists():
        create_default_art(DEFAULT_ART_PATH)
    return data


def save_settings(data):
    save_json(CONFIG_PATH, {k: data[k] for k in DEFAULTS if k in data})


def artist_database():
    try:
        return json.loads(ARTISTS_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return ARTISTS


def create_default_art(path):
    im = Image.new('RGB', (1920,1080))
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            t = (0.55 * x / im.width + 0.45 * y / im.height)
            px[x,y] = (int(255-24*t),int(242-50*t),int(248-25*t))
    d = ImageDraw.Draw(im, 'RGBA')
    for cx,cy,r in [(340,250,370),(1550,800,440),(1240,170,150)]:
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(245,155,189,32),width=0)
    im.save(path, 'JPEG', quality=92)


def safe_stem(text):
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', '', text).strip(' .')
    return (text[:90] or 'Untitled Beat')


def safe_metadata(text, max_len):
    # YouTube rejects angle brackets; description limit is BYTES, not characters.
    t = text.replace('<','(').replace('>',')')
    return t.encode('utf-8')[:max_len].decode('utf-8', errors='ignore')


def hashtags(text):
    return re.sub('[^a-z0-9]', '', text.lower())


def dedupe(values):
    output = []
    seen = set()
    for v in values:
        v = str(v).strip()
        if v and v.casefold() not in seen:
            output.append(v)
            seen.add(v.casefold())
    return output


def trim_tags(tags):
    """YouTube 500-char combined limit incl commas and wrapping quotes for spaced tags."""
    out = []
    budget = 0
    for t in dedupe(tags):
        t = t.replace('<','').replace('>','').replace('"','')
        weight = len(t) + (2 if ' ' in t else 0) + (1 if out else 0)
        if budget + weight <= 500:
            out.append(t)
            budget += weight
    return out


def metadata(artist1, artist2, name, bpm, key, options=None, beatstars_url='', art_credit=''):
    cfg = {**DEFAULTS, **(options or {})}
    a1, a2, name = artist1.strip(), artist2.strip(), name.strip()
    if not all((a1,a2,name)):
        raise ValueError('Enter both artists and a beat name.')
    template = cfg.get('title_template') or DEFAULTS['title_template']
    try:
        title = template.format(artist1=a1, artist2=a2, name=name)
    except (KeyError, ValueError, IndexError) as exc:
        raise ValueError('Invalid title template. Use {artist1}, {artist2}, {name}.') from exc
    title = ('[FREE] ' if cfg.get('free') else '') + title
    title = safe_metadata(title, 100)
    db = artist_database()
    one = db.get(a1.casefold(), {})
    two = db.get(a2.casefold(), {})
    genre = (cfg.get('genre') or one.get('genre') or two.get('genre') or '').strip()
    mood = (cfg.get('mood') or '').strip()
    terms = dedupe([f'{a1} x {a2} type beat', f'{a1} type beat', f'{a2} type beat',
        f'{a2} x {a1} type beat', f'{a1} {a2} instrumental',
        f'{genre} type beat' if genre else '', f'{mood} type beat' if mood else '',
        *(one.get('related') or []), *(two.get('related') or [])])
    tags = trim_tags(terms)
    hashwords = [hashtags(a1), hashtags(a2), hashtags(genre)]
    hashtext = ' '.join('#'+v for v in dedupe(['typebeat',*hashwords]) if v)
    desc = []
    if beatstars_url.strip():
        if not valid_beatstars_url(beatstars_url):
            raise ValueError('Enter the DIRECT URL to the individual BeatStars track, not your homepage.')
        desc.extend(['BUY / LICENSE THIS BEAT:',beatstars_url.strip(),''])
    desc.extend([f'KEY: {key.strip() or "Not set"}',f'BPM: {bpm or "Not set"}','', 'CONTACT:',
        f'Instagram: {cfg.get("instagram") or "@listentoaarxn"}'])
    if cfg.get('email'):
        desc.append('Email: '+cfg['email'].strip())
    desc.extend(['', f'{a1} x {a2} type beat'+(f' in the {genre} style' if genre else '')+
                 (f' with a {mood.lower()} mood' if mood else '')+'.',
                 '', ' | '.join(terms[:7]),'',hashtext])
    if art_credit.strip():
        desc.extend(['','Artwork: '+art_credit.strip()])
    return {'title': title,'description':safe_metadata('\n'.join(desc), 5000),'tags':tags,'genre':genre}


def valid_beatstars_url(url):
    from urllib.parse import urlparse
    try:
        p = urlparse(url.strip())
        return p.scheme == 'https' and (p.hostname == 'beatstars.com' or p.hostname.endswith('.beatstars.com')) and len(p.path.strip('/').split('/')) >= 2 and p.path.strip('/').split('/')[0] in ('beat','track','beats')
    except (ValueError, AttributeError):
        return False


def probe_duration(audio):
    exe = shutil.which('ffprobe')
    if not exe:
        raise RuntimeError('FFmpeg/ffprobe missing. Install FFmpeg and add its bin folder to Windows PATH.')
    cmd = [exe,'-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(audio)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if p.returncode:
        raise ValueError('Could not open audio: '+p.stderr[-350:])
    dur = float(p.stdout.strip())
    if dur <= 0:
        raise ValueError('Audio duration is invalid.')
    return dur


def analyze_audio(audio):
    """Heuristic key and tempo guesses only. Manual correction is always possible."""
    import numpy as np
    import librosa
    sr = 11025
    y, _ = librosa.load(str(audio), sr=sr, mono=True, duration=100)
    if len(y) < sr:
        raise ValueError('Audio too short to analyse.')
    # Prefer percussive onset tempo; half/double-time is inherently ambiguous.
    onset=librosa.onset.onset_strength(y=y,sr=sr,hop_length=256)
    candidates=librosa.feature.tempo(onset_envelope=onset,sr=sr,hop_length=256,aggregate=None)
    candidate=float(np.median(candidates)) if len(candidates) else 0.0
    bpm=round(candidate) if np.isfinite(candidate) and candidate>0 else 0
    # Krumhansl-Schmuckler key profiles on overall chroma (imperfect for beats).
    harmonic=librosa.effects.harmonic(y[:sr*60],margin=3.0)
    chroma = librosa.feature.chroma_stft(y=harmonic,sr=sr,hop_length=1024).mean(axis=1)
    major = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
    minor = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
    choices = []
    for mode, profile in [('Major',major),('Minor',minor)]:
        for offset in range(12):
            corr = np.corrcoef(chroma, np.roll(profile,offset))[0,1]
            choices.append((corr,offset,mode))
    _, idx, mode = max(choices)
    notes = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
    n=192
    edges=np.linspace(0,len(y),n+1,dtype=int)
    amplitudes=[float(np.sqrt(np.mean(np.square(y[edges[i]:edges[i+1]])))) if edges[i+1]>edges[i] else 0 for i in range(n)]
    highest=max(amplitudes) or 1
    waveform=[min(1.0, val/highest) for val in amplitudes]
    return {'bpm':bpm,'key':f'{notes[idx]} {mode}','duration':probe_duration(audio),'waveform':waveform,
            'tempo_alternatives':[round(bpm/2),bpm,round(bpm*2)] if bpm else []}


def prepare_image(source, destination, width=1920, height=1080, quality=94):
    with Image.open(source) as original:
        img = ImageOps.exif_transpose(original).convert('RGB')
        # Preserve the entire artwork and letterbox with black instead of cropping.
        img.thumbnail((width,height),Image.Resampling.LANCZOS)
        canvas=Image.new('RGB',(width,height),(0,0,0))
        canvas.paste(img,((width-img.width)//2,(height-img.height)//2))
        img=canvas
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        img.save(destination,'JPEG',quality=quality,subsampling=0,optimize=True)
    return str(destination)


def render(audio, artwork, output_path, resolution='1920x1080', progress=None):
    exe = shutil.which('ffmpeg')
    if not exe:
        raise RuntimeError('FFmpeg not found on PATH. See README for installation.')
    if resolution not in ('1920x1080','1280x720','2560x1440'):
        raise ValueError('Unsupported resolution.')
    width, height = map(int,resolution.split('x'))
    duration = probe_duration(audio)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True,exist_ok=True)
    # Only rename a completed temporary file into final destination on success.
    temp_out = output_path.with_name(output_path.stem+'.partial.mp4')
    with tempfile.TemporaryDirectory(prefix='lta_render_') as d:
        jpg = str(Path(d)/'cover.jpg')
        prepare_image(artwork,jpg,width,height)
        args = [exe,'-hide_banner','-loglevel','error','-y',
            '-loop','1','-framerate','1','-i',jpg,'-i',str(audio),
            '-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','veryfast',
            '-tune','stillimage','-r','24','-pix_fmt','yuv420p',
            '-c:a','aac','-b:a','320k','-shortest','-movflags','+faststart',
            '-progress','pipe:1','-nostats',str(temp_out)]
        startup = {'creationflags': subprocess.CREATE_NO_WINDOW} if sys.platform == 'win32' else {}
        proc = subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                text=True,bufsize=1,**startup)
        try:
            for line in proc.stdout:
                if line.startswith('out_time_us=') or line.startswith('out_time_ms='):
                    try:
                        fraction = min(0.99,float(line.split('=',1)[1].strip())/1_000_000/duration)
                        if progress: progress(int(fraction*100))
                    except ValueError: pass
            err = proc.stderr.read()
            if proc.wait() != 0:
                raise RuntimeError('FFmpeg rendering failed: '+err[-900:])
            if not temp_out.exists() or temp_out.stat().st_size == 0:
                raise RuntimeError('FFmpeg produced an empty file.')
            os.replace(temp_out, output_path)
            if progress: progress(100)
        finally:
            if proc.poll() is None: proc.kill()
            if temp_out.exists(): temp_out.unlink()
    return str(output_path)


def video_filename(beat_name, audio_path, artwork=None, resolution='1920x1080'):
    # Invalidate a cached rendering whenever audio, artwork, or resolution changes.
    h=hashlib.sha256()
    for path in [audio_path, artwork]:
        if path:
            p=Path(path)
            st=p.stat()
            h.update(str(p.resolve()).encode('utf-8'))
            h.update(f':{st.st_size}:{st.st_mtime_ns}'.encode('ascii'))
    h.update(str(resolution).encode('ascii'))
    return safe_stem(beat_name) + '_' + h.hexdigest()[:10] + '.mp4'


def london_publish_time(naive_dt):
    tz = ZoneInfo('Europe/London')
    if naive_dt.tzinfo is not None:
        raise ValueError('Pass a local London wall-clock date/time.')
    aware = naive_dt.replace(tzinfo=tz)
    if aware.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) != naive_dt:
        raise ValueError('That time does not exist in the London timezone because of daylight saving.')
    if aware <= datetime.now(tz):
        raise ValueError('Schedule must be in the future (Europe/London).')
    return aware.astimezone(timezone.utc).isoformat().replace('+00:00','Z')


class UploadJournal:
    def __init__(self, db=JOURNAL_PATH):
        self.db = str(db)
        with sqlite3.connect(self.db) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS uploads (fingerprint TEXT PRIMARY KEY, state TEXT NOT NULL, video_id TEXT, updated_at TEXT NOT NULL)')

    def fingerprint(self, audio, channel_id, title, schedule):
        h = hashlib.sha256()
        with open(audio,'rb') as f:
            while block := f.read(4*1024*1024): h.update(block)
        for item in (channel_id,title,str(schedule)):
            h.update(b'\x00'+item.encode('utf-8'))
        return h.hexdigest()

    def get(self, fingerprint):
        with sqlite3.connect(self.db) as conn:
            row = conn.execute('SELECT state,video_id FROM uploads WHERE fingerprint=?',(fingerprint,)).fetchone()
        return row

    def set(self,fingerprint,state,video_id=None):
        with sqlite3.connect(self.db) as conn:
            conn.execute('INSERT INTO uploads(fingerprint,state,video_id,updated_at) VALUES (?,?,?,?) ON CONFLICT(fingerprint) DO UPDATE SET state=excluded.state,video_id=excluded.video_id,updated_at=excluded.updated_at',
                (fingerprint,state,video_id,datetime.now(timezone.utc).isoformat()))
