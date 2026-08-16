from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
import asyncio
import json
import os
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from .auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from .db import db, get_postgres_session
from .schemas import User, UserFilter
from .models import FilterCreate, FilterOut, AlertOut, TrafficPoint, TopologyLink, HostInfo
from .consumers import consume_alerts, consume_host_info
from .utils import manager
from .config import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")

# ---- Инициализация администратора ----
def init_admin(db: Session):
    admin = db.query(User).filter(User.username == DEFAULT_ADMIN_USERNAME).first()
    if not admin:
        hashed = get_password_hash(DEFAULT_ADMIN_PASSWORD)
        admin = User(username=DEFAULT_ADMIN_USERNAME, hashed_password=hashed)
        db.add(admin)
        db.commit()
        logger.info(f"Admin user '{DEFAULT_ADMIN_USERNAME}' created with default password.")

# ---- API маршруты (выше catch-all) ----

@app.post("/api/register")
async def register(username: str, password: str, db_session: Session = Depends(get_postgres_session)):
    existing = db_session.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed = get_password_hash(password)
    user = User(username=username, hashed_password=hashed)
    db_session.add(user)
    db_session.commit()
    return {"msg": "User created"}

@app.post("/api/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db_session: Session = Depends(get_postgres_session)):
    user = authenticate_user(db_session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/api/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {"username": current_user.username}

# Фильтры пользователя
@app.post("/api/filters", response_model=FilterOut)
async def save_filter(filter_data: FilterCreate, current_user: User = Depends(get_current_user),
                      db_session: Session = Depends(get_postgres_session)):
    new_filter = UserFilter(
        user_id=current_user.id,
        name=filter_data.name,
        filter_data=filter_data.filter_data
    )
    db_session.add(new_filter)
    db_session.commit()
    db_session.refresh(new_filter)
    return FilterOut(id=new_filter.id, name=new_filter.name,
                     filter_data=new_filter.filter_data,
                     created_at=new_filter.created_at.isoformat())

@app.get("/api/filters", response_model=list[FilterOut])
async def get_filters(current_user: User = Depends(get_current_user),
                      db_session: Session = Depends(get_postgres_session)):
    filters = db_session.query(UserFilter).filter(UserFilter.user_id == current_user.id).all()
    return [FilterOut(id=f.id, name=f.name, filter_data=f.filter_data,
                      created_at=f.created_at.isoformat()) for f in filters]

@app.delete("/api/filters/{filter_id}")
async def delete_filter(filter_id: int, current_user: User = Depends(get_current_user),
                        db_session: Session = Depends(get_postgres_session)):
    f = db_session.query(UserFilter).filter(UserFilter.id == filter_id, UserFilter.user_id == current_user.id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Filter not found")
    db_session.delete(f)
    db_session.commit()
    return {"msg": "deleted"}

# Эндпоинты с фильтрацией
@app.get("/api/traffic", response_model=list[TrafficPoint])
async def get_traffic(
    start_time: str = None,
    end_time: str = None,
    src_ip: str = None,
    dst_ip: str = None,
    protocol: int = None,
    direction: int = None,
    host_ip: str = None,
    current_user: User = Depends(get_current_user)
):
    rows = await db.fetch_traffic_stats_filtered(start_time, end_time, src_ip, dst_ip, protocol, direction, host_ip)
    return [{"timestamp": row[0].isoformat(), "packets": row[1], "bytes": row[2]} for row in rows]

@app.get("/api/topology", response_model=list[TopologyLink])
async def get_topology(
    start_time: str = None,
    end_time: str = None,
    src_ip: str = None,
    dst_ip: str = None,
    protocol: int = None,
    direction: int = None,
    min_packets: int = 10,
    current_user: User = Depends(get_current_user)
):
    rows = await db.fetch_topology_filtered(start_time, end_time, src_ip, dst_ip, protocol, direction, min_packets)
    return [{"src": row[0], "dst": row[1], "packets": row[2], "bytes": row[3]} for row in rows]

@app.get("/api/hosts", response_model=list[HostInfo])
async def get_hosts(current_user: User = Depends(get_current_user)):
    rows = await db.fetch_hosts()
    # Преобразуем строку JSON interfaces обратно в dict
    result = []
    for row in rows:
        row_dict = dict(row)
        if isinstance(row_dict.get("interfaces"), str):
            row_dict["interfaces"] = json.loads(row_dict["interfaces"])
        result.append(row_dict)
    return result

@app.get("/api/alerts", response_model=list[AlertOut])
async def get_alerts(
    start_time: str = None,
    end_time: str = None,
    src_ip: str = None,
    dst_ip: str = None,
    protocol: int = None,
    direction: int = None,
    anomaly_type: str = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    rows = await db.fetch_alerts_filtered(start_time, end_time, src_ip, dst_ip, protocol, direction, anomaly_type, limit)
    return [dict(row) for row in rows]

@app.get("/api/host_traffic", response_model=list[TrafficPoint])
async def get_host_traffic(
    host_ip: str,
    start_time: str = None,
    end_time: str = None,
    current_user: User = Depends(get_current_user)
):
    rows = await db.fetch_host_traffic(host_ip, start_time, end_time)
    return [{"timestamp": row[0].isoformat(), "packets": row[1], "bytes": row[2]} for row in rows]

@app.get("/api/protocol_stats")
async def get_protocol_stats(
    start_time: str = None,
    end_time: str = None,
    current_user: User = Depends(get_current_user)
):
    rows = await db.fetch_protocol_stats(start_time, end_time)
    return [{"protocol": row[0], "packets": row[1], "bytes": row[2]} for row in rows]

@app.get("/api/port_stats")
async def get_port_stats(
    start_time: str = None,
    end_time: str = None,
    current_user: User = Depends(get_current_user)
):
    rows = await db.fetch_port_stats(start_time, end_time)
    return [{"port": row[0], "packets": row[1], "bytes": row[2]} for row in rows]

# ---- Статика ----
@app.get("/")
async def root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not built"}

assets_path = os.path.join(STATIC_DIR, "assets")
if os.path.exists(assets_path):
    app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("ws"):
        raise HTTPException(status_code=404, detail="Not found")
    file_path = os.path.join(STATIC_DIR, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend not built"}

# ---- WebSocket ----
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # В реальности можно проверить токен через query параметр
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ---- Старт/остановка ----
@app.on_event("startup")
async def startup():
    await db.connect()
    # Создаём админа в PostgreSQL
    pg = next(get_postgres_session())
    init_admin(pg)
    # Запускаем консьюмеры в фоновых задачах
    asyncio.create_task(consume_alerts())
    asyncio.create_task(consume_host_info())

@app.on_event("shutdown")
async def shutdown():
    await db.close()