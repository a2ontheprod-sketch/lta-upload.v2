"""LTA // UPLOAD — PySide6 desktop interface."""
from __future__ import annotations
import json
import os
import shutil
import sys
import traceback
import webbrowser
from dataclasses import dataclass, field
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

# Portable GitHub build: find the bundled FFmpeg tools beside the Windows .exe.
# This has no effect on the normal Python/source installation or the UI.
if getattr(sys, 'frozen', False):
    binary_folder = str(Path(sys.executable).resolve().parent)
    os.environ['PATH'] = binary_folder + os.pathsep + os.environ.get('PATH', '')

from PySide6.QtCore import Qt, QThread, Signal, QUrl, QDateTime, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QPixmap, QIcon, QPainter, QPen, QColor
from PySide6.QtWidgets import (QApplication,QWidget,QDialog,QFrame,QLabel,QPushButton,QLineEdit,
    QTextEdit,QVBoxLayout,QHBoxLayout,QGridLayout,QScrollArea,QFileDialog,QComboBox,QCheckBox,
    QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,QProgressBar,QDateTimeEdit,QSplitter,
    QSizePolicy,QInputDialog,QStackedWidget,QCalendarWidget,QGraphicsOpacityEffect)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QSoundEffect

from core import (settings,save_settings,APP_DIR,ARTISTS_PATH,metadata,probe_duration,analyze_audio,
                  prepare_image,render,video_filename,valid_beatstars_url,UploadJournal,
                  london_publish_time,DEFAULT_ART_PATH)
import youtube_api

PINK='#F8BBD0'
LIGHT='#FFE4EE'
INK='#242124'
GREY='#766F75'

STYLE='''
QWidget { background: #FFFFFF; color: #242124; font-family: 'Segoe UI'; font-size: 12px; }
QFrame#Panel {background:#FFF9FC;border:1px solid #F7E2EB;border-radius:18px;}
QFrame#Drop {background:#FFF8FB;border:2px dashed #EFB3CC;border-radius:14px;}
QLabel#Heading {font-size:21px;font-weight:750;}
QLabel#Section {font-size:13px;font-weight:700;color:#242124;}
QLabel#Muted {font-size:11px;color:#81737B;}
QLabel#Selected {background:#FFE4EE;border-radius:10px;padding:10px;font-size:14px;font-weight:700;}
QLabel#Step {color:#C06C91;font-size:12px;font-weight:700;}
QLineEdit, QTextEdit, QComboBox, QDateTimeEdit, QTableWidget {border:1px solid #EFDDE6;border-radius:9px;padding:8px;background:#FFFFFF;selection-background-color:#F8BBD0;}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {border:1px solid #EC96B6;}
QPushButton {border:1px solid #F0D7E2;border-radius:10px;background:#FFF4F8;padding:9px 14px;font-weight:600;}
QPushButton:hover {background:#FFE4EE;border-color:#EFA8C6;}
QPushButton#Primary {background:#F8BBD0;border:0;color:#38212B;font-size:15px;padding:14px 22px;}
QPushButton#Primary:hover {background:#F4A4C1;}
QPushButton:disabled {background:#F5F2F4;color:#AEA9AC;}
QScrollArea {border:none;background:transparent;}
QProgressBar {border:0;border-radius:6px;background:#F7E6EE;height:12px;text-align:center;color:transparent;}
QProgressBar::chunk {border-radius:6px;background:#F8BBD0;}
QCheckBox::indicator {width:17px;height:17px;}
QTableWidget {gridline-color:#F1E8ED;}
QHeaderView::section {background:#FFF3F8;border:none;padding:7px;font-weight:600;}
'''


def txt(label, kind='Muted'):
    l=QLabel(label)
    l.setObjectName(kind)
    l.setWordWrap(True)
    return l


def action(text, handler=None, primary=False):
    b=QPushButton(text)
    if primary: b.setObjectName('Primary')
    if handler: b.clicked.connect(handler)
    return b


def show_error(parent,heading,exception):
    QMessageBox.critical(parent,heading,str(exception))


def notify(parent,title,body):
    QMessageBox.information(parent,title,body)


class DropZone(QFrame):
    filesDropped=Signal(list)
    def __init__(self):
        super().__init__()
        self.setObjectName('Drop')
        self.setAcceptDrops(True)
        self.setMinimumHeight(92)
        lay=QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label=txt('Drop MP3 / WAV here  ·  or click to browse','Section')
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.label)
        lay.addWidget(txt('Multiple files supported'))
    def mousePressEvent(self,event):
        paths,_=QFileDialog.getOpenFileNames(self,'Choose your beats','','Audio (*.mp3 *.wav)')
        if paths: self.filesDropped.emit(paths)
    def dragEnterEvent(self,event):
        if any(u.isLocalFile() and Path(u.toLocalFile()).suffix.lower() in ('.wav','.mp3') for u in event.mimeData().urls()):
            event.acceptProposedAction()
    def dropEvent(self,event):
        paths=[u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile() and Path(u.toLocalFile()).suffix.lower() in ('.wav','.mp3')]
        if paths: self.filesDropped.emit(paths)


@dataclass
class Beat:
    path:str
    name:str
    bpm:str=''
    key:str=''
    duration:float=0
    beatstars_url:str=''
    output:str=''
    meta_override:str=''
    desc_override:str=''
    tags_override:str=''
    waveform:list=field(default_factory=list)


