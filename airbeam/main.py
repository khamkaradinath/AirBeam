import os
import base64
import webbrowser
from io import BytesIO

from fastapi import FastAPI, UploadFile, File, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
import uvicorn
import qrcode
from jinja2 import Template
from fastapi.staticfiles import StaticFiles

from .config import PORT, APP_NAME
from .utils import get_ip, format_size, format_date


app = FastAPI()
BASE_DIR = os.path.dirname(__file__)
shared_folder = os.path.join(BASE_DIR, "..", "shared")
os.makedirs(shared_folder, exist_ok=True)
app.mount("/static", StaticFiles(directory="airbeam/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    file_records = []
    for f in os.listdir(shared_folder):
        path = os.path.join(shared_folder, f)
        size = os.path.getsize(path)
        t = os.path.getmtime(path)
        file_records.append({
            "name": f,
            "size": format_size(size),
            "date": format_date(t)
        })

    file_records.sort(key=lambda x: x["date"], reverse=True)

    ip = get_ip()
    url = f"http://{ip}:{PORT}"

    img = qrcode.make(url)
    img_bytes = BytesIO()
    img.save(img_bytes, format="PNG")
    img_b64 = base64.b64encode(img_bytes.getvalue()).decode()

    template_path = os.path.join(BASE_DIR, "templates", "index.html")
    with open(template_path, "r") as f:
        template = Template(f.read())

    return template.render(files=file_records,
                           ip=ip,
                           port=PORT,
                           qr=img_b64,
                           app_name=APP_NAME)


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    with open(os.path.join(shared_folder, file.filename), "wb") as f:
        f.write(data)
    return RedirectResponse("/", status_code=303)


@app.post("/delete")
async def delete_file(filename: str = Form(...)):
    try:
        os.remove(os.path.join(shared_folder, filename))
    except:
        pass
    return RedirectResponse("/", status_code=303)


@app.get("/files/{fname}")
def download(fname: str):
    return FileResponse(os.path.join(shared_folder, fname), filename=fname)


def run():
    ip = get_ip()
    url = f"http://{ip}:{PORT}"
    webbrowser.open(url)
    uvicorn.run("airbeam.main:app", host="0.0.0.0", port=PORT, log_level="warning", reload=False)


if __name__ == "__main__":
    run()
