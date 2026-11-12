from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "Servidor Mega Dados online!"}

@app.get("/baixar")
def obter_video(url: str):
    opcoes = {'format': 'best', 'quiet': True, 'noplaylist': True}
    try:
        with yt_dlp.YoutubeDL(opcoes) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "titulo": info.get("title"),
                "capa": info.get("thumbnail"),
                "link_video": info.get("url")
            }
    except Exception as e:
        print("ERRO:", e)
        raise HTTPException(status_code=500, detail="Não foi possível processar este vídeo.")
