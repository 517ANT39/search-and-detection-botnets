import asyncio
import os
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from sqlalchemy.orm import Session

from .config import DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD
from .db import db, init_postgres, get_postgres_session, PostgresSessionLocal
from .schemas import User, UserFilter
from .auth import (
    authenticate_user, create_access_token,
    get_current_user, get_password_hash,
)
from .models import FilterCreate, FilterOut, UserOut, FilterData
from .consumers import consume_alerts
from .utils import manager

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="Traffic Anomaly Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


# =====================================================================
#  Startup / shutdown
# =====================================================================

def _ensure_admin():
    s = PostgresSessionLocal()
    try:
        u = s.query(User).filter(User.username == DEFAULT_ADMIN_USERNAME).first()
        if not u:
            s.add(User(
                username=DEFAULT_ADMIN_USERNAME,
                hashed_password=get_password_hash(DEFAULT_ADMIN_PASSWORD),
            ))
            s.commit()
            log.info(f"Создан админ '{DEFAULT_ADMIN_USERNAME}'")
    finally:
        s.close()


@app.on_event("startup")
async def startup():
    init_postgres()
    _ensure_admin()
    await db.connect()
    asyncio.create_task(consume_alerts())


@app.on_event("shutdown")
async def shutdown():
    await db.close()


# =====================================================================
#  Auth
# =====================================================================

@app.post("/api/token")
async def login(form: OAuth2PasswordRequestForm = Depends(),
                db_sess: Session = Depends(get_postgres_session)):
    user = authenticate_user(db_sess, form.username, form.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/api/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)):
    return current


@app.post("/api/register", response_model=UserOut)
async def register(username: str, password: str,
                   db_sess: Session = Depends(get_postgres_session)):
    if db_sess.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    user = User(username=username, hashed_password=get_password_hash(password))
    db_sess.add(user)
    db_sess.commit()
    db_sess.refresh(user)
    return user


# =====================================================================
#  User filters (CRUD)
# =====================================================================

@app.get("/api/filters", response_model=list[FilterOut])
async def list_filters(current: User = Depends(get_current_user),
                       db_sess: Session = Depends(get_postgres_session)):
    return db_sess.query(UserFilter).filter(UserFilter.user_id == current.id).all()


@app.post("/api/filters", response_model=FilterOut)
async def create_filter(body: FilterCreate,
                        current: User = Depends(get_current_user),
                        db_sess: Session = Depends(get_postgres_session)):
    f = UserFilter(
        user_id=current.id,
        name=body.name,
        filter_data=body.filter_data.dict(),
    )
    db_sess.add(f)
    db_sess.commit()
    db_sess.refresh(f)
    return f


@app.get("/api/filters/{fid}", response_model=FilterOut)
async def get_filter(fid: int,
                     current: User = Depends(get_current_user),
                     db_sess: Session = Depends(get_postgres_session)):
    f = db_sess.query(UserFilter).filter(
        UserFilter.id == fid, UserFilter.user_id == current.id
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="Filter not found")
    return f


@app.put("/api/filters/{fid}", response_model=FilterOut)
async def update_filter(fid: int, body: FilterCreate,
                        current: User = Depends(get_current_user),
                        db_sess: Session = Depends(get_postgres_session)):
    f = db_sess.query(UserFilter).filter(
        UserFilter.id == fid, UserFilter.user_id == current.id
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="Filter not found")
    f.name = body.name
    f.filter_data = body.filter_data.dict()
    db_sess.commit()
    db_sess.refresh(f)
    return f


@app.delete("/api/filters/{fid}")
async def delete_filter(fid: int,
                        current: User = Depends(get_current_user),
                        db_sess: Session = Depends(get_postgres_session)):
    f = db_sess.query(UserFilter).filter(
        UserFilter.id == fid, UserFilter.user_id == current.id
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="Filter not found")
    db_sess.delete(f)
    db_sess.commit()
    return {"status": "deleted", "id": fid}


# =====================================================================
#  Traffic endpoints
# =====================================================================

@app.get("/api/traffic/timeline")
async def traffic_timeline(
    minutes: int = 60,
    start_time: str | None = None,
    end_time: str | None = None,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    protocol: int | None = None,
    direction: int | None = None,
    host_ip: str | None = None,
    current: User = Depends(get_current_user),
):
    rows = await db.fetch_traffic_timeline(
        minutes, start_time, end_time, src_ip, dst_ip, protocol, direction, host_ip
    )
    return [
        {"timestamp": r[0].isoformat(), "packets": r[1], "bytes": r[2]}
        for r in rows
    ]


@app.get("/api/traffic/by_protocol")
async def traffic_by_protocol(minutes: int = 60,
                              current: User = Depends(get_current_user)):
    rows = await db.fetch_traffic_by_protocol(minutes)
    return [{"protocol": r[0], "packets": r[1], "bytes": r[2]} for r in rows]


@app.get("/api/traffic/by_port")
async def traffic_by_port(minutes: int = 60, port_type: str = "dst",
                          current: User = Depends(get_current_user)):
    rows = await db.fetch_traffic_by_port(minutes, port_type)
    return [{"port": r[0], "packets": r[1], "bytes": r[2]} for r in rows]


@app.get("/api/traffic/by_direction")
async def traffic_by_direction(minutes: int = 60,
                               current: User = Depends(get_current_user)):
    rows = await db.fetch_traffic_by_direction(minutes)
    return [{"direction": r[0], "packets": r[1], "bytes": r[2]} for r in rows]


