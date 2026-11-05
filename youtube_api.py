"""Real Google OAuth and YouTube Data API integration. Tokens live in OS credential vault."""
from __future__ import annotations
import json
import random
import time
from pathlib import Path

SERVICE = 'LTA_UPLOAD_YOUTUBE'
SCOPES = ['https://www.googleapis.com/auth/youtube.upload',
          'https://www.googleapis.com/auth/youtube.readonly']


def _imports():
    try:
        import keyring
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError
        return keyring, Credentials, Request, InstalledAppFlow, build, MediaFileUpload, HttpError
    except ImportError as exc:
        raise RuntimeError('YouTube libraries are missing. Run INSTALL_AND_START.bat again.') from exc


def disconnect():
    keyring,*_ = _imports()
    try: keyring.delete_password(SERVICE,'oauth')
    except keyring.errors.PasswordDeleteError: pass


def connect(client_json):
    keyring, Credentials, Request, InstalledAppFlow, build, MediaFileUpload, HttpError = _imports()
    if not Path(client_json).is_file():
        raise ValueError('Choose the OAuth desktop client JSON you downloaded from Google Cloud.')
    with open(client_json, encoding='utf-8') as fp:
        data=json.load(fp)
    if 'installed' not in data:
        raise ValueError('Google Cloud credential must be OAuth client type: Desktop app.')
    flow = InstalledAppFlow.from_client_secrets_file(client_json, scopes=SCOPES)
    credentials = flow.run_local_server(port=0, open_browser=True, access_type='offline', prompt='consent')
    keyring.set_password(SERVICE,'oauth',credentials.to_json())
    return channel_info()


def get_credentials():
    keyring, Credentials, Request, *_ = _imports()
    raw = keyring.get_password(SERVICE,'oauth')
    if not raw:
        raise RuntimeError('YouTube is not connected. Click Connect YouTube first.')
    creds = Credentials.from_authorized_user_info(json.loads(raw), scopes=SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            keyring.set_password(SERVICE,'oauth',creds.to_json())
        else:
            raise RuntimeError('YouTube credentials expired. Disconnect and connect again.')
    return creds


def api_service():
    *_, build, MediaFileUpload, HttpError = _imports()
    return build('youtube','v3', credentials=get_credentials(), cache_discovery=False)


def channel_info():
    result=api_service().channels().list(part='snippet',mine=True).execute()
    entries=result.get('items') or []
    if not entries:
        raise RuntimeError('Signed in, but no YouTube channel was found. Select an account with a channel.')
    channel=entries[0]
    snippet=channel.get('snippet') or {}
    thumbs=snippet.get('thumbnails') or {}
    img=(thumbs.get('default') or {}).get('url','')
    return {'id':channel['id'],'name':snippet.get('title','YouTube channel'),'image':img}


def upload(video_path, thumbnail_path, title, description, tags, privacy='private', publish_at=None,
           progress=None, already_uploaded=None):
    """Resumable media upload. Never retries ambiguous upload across program restarts.

    already_uploaded callback gets video id immediately after YouTube confirms insert success;
    caller persists it before thumbnail operation. Recoverable 5xx retries use same
    resumable upload session, not a new videos.insert request.
    """
    *_, MediaFileUpload, HttpError = _imports()
    service=api_service()
    if publish_at:
        privacy='private'
    if privacy not in ('private','public','unlisted'):
        raise ValueError('Invalid YouTube visibility.')
    video={'snippet':{'title':title,'description':description,'tags':tags,'categoryId':'10'},
           'status':{'privacyStatus':privacy,'selfDeclaredMadeForKids':False}}
    if publish_at:
        video['status']['publishAt']=publish_at
    media=MediaFileUpload(str(video_path),mimetype='video/mp4',chunksize=8*1024*1024,resumable=True)
    req=service.videos().insert(part='snippet,status',body=video,media_body=media)
    response=None
    retry=0
    while response is None:
        try:
            status,response=req.next_chunk()
            if status and progress:
                progress(int(status.progress()*100))
            retry=0
        except (OSError,ConnectionError,TimeoutError,HttpError) as exc:
            status_code = getattr(getattr(exc,'resp',None),'status',None)
            if isinstance(exc,HttpError) and status_code not in (500,502,503,504,429):
                raise
            retry+=1
            if retry > 6:
                raise RuntimeError('Upload interrupted; check YouTube Studio before trying again. '+str(exc)) from exc
            time.sleep(min(30,(2**retry)+random.random()))
    video_id=response.get('id')
    if not video_id:
        raise RuntimeError('YouTube did not return a video ID. Check YouTube Studio before retrying.')
    if already_uploaded:
        already_uploaded(video_id)
    warning=''
    if thumbnail_path:
        try:
            thumb=MediaFileUpload(str(thumbnail_path),mimetype='image/jpeg',resumable=False)
            service.thumbnails().set(videoId=video_id,media_body=thumb).execute()
        except Exception as exc:
            warning='Video uploaded, but custom thumbnail failed: '+str(exc)
    if progress: progress(100)
    return {'id':video_id,'url':f'https://www.youtube.com/watch?v={video_id}','warning':warning}
