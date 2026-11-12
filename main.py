from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import yt_dlp
import requests
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OPCOES = {'format': 'best', 'quiet': True, 'noplaylist': True}


def extrair(url: str):
    with yt_dlp.YoutubeDL(OPCOES) as ydl:
        return ydl.extract_info(url, download=False)


@app.get("/")
def home():
    return {"status": "Servidor Mega Dados online!"}


@app.get("/baixar")
def obter_video(url: str):
    try:
        info = extrair(url)
        return {
            "titulo": info.get("title"),
            "capa": info.get("thumbnail"),
            "link_video": info.get("url")
        }
    except Exception as e:
        print("ERRO:", e)
        raise HTTPException(status_code=500, detail="Não foi possível processar este vídeo.")


@app.get("/download")
def descarregar(url: str):
    try:
        info = extrair(url)
        video_url = info.get("url")
        headers = info.get("http_headers") or {}
        if not video_url:
            raise ValueError("sem link de vídeo")

        r = requests.get(video_url, headers=headers, stream=True, timeout=30)
        if r.status_code >= 400:
            print("ERRO download:", r.status_code)
            raise HTTPException(status_code=502, detail="O servidor do vídeo recusou o pedido.")

        nome = re.sub(r'[^A-Za-z0-9_-]+', '_', info.get("title") or "video")[:60] or "video"
        return StreamingResponse(
            r.iter_content(chunk_size=1024 * 256),
            media_type="video/mp4",
            headers={"Content-Disposition": f'attachment; filename="{nome}.mp4"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        print("ERRO:", e)
        raise HTTPException(status_code=500, detail="Não foi possível descarregar este vídeo.")
