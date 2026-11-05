import math
import shutil
import struct
import sys
import wave
from datetime import datetime
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import (metadata,valid_beatstars_url,trim_tags,probe_duration,render,DEFAULT_ART_PATH,
                  create_default_art,london_publish_time,UploadJournal,video_filename)


def test_metadata_personal_and_exact_link():
    d=metadata('Fimiguerrero','Lancey Foux','He4rtB3at',144,'F# Minor',
               {'free':True,'instagram':'@listentoaarxn','genre':''},
               'https://www.beatstars.com/beat/he4rtb3at-123456')
    assert d['title']=='[FREE] Fimiguerrero x Lancey Foux Type Beat - "He4rtB3at"'
    assert 'KEY: F# Minor' in d['description']
    assert 'https://www.beatstars.com/beat/he4rtb3at-123456' in d['description']
    assert 'Lancey Foux' in d['description']
    assert len(d['title'])<=100
    assert len(d['description'].encode('utf-8'))<=5000
    assert all('Taylor Swift' not in tag for tag in d['tags'])


def test_invalid_link_not_accepted():
    assert not valid_beatstars_url('https://www.beatstars.com/listentoaarxn')
    assert not valid_beatstars_url('https://evil.com/beat/my-beat')
    assert valid_beatstars_url('https://www.beatstars.com/beat/a-song-123')
    d=metadata('Che','Ken Carson','Test',150,'D Minor')
    assert 'BUY / LICENSE THIS BEAT:' not in d['description']


def test_tag_limit():
    tags=trim_tags([f'tag {n} lorem ipsum underground' for n in range(200)])
    assert len(','.join('"'+v+'"' if ' ' in v else v for v in tags))<=500


def test_schedule_and_dst():
    s=london_publish_time(datetime(2030,6,1,18,0))
    assert s=='2030-06-01T17:00:00Z'
    with pytest.raises(ValueError):london_publish_time(datetime(2030,3,31,1,30))


def test_journal(tmp_path):
    path=tmp_path/'audio.wav'; path.write_bytes(b'abcd')
    ledger=UploadJournal(tmp_path/'state.sqlite3')
    token=ledger.fingerprint(path,'channel-1','Beat','private')
    assert ledger.get(token) is None
    ledger.set(token,'uploading');assert ledger.get(token)==('uploading',None)
    ledger.set(token,'complete','abcd');assert ledger.get(token)==('complete','abcd')


@pytest.mark.skipif(not (shutil.which('ffmpeg') and shutil.which('ffprobe')),reason='FFmpeg not installed')
def test_real_ffmpeg_render(tmp_path):
    audio=tmp_path/'tone.wav'
    with wave.open(str(audio),'w') as f:
        f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000)
        samples=[int(3000*math.sin(2*math.pi*440*i/16000)) for i in range(16000)]
        f.writeframes(struct.pack('<'+str(len(samples))+'h',*samples))
    img=tmp_path/'art.jpg';create_default_art(img)
    out=tmp_path/video_filename('My Beat',audio)
    progress=[]
    render(audio,img,out,'1280x720',lambda pct:progress.append(pct))
    assert out.exists() and out.stat().st_size>5000
    assert 0.5<probe_duration(out)<1.5
    assert progress[-1]==100
