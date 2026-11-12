import tempfile, os, glob
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
import shutil

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
