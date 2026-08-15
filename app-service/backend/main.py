import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import jwt, JWTError

from data.mock_data import (
    SUMMARY, CHANNEL_USAGE, PROTOCOLS, NODES, INCIDENTS, EVENTS,
    NOTIFICATIONS, RULES, REPORTS, SETTINGS, USERS_DB,
    traffic_history, node_load_heatmap, node_load_buckets,
    traffic_history_for_node, traffic_by_node, now_iso,
)

SECRET_KEY = "dev-secret-change-me"
ALGORITHM = "HS256"

app = FastAPI(title="NetSentry Mock API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # на проде укажите конкретный домен фронта
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================================
#  ВАЖНО: все пути ниже полностью соответствуют src/api/endpoints.js
#  на фронтенде (HTTP_ENDPOINTS). Если меняете пути на фронте — меняйте
#  и здесь, чтобы контракт не расходился.
# =====================================================================


# ---------------------------- AUTH ----------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


def create_token(username: str) -> str:
    payload = {"sub": username, "exp": datetime.utcnow() + timedelta(hours=8)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Не авторизован")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username not in USERS_DB:
            raise HTTPException(status_code=401, detail="Пользователь не найден")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Токен недействителен")


def user_public(username: str) -> dict:
    u = USERS_DB[username]
    return {"username": username, "name": u["name"], "role": u["role"], "email": u["email"]}


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    user = USERS_DB.get(payload.username)
    if not user or user["password"] != payload.password:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    token = create_token(payload.username)
    return {"token": token, "user": user_public(payload.username)}


@app.get("/api/auth/me")
def me(user: str = Depends(get_current_user)):
    return user_public(user)


@app.post("/api/auth/logout")
def logout(user: str = Depends(get_current_user)):
    return {"status": "ok"}


@app.post("/api/auth/refresh")
def refresh_token(user: str = Depends(get_current_user)):
    return {"token": create_token(user)}


class ProfileUpdateRequest(BaseModel):
    email: Optional[str] = None
    newUsername: Optional[str] = None
    newPassword: Optional[str] = None
    currentPassword: Optional[str] = None


@app.patch("/api/auth/profile")
def update_profile(payload: ProfileUpdateRequest, user: str = Depends(get_current_user)):
    record = USERS_DB[user]

    if payload.newPassword or payload.newUsername:
        if not payload.currentPassword or payload.currentPassword != record["password"]:
            raise HTTPException(status_code=400, detail="Неверный текущий пароль")

    if payload.email:
        record["email"] = payload.email

    if payload.newPassword:
        record["password"] = payload.newPassword

    new_username = user
    if payload.newUsername and payload.newUsername != user:
        if payload.newUsername in USERS_DB:
            raise HTTPException(status_code=409, detail="Такой логин уже занят")
        USERS_DB[payload.newUsername] = record
        del USERS_DB[user]
        new_username = payload.newUsername

    token = create_token(new_username)
    return {"token": token, "user": user_public(new_username)}


# ---------------------------- OVERVIEW -------------------------------

@app.get("/api/overview/summary")
def overview_summary(user: str = Depends(get_current_user)):
    # немного «оживляем» метрики при каждом запросе, чтобы было видно обновление
    live = dict(SUMMARY)
    live["activeNodes"] = {
        "active": random.randint(120, 135),
        "total": SUMMARY["activeNodes"]["total"],
        "percent": SUMMARY["activeNodes"]["percent"],
    }
    return live


@app.get("/api/overview/traffic-history")
def overview_traffic_history(user: str = Depends(get_current_user)):
    return traffic_history()


@app.get("/api/overview/channel-usage")
def overview_channel_usage(user: str = Depends(get_current_user)):
    return CHANNEL_USAGE


@app.get("/api/overview/node-load")
def overview_node_load(user: str = Depends(get_current_user)):
    return node_load_buckets()


@app.get("/api/overview/traffic-by-node")
def overview_traffic_by_node(user: str = Depends(get_current_user)):
    return traffic_by_node()


@app.get("/api/overview/protocols")
def overview_protocols(user: str = Depends(get_current_user)):
    return PROTOCOLS


@app.get("/api/overview/topology")
def overview_topology(user: str = Depends(get_current_user)):
    return {"nodes": NODES}


@app.get("/api/overview/events/recent")
def overview_recent_events(user: str = Depends(get_current_user)):
    return EVENTS[:10]


@app.get("/api/overview/incidents")
def overview_incidents(user: str = Depends(get_current_user)):
    return INCIDENTS


# ---------------------------- TOPOLOGY -------------------------------

@app.get("/api/topology/graph")
def topology_graph(user: str = Depends(get_current_user)):
    return {"nodes": NODES}


# ---------------------------- NODES ----------------------------------

@app.get("/api/nodes")
def list_nodes(status: Optional[str] = None, group: Optional[str] = None,
               user: str = Depends(get_current_user)):
    result = NODES
    if status:
        result = [n for n in result if n["status"] == status]
    if group:
        result = [n for n in result if n["group"] == group]
    return result


@app.get("/api/nodes/{node_id}")
def get_node(node_id: str, user: str = Depends(get_current_user)):
    node = next((n for n in NODES if n["id"] == node_id), None)
    if not node:
        raise HTTPException(status_code=404, detail="Узел не найден")
    return node


@app.get("/api/nodes/{node_id}/traffic")
def get_node_traffic(node_id: str, user: str = Depends(get_current_user)):
    node = next((n for n in NODES if n["id"] == node_id), None)
    if not node:
        raise HTTPException(status_code=404, detail="Узел не найден")
    return {"nodeId": node_id, "label": node["label"], "history": traffic_history_for_node(node_id)}


# ---------------------------- INCIDENTS -------------------------------

@app.get("/api/incidents")
def list_incidents(status: Optional[str] = None, level: Optional[str] = None,
                    user: str = Depends(get_current_user)):
    result = INCIDENTS
    if status:
        result = [i for i in result if i["status"] == status]
    if level:
        result = [i for i in result if i["level"] == level]
    return result


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str, user: str = Depends(get_current_user)):
    inc = next((i for i in INCIDENTS if i["id"] == incident_id), None)
    if not inc:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    return inc


@app.get("/api/incidents/{incident_id}/timeline")
def get_incident_timeline(incident_id: str, user: str = Depends(get_current_user)):
    inc = next((i for i in INCIDENTS if i["id"] == incident_id), None)
    if not inc:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    return inc.get("timeline", [])


@app.get("/api/incidents/{incident_id}/related-events")
def get_incident_related_events(incident_id: str, user: str = Depends(get_current_user)):
    return EVENTS[:5]


@app.patch("/api/incidents/{incident_id}")
@app.put("/api/incidents/{incident_id}")
def update_incident(incident_id: str, payload: dict, user: str = Depends(get_current_user)):
    inc = next((i for i in INCIDENTS if i["id"] == incident_id), None)
    if not inc:
        raise HTTPException(status_code=404, detail="Инцидент не найден")
    inc.update(payload)
    return inc


# ---------------------------- EVENTS ----------------------------------

@app.get("/api/events")
def list_events(limit: int = 50, level: Optional[str] = None,
                 user: str = Depends(get_current_user)):
    result = EVENTS
    if level:
        result = [e for e in result if e["level"] == level]
    return result[:limit]


# ---------------------------- TRAFFIC ---------------------------------

@app.get("/api/traffic/stats")
def traffic_stats(user: str = Depends(get_current_user)):
    return {"total": SUMMARY["totalTraffic"], "history": traffic_history()}


@app.get("/api/traffic/channels")
def traffic_channels(user: str = Depends(get_current_user)):
    return CHANNEL_USAGE


# ---------------------------- RULES -----------------------------------

@app.get("/api/rules")
def list_rules(user: str = Depends(get_current_user)):
    return RULES


@app.get("/api/rules/{rule_id}")
def get_rule(rule_id: int, user: str = Depends(get_current_user)):
    rule = next((r for r in RULES if r["id"] == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    return rule


@app.post("/api/rules")
def create_rule(payload: dict, user: str = Depends(get_current_user)):
    new_id = max([r["id"] for r in RULES], default=0) + 1
    rule = {"id": new_id, **payload}
    RULES.append(rule)
    return rule


@app.put("/api/rules/{rule_id}")
def update_rule(rule_id: int, payload: dict, user: str = Depends(get_current_user)):
    rule = next((r for r in RULES if r["id"] == rule_id), None)
    if not rule:
        raise HTTPException(status_code=404, detail="Правило не найдено")
    rule.update(payload)
    return rule


@app.delete("/api/rules/{rule_id}")
def delete_rule(rule_id: int, user: str = Depends(get_current_user)):
    global RULES
    RULES[:] = [r for r in RULES if r["id"] != rule_id]
    return {"status": "deleted"}


# ---------------------------- REPORTS ----------------------------------

@app.get("/api/reports")
def list_reports(user: str = Depends(get_current_user)):
    return REPORTS


@app.post("/api/reports/generate")
def generate_report(payload: dict, user: str = Depends(get_current_user)):
    new_id = max([r["id"] for r in REPORTS], default=0) + 1
    report = {"id": new_id, "date": datetime.utcnow().strftime("%d.%m.%Y"), **payload}
    REPORTS.append(report)
    return report


@app.get("/api/reports/{report_id}/download")
def download_report(report_id: int, user: str = Depends(get_current_user)):
    report = next((r for r in REPORTS if r["id"] == report_id), None)
    if not report:
        raise HTTPException(status_code=404, detail="Отчёт не найден")
    # Заглушка — подставьте свою генерацию файла/ссылку на файловое хранилище
    return {"url": f"/files/reports/{report_id}.{report.get('format', 'pdf').lower()}"}


# ---------------------------- NOTIFICATIONS -----------------------------

@app.get("/api/notifications")
def list_notifications(user: str = Depends(get_current_user)):
    return NOTIFICATIONS


@app.patch("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, user: str = Depends(get_current_user)):
    n = next((x for x in NOTIFICATIONS if x["id"] == notification_id), None)
    if not n:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    n["read"] = True
    return n


# ---------------------------- SETTINGS ----------------------------------

@app.get("/api/settings")
def get_settings(user: str = Depends(get_current_user)):
    return SETTINGS


@app.put("/api/settings")
def update_settings(payload: dict, user: str = Depends(get_current_user)):
    SETTINGS.update(payload)
    return SETTINGS


@app.get("/api/settings/clusters")
def get_clusters(user: str = Depends(get_current_user)):
    return SETTINGS["clusters"]


@app.get("/api/settings/users")
def get_users(user: str = Depends(get_current_user)):
    return [user_public(u) for u in USERS_DB.keys()]


# ================================ WEBSOCKET =================================

class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, message: dict):
        for ws in list(self.active):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    try:
        if token:
            jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        await websocket.close(code=4401)
        return

    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            # Здесь можно обрабатывать msg.get("type") == "auth" и другие
            # служебные сообщения, которые присылает wsClient.js
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Фоновая рассылка обновлений — эмуляция real-time событий.
# Типы сообщений (`type`) соответствуют WS_CHANNELS во фронтенде.
async def background_broadcaster():
    while True:
        await asyncio.sleep(5)

        # metrics.update
        await manager.broadcast({
            "type": "metrics.update",
            "payload": {
                "totalTraffic": SUMMARY["totalTraffic"],
                "activeNodes": {
                    "active": random.randint(120, 135),
                    "total": SUMMARY["activeNodes"]["total"],
                },
                "suspiciousActivity": {"value": random.randint(15, 30)},
                "criticalIncidents": {"value": random.randint(4, 9)},
            },
        })

        # events.new (иногда)
        if random.random() < 0.4:
            new_event = {
                "time": datetime.utcnow().strftime("%H:%M:%S"),
                "level": random.choice(["info", "warning", "critical"]),
                "text": random.choice([
                    "Сетевое соединение", "Аномальный трафик",
                    "Попытка доступа к ресурсу", "Изменение конфигурации",
                ]),
                "source": f"10.10.{random.randint(1,9)}.{random.randint(1,254)}",
            }
            EVENTS.insert(0, new_event)
            await manager.broadcast({"type": "events.new", "payload": new_event})

        # notifications.new (реже)
        if random.random() < 0.2:
            new_id = max([n["id"] for n in NOTIFICATIONS], default=0) + 1
            notif = {
                "id": new_id,
                "level": random.choice(["warning", "critical", "info"]),
                "text": "Новое событие безопасности требует внимания",
                "time": datetime.utcnow().strftime("%H:%M:%S"),
                "read": False,
            }
            NOTIFICATIONS.insert(0, notif)
            await manager.broadcast({"type": "notifications.new", "payload": notif})


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_broadcaster())


@app.get("/api/health")
def health():
    return {"status": "ok", "time": now_iso()}