class SettingsDialog(QDialog):
    def __init__(self,cfg,parent=None):
        super().__init__(parent)
        self.setWindowTitle('LTA // SETTINGS')
        self.setMinimumWidth(540)
        self.cfg=cfg.copy()
        lay=QVBoxLayout(self)
        lay.setSpacing(12)
        lay.addWidget(txt('Settings','Heading'))
        self.insta=QLineEdit(cfg.get('instagram',''))
        self.email=QLineEdit(cfg.get('email',''))
        self.output=QLineEdit(cfg.get('output_dir',''))
        self.art=QLineEdit(cfg.get('artwork',''))
        self.json=QLineEdit(cfg.get('oauth_client_path',''))
        self.title=QLineEdit(cfg.get('title_template',''))
        self.licence=QLineEdit(cfg.get('beatstars_licence_note',''))
        self.licence.setPlaceholderText('Optional BeatStars licence preset / notes for manual upload')
        self.pexels=QLineEdit(); self.pexels.setEchoMode(QLineEdit.EchoMode.Password)
        self.pexels.setPlaceholderText('Paste Pexels API key to save/update (stored in Windows Credential Manager)')
        for name, field, pick in [
            ('Instagram',self.insta,None),('Contact email',self.email,None),
            ('Video output folder',self.output,'folder'),('Default artwork',self.art,'image'),
            ('Google OAuth desktop JSON',self.json,'json'),('YouTube title template',self.title,None),
            ('BeatStars licence note',self.licence,None),('Pexels API key',self.pexels,None)]:
            lay.addWidget(txt(name,'Section'))
            row=QHBoxLayout(); row.addWidget(field)
            if pick:
                def choose(_=False,f=field,p=pick):
                    if p=='folder': value=QFileDialog.getExistingDirectory(self,'Output folder',f.text())
                    else: value=QFileDialog.getOpenFileName(self,'Select file','',
                        'Images (*.jpg *.jpeg *.png *.webp)' if p=='image' else 'JSON (*.json)')[0]
                    if value: f.setText(value)
                row.addWidget(action('Browse',choose))
            lay.addLayout(row)
        lay.addWidget(txt('Artist keyword database is editable: '+str(ARTISTS_PATH)))
        buttons=QHBoxLayout(); buttons.addStretch()
        buttons.addWidget(action('Cancel',self.reject)); buttons.addWidget(action('Save',self.accept,True))
        lay.addLayout(buttons)
    def apply(self):
        self.cfg.update({'instagram':self.insta.text().strip(),'email':self.email.text().strip(),
            'output_dir':self.output.text().strip(),'artwork':self.art.text().strip(),
            'oauth_client_path':self.json.text().strip(),'title_template':self.title.text().strip(),
            'beatstars_licence_note':self.licence.text().strip()})
        if self.pexels.text().strip():
            import keyring
            keyring.set_password('LTA_UPLOAD_PEXELS','api_key',self.pexels.text().strip())
        return self.cfg


class PictureSearchDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setWindowTitle('Find licensed artwork on Pexels')
        self.resize(760,580)
        self.selected_path=''
        self.credit=''
        self.results=[]
        lay=QVBoxLayout(self)
        bar=QHBoxLayout()
        self.query=QLineEdit('dreamy futuristic city')
        self.query.setPlaceholderText('Try dark underground, nostalgic, abstract...')
        bar.addWidget(self.query)
        bar.addWidget(action('Search',self.search,True))
        lay.addLayout(bar)
        lay.addWidget(txt('Images provided by Pexels. Photographer credits are added to the description.'))
        self.scroll=QScrollArea(); self.scroll.setWidgetResizable(True)
        self.wrapper=QWidget()
        self.grid=QGridLayout(self.wrapper); self.grid.setSpacing(10)
        self.scroll.setWidget(self.wrapper)
        lay.addWidget(self.scroll)
        lay.addWidget(action('Open Pexels website',lambda: webbrowser.open('https://www.pexels.com/')))
    def search(self):
        try:
            import keyring,requests
            from concurrent.futures import ThreadPoolExecutor
            key=keyring.get_password('LTA_UPLOAD_PEXELS','api_key')
            if not key:
                raise ValueError('Add your free Pexels API key in Settings first.')
            r=requests.get('https://api.pexels.com/v1/search',
                headers={'Authorization':key},params={'query':self.query.text(),'per_page':12,'orientation':'landscape'},timeout=18)
            r.raise_for_status()
            self.results=r.json().get('photos',[])
            while self.grid.count():
                item=self.grid.takeAt(0)
                if item.widget():item.widget().deleteLater()
            def fetch_photo(item):
                try:
                    pic=requests.get(item['src']['medium'],timeout=12)
                    pic.raise_for_status()
                    return pic.content
                except requests.RequestException:
                    return b''
            with ThreadPoolExecutor(max_workers=8) as pool:
                picture_data=list(pool.map(fetch_photo,self.results))
            for i,(item,bytes_img) in enumerate(zip(self.results,picture_data)):
                img=QPixmap(); img.loadFromData(bytes_img)
                b=QPushButton(); b.setIcon(QIcon(img.scaled(190,115,Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation))); b.setIconSize(QSize(190,115)); b.setFixedSize(210,142)
                b.setToolTip('Photo by '+item.get('photographer','Unknown'))
                b.clicked.connect(lambda _=False,p=item:self.choose(p))
                self.grid.addWidget(b,i//3,i%3)
            if not self.results: notify(self,'No results','Try another search term.')
        except Exception as exc: show_error(self,'Artwork search failed',exc)
    def choose(self,photo):
        try:
            import requests
            r=requests.get(photo['src'].get('original') or photo['src']['large2x'],timeout=35)
            r.raise_for_status()
            ext='.jpg'
            folder=APP_DIR/'artwork'; folder.mkdir(exist_ok=True)
            dest=folder / f'pexels_{photo["id"]}{ext}'
            dest.write_bytes(r.content)
            # Verify image is an actual supported image file.
            from PIL import Image
            with Image.open(dest) as im: im.verify()
            self.selected_path=str(dest)
            self.credit=f'Photo by {photo.get("photographer","Pexels contributor")} on Pexels ({photo.get("url", "https://www.pexels.com/")})'
            self.accept()
        except Exception as exc:show_error(self,'Could not download photo',exc)


class AuthWorker(QThread):
    connected=Signal(dict)
    error=Signal(str)
    def __init__(self,path):
        super().__init__();self.path=path
    def run(self):
        try:self.connected.emit(youtube_api.connect(self.path))
        except Exception as e:self.error.emit(str(e))


class AnalyseWorker(QThread):
    result=Signal(str,dict)
    failed=Signal(str,str)
    def __init__(self,paths):
        super().__init__();self.paths=paths
    def run(self):
        for p in self.paths:
            try:self.result.emit(p,analyze_audio(p))
            except Exception as e:self.failed.emit(p,str(e))


class UploadWorker(QThread):
    progress=Signal(int)
    log=Signal(str)
    finished_all=Signal()
    failed=Signal(str)
    def __init__(self,beats,opts):
        super().__init__();self.beats=beats;self.opts=opts
    def run(self):
        try:
            cfg=self.opts['cfg']
            target=Path(cfg['output_dir']);target.mkdir(parents=True,exist_ok=True)
            journal=UploadJournal()
            for i,beat in enumerate(self.beats):
                self.log.emit(f'[{i+1}/{len(self.beats)}] {beat.name}')
                image=self.opts['image']
                if not Path(image).is_file():
                    raise ValueError('Selected artwork no longer exists: '+image)
                current=target / video_filename(beat.name,beat.path,image,cfg['res'])
                if not current.exists():
                    self.log.emit('Rendering static-image MP4…')
                    render(beat.path,image,current,cfg['res'],lambda pct,idx=i:self.progress.emit(int((idx+0.65*pct/100)/len(self.beats)*100)))
                else:
                    self.log.emit('Using existing rendered MP4: '+current.name)
                beat.output=str(current)
                self.progress.emit(int(((i+.65)/len(self.beats))*100))
                info=metadata(self.opts['a1'],self.opts['a2'],beat.name,beat.bpm,beat.key,
                    cfg,beat.beatstars_url,self.opts['credit'])
                title=beat.meta_override or info['title']
                desc=beat.desc_override or info['description']
                tags=([v.strip() for v in beat.tags_override.split(',') if v.strip()]
                      if beat.tags_override else info['tags'])
                if self.opts['beatstars'] and not beat.beatstars_url:
                    self.log.emit('Local video ready: '+str(current))
                    self.log.emit('BeatStars: assisted upload needed. Open Studio and publish this beat; paste its direct URL before YouTube upload.')
                    if self.opts['youtube']:
                        self.log.emit('YouTube upload skipped to avoid a missing BeatStars license link.')
                        self.progress.emit(int((i+1)/len(self.beats)*100))
                        continue
                if self.opts['youtube']:
                    if not self.opts['channel']:
                        raise RuntimeError('Connect your YouTube channel first.')
                    if not beat.beatstars_url and 'BUY / LICENSE THIS BEAT:' in desc:
                        raise ValueError('Description contains a BeatStars placeholder without a direct track link.')
                    publish_at=self.opts['publish_at']
                    fp=journal.fingerprint(beat.path,self.opts['channel']['id'],title,publish_at or self.opts['visibility'])
                    prior=journal.get(fp)
                    if prior and prior[0]=='complete':
                        self.log.emit('Already uploaded, skipping duplicate: https://www.youtube.com/watch?v='+prior[1])
                        continue
                    if prior and prior[0] in ('uploading','ambiguous'):
                        self.log.emit('UPLOAD BLOCKED: A previous attempt has unknown status. Check YouTube Studio before retrying to avoid duplicates.')
                        continue
                    jpeg=target / (current.stem+'_thumbnail.jpg')
                    prepare_image(image,jpeg,1280,720)
                    journal.set(fp,'uploading')
                    self.log.emit('Uploading to YouTube…')
                    from youtube_api import upload
                    result=upload(str(current),str(jpeg),title,desc,tags,
                        self.opts['visibility'],publish_at,
                        progress=lambda pct,idx=i:self.progress.emit(int((idx+.65+.35*pct/100)/len(self.beats)*100)),
                        already_uploaded=lambda video_id,k=fp:journal.set(k,'complete',video_id))
                    self.log.emit('YouTube: '+result['url'])
                    if result['warning']:self.log.emit('WARNING: '+result['warning'])
                else:
                    self.log.emit('Local video ready: '+str(current))
                self.progress.emit(int((i+1)/len(self.beats)*100))
            self.progress.emit(100)
            self.finished_all.emit()
        except Exception as exc:
            self.failed.emit(str(exc))


class Waveform(QWidget):
    def __init__(self):
        super().__init__()
        self.samples=[]
        self.setFixedHeight(58)
    def set_samples(self, values):
        self.samples=values or []
        self.update()
    def paintEvent(self, event):
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(),QColor('#FFF5F9'))
        width=self.width();mid=self.height()/2
        painter.setPen(QPen(QColor('#E88CAF'),2))
        if not self.samples:
            painter.drawLine(4,int(mid),max(4,width-4),int(mid))
        else:
            count=len(self.samples)
            for i, amplitude in enumerate(self.samples):
                x=round((i+.5)/count*width)
                h=max(2,float(amplitude)*mid*.88)
                painter.drawLine(x,int(mid-h),x,int(mid+h))
        painter.end()


