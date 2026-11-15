from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import yt_dlp
import tempfile
import os
import glob
import re
import shutil
import threading

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OPCOES = {'format': 'best', 'quiet': True, 'noplaylist': True}
QUALIDADES = {480, 720, 1080}
STATS_KEY = os.environ.get("STATS_KEY", "")

# ---------- Estatísticas (em memória, sem dados pessoais) ----------
_lock = threading.Lock()
_inicio = datetime.now(timezone.utc)


def _novo_dia():
    return {"buscas": 0, "downloads": 0, "erros": 0,
            "plataformas": defaultdict(int), "qualidades": defaultdict(int)}


_stats = defaultdict(_novo_dia)


def hoje():
    # Hora de Moçambique (UTC+2)
    return datetime.now(timezone(timedelta(hours=2))).strftime("%Y-%m-%d")


def plataforma(url: str) -> str:
    u = url.lower()
    if "tiktok.com" in u:
        return "tiktok"
    if "instagram.com" in u:
        return "instagram"
    if "facebook.com" in u or "fb.watch" in u:
        return "facebook"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    return "outra"


def registar(tipo: str, url: str, q=None, ok=True):
    p = plataforma(url)
    with _lock:
        d = _stats[hoje()]
        d[tipo] += 1
        if tipo == "downloads" and ok and q:
            d["qualidades"][str(q)] += 1
        if not ok:
            d["erros"] += 1
        if tipo == "buscas":
            d["plataformas"][p] += 1
        # guarda só os últimos 30 dias
        for dia in sorted(_stats.keys())[:-30]:
            del _stats[dia]
    print(f"PEDIDO tipo={tipo} plataforma={p} q={q} ok={ok}")


def extrair(url: str):
    with yt_dlp.YoutubeDL(OPCOES) as ydl:
        return ydl.extract_info(url, download=False)


# ---------- Rotas ----------
@app.get("/")
def home():
    return {"status": "Servidor Mega Dados online!"}


@app.get("/saude")
def saude():
    return {"status": "ok", "yt_dlp": yt_dlp.version.__version__}


@app.get("/estatisticas")
def estatisticas(chave: str = ""):
    if not STATS_KEY or chave != STATS_KEY:
        raise HTTPException(status_code=403, detail="Acesso negado.")
    with _lock:
        dias = {
            dia: {
                "buscas": d["buscas"],
                "downloads": d["downloads"],
                "erros": d["erros"],
                "plataformas": dict(d["plataformas"]),
                "qualidades": dict(d["qualidades"]),
            }
            for dia, d in sorted(_stats.items(), reverse=True)
        }
    return {
        "servidor_ligado_desde_utc": _inicio.isoformat(),
        "nota": "Os números reiniciam quando o servidor reinicia ou faz deploy.",
        "dias": dias,
    }


@app.get("/baixar")
def obter_video(url: str):
    try:
        info = extrair(url)
        registar("buscas", url)
        return {
            "titulo": info.get("title"),
            "capa": info.get("thumbnail"),
            "link_video": info.get("url")
        }
    except Exception as e:
        print("ERRO:", e)
        registar("buscas", url, ok=False)
        raise HTTPException(status_code=500, detail="Não foi possível processar este vídeo.")


@app.get("/download")
def descarregar(url: str, q: int = 720):
    if q not in QUALIDADES:
        q = 720

    formato = (
        f"best[height<={q}][ext=mp4]/"
        f"best[height<={q}]/"
        f"best[ext=mp4]/best"
    )

    pasta = tempfile.mkdtemp()
    opcoes = {
        'format': formato,
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
        registar("downloads", url, q=q)
        return FileResponse(
            ficheiros[0],
            media_type="video/mp4",
            filename=f"{nome}_{q}p.mp4",
            background=BackgroundTask(shutil.rmtree, pasta, ignore_errors=True),
        )
    except Exception as e:
        print("ERRO download:", e)
        registar("downloads", url, q=q, ok=False)
        shutil.rmtree(pasta, ignore_errors=True)
        raise HTTPException(status_code=500, detail="Não foi possível descarregar este vídeo.")
