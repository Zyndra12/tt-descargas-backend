"""
Backend Microservicio de Extracción de Videos de TikTok Sin Marca de Agua
Powered by FastAPI & yt-dlp
"""

import os
import re
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
import yt_dlp

app = FastAPI(
    title="TikTok Video Downloader API",
    description="API de alta velocidad para extraer videos de TikTok sin marca de agua",
    version="1.0.0"
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
        "version": "1.0.0",
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

def process_url(raw_url: str) -> VideoResponse:
    target_url = clean_tiktok_url(raw_url)
    if not target_url:
        raise HTTPException(status_code=400, detail="URL inválida de TikTok")

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
                raise HTTPException(status_code=404, detail="No se pudo obtener la información del video")

            video_id = info.get('id', '')
            title = info.get('title', 'TikTok Video')
            author = info.get('uploader_id', info.get('uploader', 'TikTok User'))
            author_name = info.get('uploader', author)
            thumbnail = info.get('thumbnail', '')
            duration = int(info.get('duration', 0) or 0)

            formats = info.get('formats', [])

            # Buscar stream sin marca de agua
            video_url = ""
            hd_url = ""
            audio_url = ""

            for f in formats:
                # Filtrar formatos de audio y video
                format_url = f.get('url', '')
                if not format_url:
                    continue

                if f.get('vcodec') != 'none' and not video_url:
                    video_url = format_url
                if f.get('height') and f.get('height') >= 720:
                    hd_url = format_url
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none' and not audio_url:
                    audio_url = format_url

            if not video_url:
                video_url = info.get('url', '')

            if not hd_url:
                hd_url = video_url

            if not audio_url:
                audio_url = video_url

            return VideoResponse(
                status="success",
                id=video_id,
                title=title,
                author=f"@{author}",
                author_name=author_name,
                author_avatar=thumbnail,
                thumbnail=thumbnail,
                video_no_watermark=video_url,
                video_hd=hd_url,
                audio_url=audio_url,
                duration=duration
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error procesando video: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