@app.get("/api/traffic/by_subnet")
async def traffic_by_subnet(minutes: int = 60, limit: int = 30,
                            current: User = Depends(get_current_user)):
    rows = await db.fetch_traffic_by_subnet(minutes, limit)
    return [
        {"src_subnet": r[0], "dst_subnet": r[1],
         "packets": r[2], "bytes": r[3]}
        for r in rows
    ]


@app.get("/api/traffic/topology")
async def traffic_topology(minutes: int = 60, min_packets: int = 10,
                           limit: int = 200,
                           current: User = Depends(get_current_user)):
    rows = await db.fetch_topology(minutes, min_packets, limit)
    return [
        {"src": r[0], "dst": r[1], "protocol": r[2],
         "packets": r[3], "bytes": r[4]}
        for r in rows
    ]


@app.get("/api/traffic/top_sources")
async def traffic_top_sources(minutes: int = 60, limit: int = 20,
                              current: User = Depends(get_current_user)):
    rows = await db.fetch_top_sources(minutes, limit)
    return [{"ip": r[0], "packets": r[1], "bytes": r[2]} for r in rows]


@app.get("/api/traffic/top_targets")
async def traffic_top_targets(minutes: int = 60, limit: int = 20,
                              current: User = Depends(get_current_user)):
    rows = await db.fetch_top_targets(minutes, limit)
    return [{"ip": r[0], "packets": r[1], "bytes": r[2]} for r in rows]


# =====================================================================
#  Hosts
# =====================================================================

@app.get("/api/hosts")
async def hosts(current: User = Depends(get_current_user)):
    rows = await db.fetch_hosts()
    return [dict(r) for r in rows]


@app.get("/api/hosts/status")
async def hosts_status(current: User = Depends(get_current_user)):
    rows = await db.fetch_host_status()
    return [dict(r) for r in rows]


@app.get("/api/hosts/{host_ip}/traffic")
async def host_traffic(host_ip: str, minutes: int = 60,
                       current: User = Depends(get_current_user)):
    rows = await db.fetch_host_traffic(host_ip, minutes)
    return [
        {"timestamp": r[0].isoformat(),
         "packets_sent": r[1], "bytes_sent": r[2],
         "packets_recv": r[3], "bytes_recv": r[4]}
        for r in rows
    ]


# =====================================================================
#  Alerts
# =====================================================================

@app.get("/api/alerts")
async def alerts(
    limit: int = 200,
    minutes: int | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    severity: str | None = None,
    detector: str | None = None,
    view: str | None = None,
    src_ip: str | None = None,
    dst_ip: str | None = None,
    protocol: int | None = None,
    current: User = Depends(get_current_user),
):
    rows = await db.fetch_alerts(
        limit, minutes, start_time, end_time,
        severity, detector, view, src_ip, dst_ip, protocol,
    )
    return [dict(r) for r in rows]


@app.get("/api/alerts/timeline")
async def alerts_timeline(minutes: int = 60,
                          current: User = Depends(get_current_user)):
    rows = await db.fetch_alert_timeline(minutes)
    return [
        {"timestamp": r[0].isoformat(),
         "total": r[1], "critical": r[2], "warning": r[3], "info": r[4]}
        for r in rows
    ]


@app.get("/api/alerts/by_view")
async def alerts_by_view(minutes: int = 60,
                         current: User = Depends(get_current_user)):
    rows = await db.fetch_alert_by_view(minutes)
    return [{"view": r[0], "count": r[1]} for r in rows]


@app.get("/api/alerts/by_severity")
async def alerts_by_severity(minutes: int = 60,
                             current: User = Depends(get_current_user)):
    rows = await db.fetch_alert_by_severity(minutes)
    return [{"severity": r[0], "count": r[1]} for r in rows]


@app.get("/api/alerts/top_targets")
async def alerts_top_targets(minutes: int = 60, limit: int = 10,
                             current: User = Depends(get_current_user)):
    rows = await db.fetch_top_alert_targets(minutes, limit)
    return [{"ip": r[0], "count": r[1], "max_z": r[2]} for r in rows]


@app.get("/api/alerts/top_sources")
async def alerts_top_sources(minutes: int = 60, limit: int = 10,
                             current: User = Depends(get_current_user)):
    rows = await db.fetch_top_alert_sources(minutes, limit)
    return [{"ip": r[0], "count": r[1], "max_z": r[2]} for r in rows]


# =====================================================================
#  WebSocket — real-time alerts
# =====================================================================

@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()   # ping/pong keepalive
    except WebSocketDisconnect:
        manager.disconnect(websocket)
@app.websocket("/ws")
async def ws_alias(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# =====================================================================
#  Frontend (SPA)
# =====================================================================

@app.get("/")
async def root():
    idx = os.path.join(STATIC_DIR, "index.html")
    return FileResponse(idx) if os.path.exists(idx) else {"msg": "no frontend"}


assets = os.path.join(STATIC_DIR, "assets")
if os.path.exists(assets):
    app.mount("/assets", StaticFiles(directory=assets), name="assets")


@app.get("/{full_path:path}")
async def spa(full_path: str):
    if full_path.startswith(("api/", "ws/")):
        raise HTTPException(status_code=404, detail="Not found")
    p = os.path.join(STATIC_DIR, full_path)
    if os.path.isfile(p):
        return FileResponse(p)
    idx = os.path.join(STATIC_DIR, "index.html")
    return FileResponse(idx) if os.path.exists(idx) else {"msg": "no frontend"}