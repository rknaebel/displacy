#!/usr/bin/python3
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers import displacy
from app.routers import docs
from app.routers import tools
from app.utils import get_args

args = get_args()

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/pages")

app.include_router(
    displacy.router,
    prefix="/api/display",
    tags=["display"]
)
app.include_router(
    docs.router,
    prefix="/api/docs",
    tags=["docs"]
)
app.include_router(
    tools.router,
    prefix="/api/tools",
    tags=["tools"]
)


@app.get("/", tags=["pages"])
@app.get("/index", tags=["pages"], response_class=HTMLResponse)
async def main(request: Request):
    return templates.TemplateResponse("document_view.html", {"request": request})


@app.get("/relations", tags=["pages"], response_class=HTMLResponse)
async def main(request: Request):
    return templates.TemplateResponse("relation_view.html", {"request": request})


@app.get("/vote", tags=["pages"], response_class=HTMLResponse)
async def main(request: Request):
    return templates.TemplateResponse("voting.html", {"request": request})


@app.get("/vote2", tags=["pages"], response_class=HTMLResponse)
async def main(request: Request):
    return templates.TemplateResponse("voting2.html", {"request": request})


if __name__ == '__main__':
    uvicorn.run("main:app", host=args.hostname, port=args.port, log_level="debug" if args.debug else "info",
                reload=args.debug)