class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.cfg=settings()
        self.beats=[]
        self.current=-1
        self.syncing=False
        self.art=self.cfg.get('artwork') if Path(self.cfg.get('artwork','')).is_file() else str(DEFAULT_ART_PATH)
        self.art_credit=''
        self.channel=None
        self.worker=None
        self.auth_worker=None
        self.analyse_worker=None
        self.setWindowTitle('LTA // UPLOAD')
        self.setMinimumSize(850,680)
        self.resize(1330,880)
        self.setStyleSheet(STYLE)
        root=QVBoxLayout(self);root.setContentsMargins(24,18,24,18);root.setSpacing(14)
        header=QHBoxLayout()
        brand=QVBoxLayout(); brand.addWidget(txt('LTA // UPLOAD','Heading'));brand.addWidget(txt('by LISTENTOAARXN  ·  Local beat-to-video publishing'))
        header.addLayout(brand);header.addStretch()
        self.channel_label=txt('YouTube not connected')
        header.addWidget(self.channel_label)
        header.addWidget(action('Connect YouTube',self.connect_youtube))
        header.addWidget(action('Disconnect',self.disconnect_youtube))
        header.addWidget(action('Settings  ⚙',self.edit_settings))
        root.addLayout(header)
        self.step_label=txt('STEP 1 OF 4  ·  BEATS','Step')
        root.addWidget(self.step_label)
        self.pages=QStackedWidget()
        root.addWidget(self.pages,stretch=1)
        left_wrap=QScrollArea(); left_wrap.setWidgetResizable(True)
        left=QWidget();self.left=QVBoxLayout(left)
        self.left.setSpacing(13)
        left_wrap.setWidget(left)
        right_wrap=QScrollArea();right_wrap.setWidgetResizable(True)
        right=QWidget();self.right=QVBoxLayout(right);self.right.setSpacing(12)
        right_wrap.setWidget(right)
        self.build_left();self.build_right()
        self.organise_wizard(left_wrap,right_wrap)
        footer=QHBoxLayout()
        self.status=txt('Ready to create. Add one or more beats.')
        footer.addWidget(self.status,stretch=1)
        self.back_btn=action('← Back',self.previous_step)
        footer.addWidget(self.back_btn)
        self.next_btn=action('Continue →',self.next_step,True)
        footer.addWidget(self.next_btn)
        self.start_btn=action('Generate & Upload',self.start,True)
        footer.addWidget(self.start_btn)
        root.addLayout(footer)
        self.progress=QProgressBar();self.progress.setRange(0,100);self.progress.setValue(0)
        root.addWidget(self.progress)
        self.audio_output=QAudioOutput(self);self.player=QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.playbackStateChanged.connect(self.play_state_changed)
        self.refresh_metadata()
        self.set_step(0)
        self.try_auto_connect()
        self.setup_sound()

    def build_left(self):
        self.left.addWidget(txt('01  BEAT SETUP','Section'))
        self.drop=DropZone();self.drop.filesDropped.connect(self.add_files);self.left.addWidget(self.drop)
        self.table=QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels(['Beat name','File','BPM','Key','BeatStars track URL'])
        self.table.setMinimumHeight(230)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(self.table_changed)
        self.table.currentCellChanged.connect(self.selected_changed)
        self.left.addWidget(self.table)
        self.selected_label=txt('SELECTED BEAT: None','Selected')
        self.left.addWidget(self.selected_label)
        r=QHBoxLayout()
        r.addWidget(action('Remove selected',self.remove_selected))
        r.addWidget(action('Re-analyse selected',self.analyse_selected))
        r.addStretch();self.left.addLayout(r)
        artists=QHBoxLayout()
        self.a1=QLineEdit(self.cfg.get('artist1',''));self.a1.setPlaceholderText('Artist 1')
        self.a2=QLineEdit(self.cfg.get('artist2',''));self.a2.setPlaceholderText('Artist 2')
        for lab,entry in [('Artist 1',self.a1),('Artist 2',self.a2)]:
            v=QVBoxLayout();v.addWidget(txt(lab,'Section'));v.addWidget(entry);artists.addLayout(v)
        self.left.addLayout(artists)
        self.a1.textChanged.connect(self.refresh_metadata);self.a2.textChanged.connect(self.refresh_metadata)
        extra=QHBoxLayout()
        self.genre=QLineEdit(self.cfg.get('genre',''));self.genre.setPlaceholderText('Genre (optional)')
        self.mood=QLineEdit(self.cfg.get('mood',''));self.mood.setPlaceholderText('Mood (optional)')
        extra.addWidget(self.genre);extra.addWidget(self.mood)
        self.left.addLayout(extra)
        self.genre.textChanged.connect(self.refresh_metadata);self.mood.textChanged.connect(self.refresh_metadata)
        self.free=QCheckBox('Add [FREE] to YouTube title');self.free.setChecked(bool(self.cfg.get('free',True)))
        self.free.toggled.connect(self.refresh_metadata);self.left.addWidget(self.free)
        self.left.addWidget(txt('02  ARTWORK','Section'))
        artrow=QHBoxLayout()
        artrow.addWidget(action('Choose image',self.pick_art))
        artrow.addWidget(action('Find on Pexels',self.find_art))
        artrow.addWidget(action('Use default',self.use_default_art))
        self.left.addLayout(artrow)
        self.art_label=txt(Path(self.art).name)
        self.left.addWidget(self.art_label)
        self.left.addWidget(txt('03  PUBLISH','Section'))
        p=QHBoxLayout()
        self.yt=QCheckBox('YouTube');self.yt.setChecked(True)
        self.bs=QCheckBox('BeatStars assisted');self.bs.setChecked(False)
        self.bs.toggled.connect(self.bs_changed)
        p.addWidget(self.yt);p.addWidget(self.bs);p.addStretch()
        self.left.addLayout(p)
        pub=QHBoxLayout()
        self.visibility=QComboBox();self.visibility.addItems(['Private','Unlisted','Public','Scheduled'])
        self.visibility.setCurrentText(self.cfg.get('visibility','Private'))
        self.visibility.currentTextChanged.connect(self.schedule_visibility)
        self.res=QComboBox();self.res.addItems(['1920x1080','1280x720','2560x1440'])
        self.res.setCurrentText(self.cfg.get('res','1920x1080'))
        pub.addWidget(self.visibility);pub.addWidget(self.res)
        self.left.addLayout(pub)
        self.schedule=QDateTimeEdit(QDateTime.currentDateTime().addDays(1))
        self.schedule.setDisplayFormat('dd MMM yyyy  HH:mm')
        self.schedule.setCalendarPopup(True)
        self.schedule.setCalendarWidget(QCalendarWidget())
        self.schedule.setMinimumDateTime(QDateTime.currentDateTime())
        self.left.addWidget(txt('Scheduled time (Europe/London)'))
        self.left.addWidget(self.schedule)
        self.schedule_visibility()
        self.bs_btn=action('Open BeatStars Studio ↗',lambda:webbrowser.open('https://www.beatstars.com/studio'))
        self.left.addWidget(self.bs_btn)
        self.bs_btn.setVisible(False)
        self.bs_copy=action('Copy selected beat details for BeatStars',self.copy_beatstars_details)
        self.left.addWidget(self.bs_copy)
        self.bs_copy.setVisible(False)
        self.left.addStretch()

    def build_right(self):
        self.right.addWidget(txt('LIVE PREVIEW','Section'))
        self.preview=QLabel()
        self.preview.setMinimumHeight(205)
        self.preview.setMaximumHeight(325)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet('border-radius:14px;background:#000000;color:#FFFFFF;')
        self.preview.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)
        self.right.addWidget(self.preview)
        self.waveform=Waveform()
        self.right.addWidget(self.waveform)
        r=QHBoxLayout()
        self.audio_btn=action('▶ Play beat',self.toggle_audio)
        r.addWidget(self.audio_btn)
        self.duration=txt('No audio selected')
        r.addWidget(self.duration);r.addStretch()
        self.right.addLayout(r)
        self.right.addWidget(txt('YouTube title  ·  editable','Section'))
        self.title_editor=QLineEdit()
        self.title_editor.textEdited.connect(self.title_edited)
        self.right.addWidget(self.title_editor)
        self.right.addWidget(txt('Description  ·  editable','Section'))
        self.desc=QTextEdit();self.desc.setMinimumHeight(205)
        self.desc.textChanged.connect(self.desc_edited)
        self.right.addWidget(self.desc)
        self.right.addWidget(txt('Tags  ·  comma-separated, editable','Section'))
        self.tags=QLineEdit()
        self.tags.textEdited.connect(self.tags_edited)
        self.right.addWidget(self.tags)
        self.chip_frame=QWidget()
        self.chips=QHBoxLayout(self.chip_frame)
        self.chips.setContentsMargins(0,0,0,0)
        self.right.addWidget(self.chip_frame)
        self.right.addWidget(txt('UPLOAD ACTIVITY','Section'))
        self.log=QTextEdit();self.log.setReadOnly(True);self.log.setMaximumHeight(135)
        self.right.addWidget(self.log)
        self.right.addStretch()
        self.update_preview()

    def organise_wizard(self,left_wrap,right_wrap):
        """Reuse original controls unchanged, but show one task at a time."""
        layout=self.left
        items=[]
        while layout.count():
            items.append(layout.takeAt(0))
        # Each item is an existing widget or nested layout from build_left.
        groups=[items[:5],items[5:11],items[11:18]]
        self.step_titles=['BEATS','DETAILS & ARTWORK','PUBLISH SETTINGS','REVIEW & UPLOAD']
        for group in groups:
            page=QWidget();v=QVBoxLayout(page);v.setContentsMargins(18,12,18,12);v.setSpacing(16)
            for item in group:
                if item.widget():v.addWidget(item.widget())
                elif item.layout():v.addLayout(item.layout())
            v.addStretch()
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(page)
            self.pages.addWidget(scroll)
        self.pages.addWidget(right_wrap)
        left_wrap.deleteLater()

    def set_step(self,index):
        self.step=max(0,min(index,3))
        self.pages.setCurrentIndex(self.step)
        self.step_label.setText(f'STEP {self.step+1} OF 4  ·  {self.step_titles[self.step]}')
        self.back_btn.setVisible(self.step>0)
        self.next_btn.setVisible(self.step<3)
        self.start_btn.setVisible(self.step==3)
        self.next_btn.setText(['Continue to details →','Continue to publishing →','Review everything →',''][self.step])
        if self.step==3:self.refresh_metadata()
        effect=QGraphicsOpacityEffect(self.pages.currentWidget())
        self.pages.currentWidget().setGraphicsEffect(effect)
        self.transition=QPropertyAnimation(effect,b'opacity',self)
        self.transition.setDuration(260)
        self.transition.setStartValue(0.15)
        self.transition.setEndValue(1.0)
        self.transition.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.transition.start()

    def next_step(self):
        if self.step==0 and not self.beats:
            show_error(self,'Add a beat first','Drop an MP3 or WAV into the app to continue.');return
        self.set_step(self.step+1)

    def previous_step(self):self.set_step(self.step-1)

    def setup_sound(self):
        # Gentle optional UI feedback; disabled if the audio device cannot play it.
        import wave, math, struct
        sound=APP_DIR/'ui_click.wav'
        if not sound.exists():
            with wave.open(str(sound),'wb') as f:
                f.setnchannels(1);f.setsampwidth(2);f.setframerate(22050)
                f.writeframes(b''.join(struct.pack('<h',int(1600*math.sin(2*math.pi*720*i/22050)*(1-i/2205))) for i in range(2205)))
        self.click_sound=QSoundEffect(self)
        self.click_sound.setSource(QUrl.fromLocalFile(str(sound)))
        self.click_sound.setVolume(.13)
        for b in self.findChildren(QPushButton):
            b.clicked.connect(self.click_sound.play)

    def cfg_from_ui(self):
        values=self.cfg.copy()
        values.update({'artist1':self.a1.text().strip(),'artist2':self.a2.text().strip(),
            'genre':self.genre.text().strip(),'mood':self.mood.text().strip(),
            'free':self.free.isChecked(),'res':self.res.currentText(),
            'visibility':self.visibility.currentText(),'artwork':self.art})
        return values

    def add_files(self,files):
        known={b.path.casefold() for b in self.beats}
        added=[]
        for filepath in files:
            p=Path(filepath)
            if not p.exists() or p.suffix.lower() not in ('.mp3','.wav') or str(p).casefold() in known: continue
            try:
                duration=probe_duration(p)
            except Exception as exc:
                show_error(self,'Audio could not be loaded',f'{p.name}: {exc}');continue
            self.beats.append(Beat(str(p),p.stem,duration=duration))
            added.append(str(p));known.add(str(p).casefold())
        self.populate_table()
        if added:
            self.table.setCurrentCell(len(self.beats)-len(added),0)
            self.status.setText(f'{len(self.beats)} beat(s) ready. Detecting BPM and key…')
            self.begin_analysis(added)

    def begin_analysis(self,paths):
        if self.analyse_worker and self.analyse_worker.isRunning():
            self.status.setText('Analysis in progress. Further files can be analysed with Re-analyse selected.')
            return
        self.analyse_worker=AnalyseWorker(paths)
        self.analyse_worker.result.connect(self.on_analyzed)
        self.analyse_worker.failed.connect(lambda p,e:self.append_log('Analysis skipped for '+Path(p).name+': '+e))
        self.analyse_worker.start()

    def analyse_selected(self):
        if self.current>=0:self.begin_analysis([self.beats[self.current].path])

    def on_analyzed(self,path,result):
        for item in self.beats:
            if item.path==path:
                if not item.bpm:item.bpm=str(result['bpm'])
                if not item.key:item.key=result['key']
                item.duration=result['duration']
                item.waveform=result.get('waveform',[])
        self.populate_table(preserve=self.current)
        self.refresh_metadata()
        self.status.setText('BPM/key estimates ready. Correct values in the table if necessary.')

    def populate_table(self,preserve=None):
        self.syncing=True
        self.table.setRowCount(len(self.beats))
        for row,beat in enumerate(self.beats):
            for col,value in enumerate([beat.name,Path(beat.path).name,beat.bpm,beat.key,beat.beatstars_url]):
                item=QTableWidgetItem(str(value))
                if col==1:item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row,col,item)
        self.syncing=False
        if preserve is not None and 0<=preserve<len(self.beats):self.table.setCurrentCell(preserve,0)

    def table_changed(self,item):
        if self.syncing or item.row()>=len(self.beats):return
        beat=self.beats[item.row()]
        value=item.text().strip()
        if item.column()==0:beat.name=value
        elif item.column()==2:beat.bpm=value
        elif item.column()==3:beat.key=value
        elif item.column()==4:beat.beatstars_url=value
        self.refresh_metadata()

    def selected_changed(self,row,*_):
        self.current=row if 0<=row<len(self.beats) else -1
        self.selected_label.setText('SELECTED BEAT: '+(f'{row+1} / {len(self.beats)}  ·  {self.beats[row].name}' if self.current>=0 else 'None'))
        self.refresh_metadata()
        if self.current>=0:
            beat=self.beats[self.current]
            self.duration.setText(f'{Path(beat.path).name} · {int(beat.duration//60)}:{int(beat.duration%60):02d}')
            self.player.stop();self.player.setSource(QUrl.fromLocalFile(beat.path))
            self.waveform.set_samples(beat.waveform)
        else:
            self.duration.setText('No audio selected')
            self.waveform.set_samples([])

    def remove_selected(self):
        if self.current<0:return
        self.player.stop()
        del self.beats[self.current]
        self.current=-1
        self.populate_table()
        if self.beats:self.table.setCurrentCell(0,0)
        else:self.refresh_metadata()

    def ui_metadata(self,beat):
        return metadata(self.a1.text(),self.a2.text(),beat.name,beat.bpm,beat.key,
            self.cfg_from_ui(),beat.beatstars_url,self.art_credit)

    def refresh_metadata(self,*_):
        if not hasattr(self,'title_editor'):return
        self.syncing=True
        if self.current>=0 and self.current<len(self.beats):
            beat=self.beats[self.current]
            try:
                meta=self.ui_metadata(beat)
                self.title_editor.setText(beat.meta_override or meta['title'])
                self.desc.setPlainText(beat.desc_override or meta['description'])
                self.tags.setText(beat.tags_override or ', '.join(meta['tags']))
            except Exception as exc:
                self.title_editor.setText('');self.desc.setPlainText(str(exc));self.tags.setText('')
        else:
            self.title_editor.setText('Add a beat to see its title')
            self.desc.setPlainText('Your description and BeatStars track link will appear here.')
            self.tags.setText('')
        self.syncing=False
        self.update_preview()
        self.render_chips()

    def render_chips(self):
        while self.chips.count():
            item=self.chips.takeAt(0)
            if item.widget():item.widget().deleteLater()
        values=[t.strip() for t in self.tags.text().split(',') if t.strip()]
        for t in values[:7]:
            b=action(t[:23]+' ×',lambda _=False,v=t:self.remove_chip(v))
            b.setStyleSheet('QPushButton { background:#FFE4EE; border:0; border-radius:9px; padding:4px 8px; font-size:10px; }')
            self.chips.addWidget(b)
        self.chips.addStretch()

    def remove_chip(self,removed):
        values=[t.strip() for t in self.tags.text().split(',') if t.strip() and t.strip()!=removed]
        self.tags.setText(', '.join(values))
        self.tags_edited('')

    def title_edited(self,_):
        if not self.syncing and self.current>=0:self.beats[self.current].meta_override=self.title_editor.text()
    def desc_edited(self):
        if not self.syncing and self.current>=0:self.beats[self.current].desc_override=self.desc.toPlainText()
    def tags_edited(self,_):
        if not self.syncing and self.current>=0:self.beats[self.current].tags_override=self.tags.text()
        self.render_chips()

    def pick_art(self):
        p=QFileDialog.getOpenFileName(self,'Choose artwork','','Images (*.jpg *.jpeg *.png *.webp)')[0]
        if p:
            self.art=p;self.art_credit='';self.update_preview();self.refresh_metadata()
    def use_default_art(self):
        self.art=self.cfg.get('artwork') if Path(self.cfg.get('artwork','')).exists() else str(DEFAULT_ART_PATH)
        self.art_credit='';self.refresh_metadata()
    def find_art(self):
        dialog=PictureSearchDialog(self)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.art=dialog.selected_path;self.art_credit=dialog.credit;self.refresh_metadata()

    def update_preview(self):
        if not hasattr(self,'preview'):return
        self.art_label.setText('Artwork: '+Path(self.art).name)
        pix=QPixmap(self.art)
        if not pix.isNull():
            self.preview.setPixmap(pix.scaled(680,310,Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation))
        else:self.preview.setText('Choose an artwork image')

    def toggle_audio(self):
        if self.current<0:return
        if self.player.playbackState()==QMediaPlayer.PlaybackState.PlayingState:self.player.pause()
        else:self.player.play()
    def play_state_changed(self,state):
        self.audio_btn.setText('Ⅱ Pause beat' if state==QMediaPlayer.PlaybackState.PlayingState else '▶ Play beat')

    def bs_changed(self,enabled):
        self.bs_btn.setVisible(enabled)
        self.bs_copy.setVisible(enabled)

    def copy_beatstars_details(self):
        if self.current<0:
            show_error(self,'Select a beat','Click a row before copying its details.');return
        beat=self.beats[self.current]
        try:
            info=self.ui_metadata(beat)
            lines=[f'Beat: {beat.name}',f'Artists: {self.a1.text()} x {self.a2.text()}',
                f'BPM: {beat.bpm or "Not set"}',f'Key: {beat.key or "Not set"}',
                f'Genre: {info["genre"] or "Not set"}',f'Mood: {self.mood.text() or "Not set"}',
                f'Tags: {", ".join(info["tags"])}']
            if self.cfg.get('beatstars_licence_note'):
                lines.append('Licence note: '+self.cfg['beatstars_licence_note'])
            QApplication.clipboard().setText('\n'.join(lines))
            self.append_log('Copied BeatStars metadata for: '+beat.name)
        except Exception as exc:show_error(self,'Could not copy details',exc)
    def schedule_visibility(self,*_):
        self.schedule.setEnabled(self.visibility.currentText()=='Scheduled')

    def edit_settings(self):
        dia=SettingsDialog(self.cfg,self)
        if dia.exec()==QDialog.DialogCode.Accepted:
            try:
                self.cfg=dia.apply();save_settings(self.cfg)
                self.refresh_metadata()
            except Exception as exc:show_error(self,'Settings could not be saved',exc)

    def connect_youtube(self):
        path=self.cfg.get('oauth_client_path')
        if not path:
            show_error(self,'Google OAuth setup required','YouTube requires a Google Cloud OAuth Desktop client JSON (not your password). Create one in Google Cloud Console, enable YouTube Data API v3, add yourself as a test user if needed, then choose the JSON in Settings. See YOUTUBE_SETUP_GUIDE.md.')
            return
        self.channel_label.setText('Connecting…')
        self.auth_worker=AuthWorker(path)
        self.auth_worker.connected.connect(self.auth_done)
        self.auth_worker.error.connect(lambda e:(self.channel_label.setText('Not connected'),show_error(self,'YouTube connection failed',e)))
        self.auth_worker.start()

    def try_auto_connect(self):
        try:
            import keyring
            if not keyring.get_password('LTA_UPLOAD_YOUTUBE','oauth'):return
        except Exception:return
        self.channel_label.setText('Checking YouTube connection…')
        self.auth_worker=AuthWorker(None)
        self.auth_worker.connected.connect(self.auto_auth_done)
        self.auth_worker.error.connect(lambda e:self.channel_label.setText('Reconnect YouTube required'))
        self.auth_worker.start()

    def auto_auth_done(self,info):
        self.channel=info
        self.channel_label.setText('✓ '+info['name'])

    def disconnect_youtube(self):
        try:
            youtube_api.disconnect()
            self.channel=None
            self.channel_label.setText('YouTube not connected')
        except Exception as exc:show_error(self,'Could not disconnect',exc)

    def auth_done(self,info):
        self.channel=info
        self.channel_label.setText('✓ '+info['name'])
        notify(self,'Connected to YouTube', 'Connected channel: '+info['name'])

    def append_log(self,text):
        self.log.append(text)
        self.status.setText(text)

    def start(self):
        self.set_step(3)
        from core import trim_tags
        if not self.beats:
            show_error(self,'No beats','Choose at least one MP3 or WAV file.');return
        if self.worker and self.worker.isRunning():return
        if not Path(self.art).exists():
            show_error(self,'Artwork missing','Choose a valid image file.');return
        cfg=self.cfg_from_ui()
        if not cfg['output_dir']:
            show_error(self,'Output folder needed','Select output folder in Settings.');return
        if self.yt.isChecked() and not self.channel:
            show_error(self,'Connect YouTube','Use Connect YouTube first or uncheck YouTube to render locally.');return
        for beat in self.beats:
            try:
                if not beat.name:raise ValueError('Enter a beat name in the table.')
                if not Path(beat.path).exists():raise ValueError('Audio file no longer exists: '+beat.path)
                if beat.beatstars_url and not valid_beatstars_url(beat.beatstars_url):
                    raise ValueError('BeatStars link must be a direct track URL: '+beat.beatstars_url)
                info=self.ui_metadata(beat)
                title=beat.meta_override or info['title']
                description=beat.desc_override or info['description']
                if len(title)>100 or not title:raise ValueError('YouTube title must be 1–100 characters.')
                if len(description.encode('utf-8'))>5000:raise ValueError('YouTube description exceeds 5000 bytes.')
                custom=beat.tags_override
                if custom:
                    entered=[t.strip() for t in custom.split(',') if t.strip()]
                    if len(trim_tags(entered)) != len(set(t.lower() for t in entered)):
                        raise ValueError('YouTube tags exceed the 500-character limit or contain invalid values. Shorten them.')
            except Exception as e:show_error(self,'Check beat details',e);return
        publish_at=None
        if self.yt.isChecked() and self.visibility.currentText()=='Scheduled':
            try:
                # UI displays UK wall-clock values regardless of computer's current timezone.
                d=self.schedule.dateTime()
                publish_at=london_publish_time(datetime(d.date().year(),d.date().month(),d.date().day(),
                    d.time().hour(),d.time().minute()))
            except Exception as exc:show_error(self,'Schedule error',exc);return
        self.cfg=cfg;save_settings(self.cfg)
        opts={'cfg':cfg,'a1':self.a1.text().strip(),'a2':self.a2.text().strip(),
              'image':self.art,'credit':self.art_credit,'youtube':self.yt.isChecked(),
              'beatstars':self.bs.isChecked(),'channel':self.channel,'visibility':self.visibility.currentText().lower(),
              'publish_at':publish_at}
        self.log.clear();self.progress.setValue(0);self.start_btn.setEnabled(False)
        self.worker=UploadWorker(deepcopy(self.beats),opts)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log.connect(self.append_log)
        self.worker.finished_all.connect(self.finished)
        self.worker.failed.connect(self.failed)
        self.worker.start()

    def finished(self):
        self.start_btn.setEnabled(True)
        self.append_log('Finished processing queue. Check messages above for skipped BeatStars/YouTube steps.')
        self.status.setText('Finished.')
        notify(self,'LTA // UPLOAD','Queue finished. Check upload activity for video links or assisted-upload steps.')

    def failed(self,msg):
        self.start_btn.setEnabled(True)
        self.append_log('ERROR: '+msg)
        show_error(self,'Upload pipeline failed',msg)

    def closeEvent(self,event):
        if self.worker and self.worker.isRunning():
            notify(self,'Work in progress','The app is rendering or uploading. Keep it open until complete.')
            event.ignore();return
        if (self.analyse_worker and self.analyse_worker.isRunning()) or (self.auth_worker and self.auth_worker.isRunning()):
            notify(self,'Work in progress','Please close after this operation finishes.')
            event.ignore();return
        event.accept()


def main():
    app=QApplication(sys.argv)
    app.setApplicationName('LTA // UPLOAD')
    win=Main();win.show()
    sys.exit(app.exec())

if __name__=='__main__':main()
