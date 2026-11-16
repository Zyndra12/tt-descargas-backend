"""
Backend Microservicio de Extracción de Videos de TikTok Sin Marca de Agua
Powered by FastAPI, TikWM & yt-dlp
"""

import os
import re
from typing import Optional
from urllib.parse import quote
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import requests
import yt_dlp

app = FastAPI(
    title="TikTok Video Downloader API",
    description="API de alta velocidad para extraer videos de TikTok sin marca de agua",
    version="1.1.0"
)

# Permitir solicitudes CORS desde cualquier origen (para la app Android)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ExtractRequest(BaseModel):
    url: str

class VideoResponse(BaseModel):
    status: str
    id: str
    title: str
    author: str
    author_name: Optional[str] = ""
    author_avatar: Optional[str] = ""
    thumbnail: Optional[str] = ""
    video_no_watermark: str
    video_hd: Optional[str] = ""
    audio_url: Optional[str] = ""
    duration: Optional[int] = 0

def clean_tiktok_url(text: str) -> str:
    """Extrae la URL de TikTok del texto ingresado o compartido"""
    pattern = r'https?://[^\s]+'
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    return text.strip()

@app.get("/")
def home():
    return {
        "app": "TT Descargas API",
        "status": "online",
        "version": "1.1.0",
        "docs": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/extract", response_model=VideoResponse)
def extract_video_post(req: ExtractRequest):
    return process_url(req.url)

@app.get("/api/extract", response_model=VideoResponse)
def extract_video_get(url: str = Query(..., description="URL del video de TikTok")):
    return process_url(url)

@app.get("/api/stream")
def stream_video(url: str = Query(..., description="URL original de TikTok")):
    """
    Endpoint Proxy: Transmite los bytes del video desde TikTok usando las cookies
    y headers de yt-dlp para evitar errores 403 Forbidden por restricción de IP.
    """
    target_url = clean_tiktok_url(url)
    if not target_url:
        raise HTTPException(status_code=400, detail="URL de TikTok no válida")

    opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if not info:
                raise HTTPException(status_code=404, detail="No se encontró información del video")

            formats = info.get("formats", [])
            fmt = formats[-1] if formats else info
            video_url = fmt.get("url", "")

            if not video_url:
                raise HTTPException(status_code=404, detail="No se pudo obtener la URL de streaming del CDN")

            headers = dict(fmt.get("http_headers") or info.get("http_headers") or {})

            try:
                cookie_header = ydl.cookiejar.get_cookie_header(video_url)
                if cookie_header:
                    headers["Cookie"] = cookie_header
            except Exception:
                pass

            headers.setdefault("Referer", "https://www.tiktok.com/")
            headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

            r = requests.get(video_url, headers=headers, stream=True, timeout=30)
            if r.status_code != 200:
                raise HTTPException(status_code=r.status_code, detail=f"El CDN de TikTok rechazó la petición ({r.status_code})")

            return StreamingResponse(
                r.iter_content(chunk_size=64 * 1024),
                media_type="video/mp4",
                headers={"Content-Disposition": 'attachment; filename="tiktok_video.mp4"'},
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en streaming: {str(e)}")

def process_url(raw_url: str) -> VideoResponse:
    target_url = clean_tiktok_url(raw_url)
    if not target_url:
        raise HTTPException(status_code=400, detail="URL inválida de TikTok")

    # 1. Estrategia Principal: TikWM (URLs de CDN sin restricción de IP)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.post(
            'https://www.tikwm.com/api/',
            data={'url': target_url, 'hd': 1},
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            res_json = response.json()
            if res_json.get('code') == 0 and res_json.get('data'):
                data = res_json['data']

                hdplay_url = data.get('hdplay', '')
                if hdplay_url and not hdplay_url.startswith('http'):
                    hdplay_url = f"https://www.tikwm.com{hdplay_url}"

                play_url = data.get('play', '')
                if play_url and not play_url.startswith('http'):
                    play_url = f"https://www.tikwm.com{play_url}"

                wmplay_url = data.get('wmplay', '')
                if wmplay_url and not wmplay_url.startswith('http'):
                    wmplay_url = f"https://www.tikwm.com{wmplay_url}"

                video_url = hdplay_url or play_url or wmplay_url

                music_url = data.get('music', '')
                if music_url and not music_url.startswith('http'):
                    music_url = f"https://www.tikwm.com{music_url}"

                cover_url = data.get('cover', '')
                if cover_url and not cover_url.startswith('http'):
                    cover_url = f"https://www.tikwm.com{cover_url}"

                author_info = data.get('author', {})
                unique_id = author_info.get('unique_id', 'tiktok_user')
                nickname = author_info.get('nickname', unique_id)
                avatar = author_info.get('avatar', cover_url)

                if video_url:
                    return VideoResponse(
                        status="success",
                        id=str(data.get('id', '')),
                        title=data.get('title', 'TikTok Video'),
                        author=f"@{unique_id}",
                        author_name=nickname,
                        authorAvatar=avatar,
                        thumbnail=cover_url,
                        video_no_watermark=video_url,
                        video_hd=hdplay_url or video_url,
                        audio_url=music_url or video_url,
                        duration=data.get('duration', 0)
                    )
        else:
            print(f"TikWM retornó HTTP {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"Advertencia: Falló extracción vía TikWM API: {e}. Probando yt-dlp + Stream Proxy...")

    # 2. Estrategia de Respaldo: yt-dlp enrutado a través de nuestro endpoint /api/stream
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best',
        'extract_flat': False,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if not info:
                raise HTTPException(status_code=404, detail="No se pudo obtener información del video")

            video_id = info.get('id', '')
            title = info.get('title', 'TikTok Video')
            author = info.get('uploader_id', info.get('uploader', 'TikTok User'))
            author_name = info.get('uploader', author)
            thumbnail = info.get('thumbnail', '')
            duration = int(info.get('duration', 0) or 0)

            # En lugar de enviar la URL cruda v19-webapp-prime.us.tiktok.com que da 403 en el móvil,
            # devolvemos la URL de nuestro propio proxy /api/stream que retransmite con las cookies de yt-dlp
            encoded_target_url = quote(target_url, safe='')
            stream_proxy_url = f"/api/stream?url={encoded_target_url}"

            return VideoResponse(
                status="success",
                id=video_id,
                title=title,
                author=f"@{author}",
                author_name=author_name,
                author_avatar=thumbnail,
                thumbnail=thumbnail,
                video_no_watermark=stream_proxy_url,
                video_hd=stream_proxy_url,
                audio_url=stream_proxy_url,
                duration=duration
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando video con yt-dlp: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
