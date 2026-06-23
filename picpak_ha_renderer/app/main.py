from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import paho.mqtt.publish as mqtt_publish
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app.open_meteo import fetch_open_meteo_card
from renderer import WeatherCardData, render_to_artifact, render_weather_card
from renderer.pack import write_artifact

APP_TITLE = "PicPak Home Assistant Renderer"
DATA_ROOT = Path(os.environ.get("PICPAK_DATA_DIR", "/data/picpak")).resolve()
PAYLOAD_DIR = DATA_ROOT / "payloads"
SETTINGS_PATH = DATA_ROOT / "settings.json"

app = FastAPI(title=APP_TITLE)


def _load_settings() -> Dict[str, Any]:
    if SETTINGS_PATH.exists():
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    return {
        "mqtt_host": "homeassistant.local",
        "mqtt_port": 1883,
        "mqtt_username": "",
        "mqtt_password": "",
        "library_id": "replace-with-library-id",
        "topic_base": "picpak/replace-with-library-id",
        "public_base_url": "http://homeassistant.local:8099",
        "expires_minutes": 15,
    }


def _save_settings(settings: Dict[str, Any]) -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def _html_page(body: str) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{APP_TITLE}</title>
  <style>
    :root {{
      --ink: #121412;
      --paper: #f5f3e8;
      --panel: #ffffff;
      --muted: #5a554d;
      --yellow: #cab03e;
      --red: #a43f37;
      --line: #d6d0bc;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: var(--paper);
    }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 24px;
      background: var(--panel);
      border-bottom: 4px solid var(--yellow);
    }}
    h1 {{ margin: 0; font-size: 22px; }}
    main {{
      display: grid;
      grid-template-columns: minmax(300px, 420px) minmax(340px, 1fr);
      gap: 18px;
      padding: 18px;
      max-width: 1120px;
      margin: 0 auto;
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 16px;
    }}
    h2 {{ margin: 0 0 14px; font-size: 18px; }}
    label {{ display: block; margin: 10px 0 5px; font-weight: 700; font-size: 13px; }}
    input {{
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 4px;
      padding: 8px 10px;
      font-size: 14px;
    }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    button {{
      border: 0;
      border-radius: 4px;
      background: var(--ink);
      color: white;
      font-weight: 700;
      padding: 10px 14px;
      margin-top: 14px;
      cursor: pointer;
    }}
    .secondary {{ background: var(--yellow); color: var(--ink); }}
    .danger {{ background: var(--red); color: white; }}
    .preview {{
      width: 100%;
      max-width: 520px;
      image-rendering: pixelated;
      border: 4px solid var(--ink);
      background: #cdcfc6;
    }}
    .meta {{
      background: #f7f4e9;
      border-left: 4px solid var(--yellow);
      padding: 10px 12px;
      font-family: Consolas, monospace;
      font-size: 13px;
      overflow-wrap: anywhere;
    }}
    @media (max-width: 820px) {{
      main {{ grid-template-columns: 1fr; }}
      header {{ align-items: flex-start; flex-direction: column; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>{APP_TITLE}</h1>
    <div>Prototype renderer and MQTT job publisher</div>
  </header>
  <main>{body}</main>
</body>
</html>"""
    )


def _render_weather_files(form: Dict[str, str]) -> Dict[str, Any]:
    details = (
        (form.get("detail1_label", "High"), form.get("detail1_value", f"{form.get('high', '26')}{form.get('unit', 'C')}")),
        (form.get("detail2_label", "Low"), form.get("detail2_value", f"{form.get('low', '16')}{form.get('unit', 'C')}")),
        (form.get("detail3_label", "Hum"), form.get("detail3_value", form.get("humidity", "--"))),
        (form.get("detail4_label", "UV"), form.get("detail4_value", form.get("uv_index", "--"))),
        (form.get("detail5_label", "Rain"), form.get("detail5_value", form.get("rain", "10%"))),
        (form.get("detail6_label", "Wind"), form.get("detail6_value", form.get("wind", "9 km/h"))),
    )
    data = WeatherCardData(
        location=form.get("location", "Home"),
        condition=form.get("condition", "Sunny"),
        temperature=form.get("temperature", "22"),
        unit=form.get("unit", "C"),
        high=form.get("high", "26"),
        low=form.get("low", "16"),
        rain=form.get("rain", "10%"),
        wind=form.get("wind", "9 km/h"),
        updated=form.get("updated", "Now"),
        alert=form.get("alert", ""),
        source_entity_id=form.get("source_entity_id", "weather.home"),
        humidity=form.get("humidity", ""),
        uv_index=form.get("uv_index", ""),
        feels_like=form.get("feels_like", ""),
        pressure=form.get("pressure", ""),
        details=details,
    )
    image = render_weather_card(data)
    artifact = render_to_artifact(image, "weather_current", [data.source_entity_id])
    stem = "weather-current"
    paths = write_artifact(artifact, PAYLOAD_DIR, stem)
    return {"data": data, "artifact": artifact, "paths": paths, "stem": stem}


def _latest_or_default_payload() -> Dict[str, Any]:
    metadata_path = PAYLOAD_DIR / "weather-current.json"
    ppbin_path = PAYLOAD_DIR / "weather-current.ppbin"
    if metadata_path.exists() and ppbin_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        packed = ppbin_path.read_bytes()
        return {
            "content_id": metadata["content_id"],
            "crc32": metadata["crc32"],
            "length": len(packed),
        }
    result = _render_weather_files({})
    artifact = result["artifact"]
    return {
        "content_id": artifact.content_id,
        "crc32": artifact.crc32,
        "length": len(artifact.packed),
    }


def _form_body(settings: Dict[str, Any], result: Dict[str, Any] | None = None) -> str:
    artifact = result["artifact"] if result else None
    preview_html = ""
    if artifact:
        preview_html = f"""
        <h2>Latest Preview</h2>
        <img class="preview" src="/payloads/weather-current.preview.png?crc={artifact.crc32}" alt="PicPak display preview">
        <div class="meta">
          content_id={artifact.content_id}<br>
          length={len(artifact.packed)}<br>
          crc32={artifact.crc32}
        </div>
        """
    return f"""
    <section>
      <h2>Weather Card</h2>
      <form method="post" action="/render/weather">
        <label>Location</label><input name="location" value="Home">
        <div class="row">
          <div><label>Temperature</label><input name="temperature" value="22"></div>
          <div><label>Unit</label><input name="unit" value="C"></div>
        </div>
        <label>Condition</label><input name="condition" value="Sunny">
        <div class="row">
          <div><label>High</label><input name="high" value="26"></div>
          <div><label>Low</label><input name="low" value="16"></div>
        </div>
        <div class="row">
          <div><label>Rain</label><input name="rain" value="10%"></div>
          <div><label>Wind</label><input name="wind" value="9 km/h"></div>
        </div>
        <label>Updated</label><input name="updated" value="Now">
        <label>Alert text</label><input name="alert" value="">
        <label>Source entity ID</label><input name="source_entity_id" value="weather.home">
        <div class="row">
          <div><label>Detail 1 label</label><input name="detail1_label" value="High"></div>
          <div><label>Detail 1 value</label><input name="detail1_value" value="26C"></div>
        </div>
        <div class="row">
          <div><label>Detail 2 label</label><input name="detail2_label" value="Low"></div>
          <div><label>Detail 2 value</label><input name="detail2_value" value="16C"></div>
        </div>
        <div class="row">
          <div><label>Detail 3 label</label><input name="detail3_label" value="Hum"></div>
          <div><label>Detail 3 value</label><input name="detail3_value" value="61%"></div>
        </div>
        <div class="row">
          <div><label>Detail 4 label</label><input name="detail4_label" value="UV"></div>
          <div><label>Detail 4 value</label><input name="detail4_value" value="7"></div>
        </div>
        <div class="row">
          <div><label>Detail 5 label</label><input name="detail5_label" value="Rain"></div>
          <div><label>Detail 5 value</label><input name="detail5_value" value="10%"></div>
        </div>
        <div class="row">
          <div><label>Detail 6 label</label><input name="detail6_label" value="Wind"></div>
          <div><label>Detail 6 value</label><input name="detail6_value" value="9km/h"></div>
        </div>
        <button class="secondary" type="submit">Render preview</button>
      </form>
      <h2 style="margin-top:20px">Open-Meteo Test</h2>
      <form method="post" action="/fetch/open-meteo">
        <label>Location label</label><input name="location" value="Home">
        <div class="row">
          <div><label>Latitude</label><input name="latitude" value="-33.8688"></div>
          <div><label>Longitude</label><input name="longitude" value="151.2093"></div>
        </div>
        <button class="secondary" type="submit">Fetch free weather</button>
      </form>
    </section>
    <section>
      {preview_html or '<h2>Latest Preview</h2><div class="meta">Render a card to create preview and payload files.</div>'}
      <h2>MQTT Job</h2>
      <form method="post" action="/publish/weather">
        <label>MQTT host</label><input name="mqtt_host" value="{settings.get('mqtt_host', '')}">
        <div class="row">
          <div><label>MQTT port</label><input name="mqtt_port" value="{settings.get('mqtt_port', 1883)}"></div>
          <div><label>Expiry minutes</label><input name="expires_minutes" value="{settings.get('expires_minutes', 15)}"></div>
        </div>
        <label>MQTT username</label><input name="mqtt_username" value="{settings.get('mqtt_username', '')}">
        <label>MQTT password</label><input name="mqtt_password" type="password" value="{settings.get('mqtt_password', '')}">
        <label>Library ID</label><input name="library_id" value="{settings.get('library_id', '')}">
        <label>Topic base</label><input name="topic_base" value="{settings.get('topic_base', '')}">
        <label>Public base URL reachable by frame</label><input name="public_base_url" value="{settings.get('public_base_url', '')}">
        <button type="submit">Render and publish job</button>
      </form>
    </section>
    """


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    return _html_page(_form_body(_load_settings()))


@app.post("/render/weather")
def render_weather(
    location: str = Form("Home"),
    condition: str = Form("Sunny"),
    temperature: str = Form("22"),
    unit: str = Form("C"),
    high: str = Form("26"),
    low: str = Form("16"),
    rain: str = Form("10%"),
    wind: str = Form("9 km/h"),
    updated: str = Form("Now"),
    alert: str = Form(""),
    source_entity_id: str = Form("weather.home"),
    detail1_label: str = Form("High"),
    detail1_value: str = Form("26C"),
    detail2_label: str = Form("Low"),
    detail2_value: str = Form("16C"),
    detail3_label: str = Form("Hum"),
    detail3_value: str = Form("61%"),
    detail4_label: str = Form("UV"),
    detail4_value: str = Form("7"),
    detail5_label: str = Form("Rain"),
    detail5_value: str = Form("10%"),
    detail6_label: str = Form("Wind"),
    detail6_value: str = Form("9km/h"),
) -> HTMLResponse:
    result = _render_weather_files(locals())
    return _html_page(_form_body(_load_settings(), result))


@app.post("/fetch/open-meteo")
def fetch_open_meteo(
    location: str = Form("Home"),
    latitude: str = Form(...),
    longitude: str = Form(...),
) -> HTMLResponse:
    data = fetch_open_meteo_card(latitude=latitude, longitude=longitude, location=location)
    image = render_weather_card(data)
    artifact = render_to_artifact(image, "weather_current", [data.source_entity_id])
    write_artifact(artifact, PAYLOAD_DIR, "weather-current")
    return _html_page(_form_body(_load_settings(), {"data": data, "artifact": artifact, "paths": {}, "stem": "weather-current"}))


@app.post("/publish/weather")
def publish_weather(
    mqtt_host: str = Form(...),
    mqtt_port: int = Form(1883),
    mqtt_username: str = Form(""),
    mqtt_password: str = Form(""),
    library_id: str = Form(...),
    topic_base: str = Form(...),
    public_base_url: str = Form(...),
    expires_minutes: int = Form(15),
) -> RedirectResponse:
    settings = {
        "mqtt_host": mqtt_host,
        "mqtt_port": mqtt_port,
        "mqtt_username": mqtt_username,
        "mqtt_password": mqtt_password,
        "library_id": library_id,
        "topic_base": topic_base.rstrip("/"),
        "public_base_url": public_base_url.rstrip("/"),
        "expires_minutes": expires_minutes,
    }
    _save_settings(settings)
    payload = _latest_or_default_payload()
    payload_url = f"{settings['public_base_url']}/payloads/weather-current.ppbin"
    now = datetime.now(timezone.utc)
    command_id = f"ha-weather-{now.strftime('%Y%m%d-%H%M%S')}-{payload['crc32'].lower()}"
    job = {
        "command_id": command_id,
        "job_type": "content_card",
        "content_id": payload["content_id"],
        "source": "home_assistant",
        "template": "weather_current",
        "slot": "auto",
        "display": True,
        "payload_url": payload_url,
        "length": payload["length"],
        "crc32": payload["crc32"],
        "expires_at": (now + timedelta(minutes=expires_minutes)).isoformat(),
        "fallback_slot": "random",
    }
    auth = None
    if mqtt_username:
        auth = {"username": mqtt_username, "password": mqtt_password}
    try:
        mqtt_publish.single(
            f"{settings['topic_base']}/cmd/job",
            payload=json.dumps(job),
            hostname=mqtt_host,
            port=mqtt_port,
            auth=auth,
            qos=1,
            retain=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MQTT publish failed: {exc}") from exc
    (PAYLOAD_DIR / "last-job.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
    return RedirectResponse("/", status_code=303)


@app.get("/payloads/{filename}")
def payload_file(filename: str) -> FileResponse:
    path = (PAYLOAD_DIR / filename).resolve()
    if not str(path).startswith(str(PAYLOAD_DIR.resolve())) or not path.exists():
        raise HTTPException(status_code=404, detail="Payload not found")
    return FileResponse(path)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}
