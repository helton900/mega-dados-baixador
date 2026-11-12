from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
import yt_dlp
import tempfile
import os
import glob
import re
import shutil

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
    pasta = tempfile.mkdtemp()
    opcoes = {
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'noplaylist': True,
        'outtmpl': os.path.join(pasta, 'video.%(ext)s'),
    }
    try:
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(url, download=True)
        ficheiros = glob.glob(os.path.join(pasta, 'video.*'))
        if not ficheiros:
            raise ValueError("ficheiro não foi criado")
        nome = re.sub(r'[^A-Za-z0-9_-]+', '_', info.get("title") or "video")[:60] or "video"
        return FileResponse(
            ficheiros[0],
            media_type="video/mp4",
            filename=f"{nome}.mp4",
            background=BackgroundTask(shutil.rmtree, pasta, ignore_errors=True),
        )
    except Exception as e:
        print("ERRO download:", e)
        shutil.rmtree(pasta, ignore_errors=True)
        raise HTTPException(status_code=500, detail="Não foi possível descarregar este vídeo.")
