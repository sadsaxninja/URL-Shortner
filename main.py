import os
import string
import random
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# ────────────────────────────────────────────────────────────
# DATABASE CONFIG
# ─────────────────────────────────────────────────────────────
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import pathlib

STATIC_DIR = pathlib.Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./links.db")
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Link(Base):
    __tablename__ = "links"
    id = Column(Integer, primary_key=True, index=True)
    long_url = Column(String, nullable=False)
    short_code = Column(String, unique=True, index=True, nullable=False)
    clicks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, nullable=True)

# ─────────────────────────────────────────────────────────────
# APP LIFECYCLE & MIDDLEWARE
# ─────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="LinkRouter API", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(STATIC_DIR / "index.html")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────────────────────────────
# ENCODING & MODELS
# ─────────────────────────────────────────────────────────────
BASE62 = string.ascii_letters + string.digits

class ShortenRequest(BaseModel):
    long_url: HttpUrl
    custom_code: str | None = None

class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    long_url: str
    clicks: int

class AnalyticsResponse(BaseModel):
    short_code: str
    long_url: str
    clicks: int
    created_at: str
    last_accessed: str | None

# ────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────
@app.post("/shorten", response_model=ShortenResponse)
def shorten_link(req: ShortenRequest):
    db = next(get_db())
    
    if req.custom_code:
        if not all(c in BASE62 for c in req.custom_code) or len(req.custom_code) < 3:
            raise HTTPException(400, "Custom code must be 3+ alphanumeric characters.")
        if db.query(Link).filter(Link.short_code == req.custom_code).first():
            raise HTTPException(409, "Custom code already in use.")
        short_code = req.custom_code
    else:
        while True:
            short_code = "".join(random.choices(BASE62, k=6))
            if not db.query(Link).filter(Link.short_code == short_code).first():
                break

    new_link = Link(long_url=str(req.long_url), short_code=short_code)
    db.add(new_link)
    db.commit()
    db.refresh(new_link)

    return ShortenResponse(
        short_code=new_link.short_code,
        short_url=f"/{new_link.short_code}",
        long_url=new_link.long_url,
        clicks=0
    )

@app.get("/{code}")
def redirect_link(code: str, request: Request):
    db = next(get_db())
    link = db.query(Link).filter(Link.short_code == code).first()
    if not link:
        raise HTTPException(404, "Link not found")
    
    link.clicks += 1
    link.last_accessed = datetime.utcnow()
    db.commit()
    
    return RedirectResponse(url=link.long_url, status_code=302)

@app.get("/analytics/{code}", response_model=AnalyticsResponse)
def get_analytics(code: str):
    db = next(get_db())
    link = db.query(Link).filter(Link.short_code == code).first()
    if not link:
        raise HTTPException(404, "Link not found")
    return AnalyticsResponse(
        short_code=link.short_code,
        long_url=link.long_url,
        clicks=link.clicks,
        created_at=link.created_at.isoformat(),
        last_accessed=link.last_accessed.isoformat() if link.last_accessed else None
    )