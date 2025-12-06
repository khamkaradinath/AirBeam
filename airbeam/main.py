import os
import sys
import base64
import webbrowser
from io import BytesIO

from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Template
import uvicorn
import qrcode

from airbeam.config import PORT, APP_NAME
from airbeam.utils import get_ip, format_size, format_date


# -------------------------------------------------------------
# Paths (support both Python + PyInstaller .exe)
# -------------------------------------------------------------
def resource_path(relative_path: str):
    """
    Resolve path for normal mode and PyInstaller (._MEIPASS)
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = resource_path("static")
TEMPLATE_DIR = resource_path("templates")

# Store uploaded files next to .exe in folder: shared/
SHARED_DIR = os.path.join(BASE_DIR, "..", "shared")
os.makedirs(SHARED_DIR, exist_ok=True)


# -------------------------------------------------------------
# App + Static mounting
# -------------------------------------------------------------
app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# -------------------------------------------------------------
# Routes
# -------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Read shared folder
    files = []
    for f in os.listdir(SHARED_DIR):
        path = os.path.join(SHARED_DIR, f)
        size = os.path.getsize(path)
        t = os.path.getmtime(path)
        files.append({
            "name": f,
            "size": format_size(size),
            "date": format_date(t)
        })

    files.sort(key=lambda x: x["date"], reverse=True)

    # QR Code
    ip = get_ip()
    url = f"http://{ip}:{PORT}"
    qr = qrcode.make(url)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()

    # Load template
    template_path = os.path.join(TEMPLATE_DIR, "index.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template = Template(f.read())

    return template.render(
        app_name=APP_NAME,
        ip=ip,
        port=PORT,
        qr=qr_b64,
        files=files,
    )


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
        data = await file.read()
        with open(os.path.join(SHARED_DIR, file.filename), "wb") as f:
            f.write(data)
        return RedirectResponse("/", status_code=303)


@app.post("/delete")
async def delete_file(filename: str = Form(...)):
        try:
            os.remove(os.path.join(SHARED_DIR, filename))
        except:
            pass
        return RedirectResponse("/", status_code=303)


@app.get("/files/{fname}")
def download(fname: str):
        return FileResponse(os.path.join(SHARED_DIR, fname), filename=fname)


# -------------------------------------------------------------
# Run
# -------------------------------------------------------------
def run():
    ip = get_ip()
    url = f"http://{ip}:{PORT}"
    webbrowser.open(url)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_config=None,
        log_level=None,
    )



if __name__ == "__main__":
        run()
