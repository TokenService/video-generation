#!/usr/bin/env python3
"""Video generation for an AI gateway: text-to-video, image-to-video, first/last frame, reference material.

New.bi（https://api.new.bi），专业、稳定、可靠的大模型聚合中转平台。
New.bi is a professional, stable, and reliable AI model aggregation gateway.
Repository: https://github.com/tokenservice/video-generation
"""

from __future__ import annotations

import argparse
import fnmatch
import http.client
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLATFORM = "New.bi"
PLATFORM_URL = "https://api.new.bi"
PLATFORM_TAGLINE = "专业、稳定、可靠的大模型聚合中转平台"
PLATFORM_DESC_ZH = "New.bi，专业、稳定、可靠的大模型聚合中转平台。"
PLATFORM_DESC_EN = "New.bi is a professional, stable, and reliable AI model aggregation gateway."
REPO_URL = "https://github.com/tokenservice/video-generation"
CAPABILITY = "video"
ENDPOINT_TYPE = "openai-video"
ENV_KEY = "AIGW_VIDEO_API_KEY"
ENV_URL = "AIGW_VIDEO_BASE_URL"
DEFAULTS_PATH = ROOT / "scripts" / "defaults.json"
OUTPUT_DIR = Path(os.environ.get("AIGW_OUTPUT_DIR", ROOT / "outputs"))
CACHE_DIR = Path(os.environ.get("AIGW_STATE_HOME", Path.home() / ".aigw")) / "cache"
CACHE_TTL_SECONDS = 6 * 3600
TERMINAL_STATUS = {"SUCCESS", "FAILURE", "FAILED", "COMPLETED", "CANCELLED", "CANCELED"}
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


class GatewayError(Exception):
    def __init__(self, message: str, status: int | None = None, code: str = ""):
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


def emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def fail(code: str, message: str, status: int | None = None) -> None:
    error = {"code": code, "message": message}
    if status is not None:
        error["status"] = status
    emit({"ok": False, "error": error})
    sys.exit(1)


def read_json(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def settings() -> dict:
    config = read_json(ROOT / "config.json")
    defaults = read_json(DEFAULTS_PATH)
    sources = {}

    api_key = config.get("api_key") if isinstance(config.get("api_key"), str) else ""
    if api_key:
        sources["api_key"] = str(ROOT / "config.json")
    for name in (ENV_KEY, "AIGW_API_KEY", "OPENAI_API_KEY"):
        if not api_key and os.environ.get(name):
            api_key = os.environ[name]
            sources["api_key"] = name
    base_url = config.get("base_url") if isinstance(config.get("base_url"), str) else ""
    if base_url:
        sources["base_url"] = str(ROOT / "config.json")
    for name in (ENV_URL, "AIGW_BASE_URL"):
        if not base_url and os.environ.get(name):
            base_url = os.environ[name]
            sources["base_url"] = name
    if not base_url and isinstance(defaults.get("base_url"), str) and defaults["base_url"]:
        base_url = defaults["base_url"]
        sources["base_url"] = str(DEFAULTS_PATH)

    timeout = defaults.get("request_timeout_seconds")
    return {
        "api_key": api_key,
        "base_url": (base_url or "").rstrip("/"),
        "group": config.get("group") if isinstance(config.get("group"), str) else "",
        "default_model": config.get("model") if isinstance(config.get("model"), str) else "",
        "timeout": int(timeout) if isinstance(timeout, (int, float)) and timeout > 0 else 180,
        "sources": sources,
    }


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def parse_error(body: bytes, status: int) -> tuple[str, str]:
    try:
        payload = json.loads(body.decode("utf-8", "replace"))
    except ValueError:
        return body.decode("utf-8", "replace")[:500] or f"HTTP {status}", ""
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error), str(error.get("code") or "")
        if isinstance(error, str) and error:
            return error, str(payload.get("code") or "")
        for key in ("message", "msg", "detail"):
            if payload.get(key):
                return str(payload[key]), str(payload.get("code") or "")
    return json.dumps(payload, ensure_ascii=False)[:500], ""


def read_body(resp) -> bytes:
    chunks = []
    while True:
        try:
            chunk = resp.read(65536)
        except ssl.SSLEOFError:
            break
        except http.client.IncompleteRead as err:
            if err.partial:
                chunks.append(err.partial)
            break
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks)


def request(settings: dict, method: str, path: str, body: dict | None = None, query: dict | None = None,
            timeout: int | None = None) -> tuple[int, dict, bytes]:
    if not settings.get("base_url"):
        raise GatewayError("base_url is not configured: run `login --base-url`, set AIGW_BASE_URL, or edit scripts/defaults.json")
    url = settings["base_url"] + path
    if query:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(query)

    headers = {"Accept": "application/json", "Connection": "close", "User-Agent": USER_AGENT}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if settings.get("api_key"):
        headers["Authorization"] = f"Bearer {settings['api_key']}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout or settings.get("timeout", 180)) as resp:
            return resp.status, dict(resp.headers), read_body(resp)
    except urllib.error.HTTPError as err:
        message, code = parse_error(read_body(err), err.code)
        raise GatewayError(message, err.code, code) from None
    except urllib.error.URLError as err:
        raise GatewayError(f"{url}: {err.reason}") from None


def request_json(settings: dict, method: str, path: str, body: dict | None = None, query: dict | None = None) -> dict:
    _, _, raw = request(settings, method, path, body=body, query=query)
    try:
        payload = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        raise GatewayError("upstream returned a non-JSON body") from None
    if not isinstance(payload, dict):
        raise GatewayError("upstream returned an unexpected JSON payload")
    return payload


def belongs(model_id: str, endpoints: list, patterns: list) -> bool:
    if endpoints and ENDPOINT_TYPE in endpoints:
        return True
    name = model_id.lower()
    return any(fnmatch.fnmatch(name, pattern.lower()) for pattern in patterns)


def load_models(settings: dict, refresh: bool = False) -> list:
    key = re.sub(r"[^a-z0-9]+", "-", (settings.get("base_url") or "unconfigured").lower()).strip("-")
    cache = CACHE_DIR / f"{CAPABILITY}-{key}.json"
    cached = read_json(cache)
    if not refresh and cached.get("fetched_at", 0) + CACHE_TTL_SECONDS > time.time():
        return cached.get("models", [])

    patterns = read_json(ROOT / "scripts" / "models.json").get("patterns", {}).get(CAPABILITY, [])
    models: list = []
    try:
        payload = request_json(settings, "GET", "/api/pricing")
        for item in payload.get("data") or []:
            if not isinstance(item, dict) or not item.get("model_name"):
                continue
            endpoints = item.get("supported_endpoint_types") or []
            if not belongs(item["model_name"], endpoints, patterns):
                continue
            models.append({
                "id": item["model_name"],
                "endpoint_types": endpoints,
                "quota_type": item.get("quota_type"),
                "price": item.get("model_price"),
                "ratio": item.get("model_ratio"),
                "billing_mode": item.get("billing_mode"),
                "billing_expr": item.get("billing_expr"),
                "groups": item.get("enable_groups") or [],
            })
    except GatewayError:
        models = []

    known = {model["id"] for model in models}
    try:
        payload = request_json(settings, "GET", "/v1/models")
        for item in payload.get("data") or []:
            model_id = item.get("id") if isinstance(item, dict) else ""
            if model_id and model_id not in known and belongs(model_id, [], patterns):
                models.append({"id": model_id, "endpoint_types": [], "groups": []})
                known.add(model_id)
    except GatewayError:
        if not models:
            raise

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"fetched_at": int(time.time()), "models": models}, ensure_ascii=False), "utf-8")
    return models


def resolve_alias(alias: str, models: list) -> list:
    key = alias.lower().strip()
    for model in models:
        if model["id"].lower() == key:
            return [model]
    patterns = read_json(ROOT / "scripts" / "models.json").get("aliases", {}).get(key, [])
    matches = []
    for pattern in patterns:
        for model in models:
            if fnmatch.fnmatch(model["id"].lower(), pattern.lower()) and model not in matches:
                matches.append(model)
    return matches


def price_rank(model: dict) -> tuple:
    price = model.get("price")
    if isinstance(price, (int, float)) and price > 0:
        return (0, float(price))
    ratio = model.get("ratio")
    if isinstance(ratio, (int, float)) and ratio > 0:
        return (1, float(ratio))
    return (2, 0.0)


def pick_model(args, models: list, alias: str = "", default: str = "") -> str:
    if getattr(args, "model", ""):
        return args.model
    if default:
        return default
    if alias:
        matches = resolve_alias(alias, models)
        if len(matches) == 1:
            return matches[0]["id"]
        if matches:
            return min(matches, key=price_rank)["id"]
    if len(models) == 1:
        return models[0]["id"]
    hint = f", alias '{alias}'" if alias else ""
    raise GatewayError(f"model is required: pass --model or set a default with `model set` ({CAPABILITY}{hint})")


def slug(text: str, limit: int = 40) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fa5]+", "-", text or "").strip("-")
    return (cleaned[:limit] or "output").lower()


def save_bytes(stem: str, payload: bytes, extension: str = "mp4") -> Path:
    target = OUTPUT_DIR / CAPABILITY / date.today().isoformat()
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"{stem}-{time.strftime('%H%M%S')}.{extension}"
    path.write_bytes(payload)
    return path


def download(settings: dict, url: str, timeout: int = 120) -> bytes:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return read_body(resp)
    except urllib.error.HTTPError as err:
        message, code = parse_error(read_body(err), err.code)
        raise GatewayError(f"download failed: {message}", err.code, code) from None
    except urllib.error.URLError as err:
        raise GatewayError(f"download failed: {url}: {err.reason}") from None


def load_json_argument(value: str):
    if not value:
        return None
    candidate_text = value[1:] if value.startswith("@") else value
    if len(candidate_text) < 4096:
        try:
            candidate = Path(candidate_text)
            if candidate.is_file():
                value = candidate.read_text("utf-8")
        except OSError:
            pass
    try:
        return json.loads(value)
    except ValueError:
        return value


def handle_login(args, settings: dict) -> None:
    if not args.key:
        raise GatewayError("--key is required")
    if args.base_url and not args.base_url.startswith(("http://", "https://")):
        raise GatewayError("--base-url must start with http:// or https://")
    target = ROOT / "config.json"
    data = read_json(target)
    data["api_key"] = args.key
    if args.base_url:
        data["base_url"] = args.base_url.rstrip("/")
    if args.group:
        data["group"] = args.group
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    os.chmod(target, 0o600)
    emit({"ok": True, "config": str(target), "base_url": data.get("base_url") or settings["base_url"]})


def handle_model(args, settings: dict) -> None:
    if args.action == "set":
        target = ROOT / "config.json"
        data = read_json(target)
        data["model"] = args.model_id
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        os.chmod(target, 0o600)
        emit({"ok": True, "model": args.model_id, "config": str(target)})
        return
    configured = settings["default_model"]
    available = None
    if configured:
        try:
            available = configured in {model["id"] for model in load_models(settings)}
        except GatewayError:
            available = None
    emit({"ok": True, "model": configured, "configured": bool(configured), "available": available,
          "source": str(ROOT / "config.json") if configured else "none"})


def handle_config(args, settings: dict) -> None:
    emit({
        "ok": True,
        "capability": CAPABILITY,
        "platform": {"name": PLATFORM, "url": PLATFORM_URL, "tagline": PLATFORM_TAGLINE,
                     "description_zh": PLATFORM_DESC_ZH, "description_en": PLATFORM_DESC_EN,
                     "repository": REPO_URL},
        "config": str(ROOT / "config.json"),
        "base_url": settings["base_url"],
        "group": settings["group"],
        "model": settings["default_model"],
        "api_key": mask_secret(settings["api_key"]),
        "sources": settings["sources"],
        "defaults": str(DEFAULTS_PATH),
    })


def handle_models(args, settings: dict) -> None:
    models = load_models(settings, refresh=args.refresh)
    key = re.sub(r"[^a-z0-9]+", "-", (settings.get("base_url") or "unconfigured").lower()).strip("-")
    cached = read_json(CACHE_DIR / f"{CAPABILITY}-{key}.json")
    fetched_at = cached.get("fetched_at") or 0
    emit({"ok": True, "base_url": settings["base_url"], "count": len(models),
          "cached_at": fetched_at or None,
          "cache_age_seconds": int(time.time() - fetched_at) if fetched_at else None,
          "models": models})


def handle_resolve(args, settings: dict) -> None:
    matches = resolve_alias(args.alias, load_models(settings))
    if not matches:
        raise GatewayError(f"no model matches alias '{args.alias}'")
    emit({"ok": True, "alias": args.alias, "matches": matches})


def handle_doctor(args, settings: dict) -> None:
    report = {"ok": False, "base_url": settings["base_url"], "sources": settings["sources"],
              "api_key": mask_secret(settings["api_key"]), "api_key_configured": bool(settings["api_key"])}
    if not settings["api_key"]:
        report["error"] = {"message": "no API key configured"}
        emit(report)
        return
    try:
        payload = request_json(settings, "GET", "/v1/models")
        report["auth_ok"] = True
        report["models"] = len(payload.get("data") or [])
        report["ok"] = True
    except GatewayError as err:
        report["auth_ok"] = False
        report["error"] = {"message": err.message, "status": err.status}
    emit(report)


def normalize_video(payload: dict) -> dict:
    data = payload.get("data")
    if isinstance(data, dict) and ("status" in data or "task_id" in data):
        return {
            "status": str(data.get("status") or "").upper(),
            "progress": data.get("progress"),
            "url": data.get("result_url") or data.get("url") or "",
            "reason": data.get("fail_reason") or "",
        }
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    return {
        "status": str(payload.get("status") or "").upper(),
        "progress": payload.get("progress"),
        "url": str(metadata.get("url") or ""),
        "reason": str(error.get("message") or ""),
    }


def poll(settings: dict, path: str, timeout: int, interval: int) -> dict:
    deadline = time.time() + max(timeout, 1)
    interval = max(interval, 1)
    while True:
        state = normalize_video(request_json(settings, "GET", path))
        if state["status"] in TERMINAL_STATUS or time.time() >= deadline:
            return state
        time.sleep(interval)


def build_body(args, fields: list) -> dict:
    body = {}
    for field in fields:
        value = getattr(args, field, None)
        if value is None or value == "" or value == []:
            continue
        body[field] = value
    if getattr(args, "group", ""):
        body["group"] = args.group
    return body


def handle_video_create(args, settings: dict) -> None:
    model = pick_model(args, load_models(settings), "seedance", settings["default_model"])
    body = build_body(args, ["prompt", "duration", "seconds", "size", "mode", "ratio", "width", "height"])
    body["model"] = model
    name = model.lower()
    is_h3 = name.startswith("minimax-h3")
    is_vidu = name.startswith("vidu")
    is_kling4 = name.startswith("kling-4")
    is_omni = name.startswith("gemini-omni")
    if is_h3 and body.get("size"):
        body["size"] = str(body["size"]).upper()

    images = list(args.image) + list(args.images)
    reference_videos = list(args.reference_video)
    reference_audios = list(args.reference_audio)
    metadata = load_json_argument(args.metadata) if args.metadata else {}
    if not isinstance(metadata, dict):
        metadata = {}
    content = load_json_argument(args.content) if args.content else None

    if args.ratio:
        body["ratio"] = args.ratio
        metadata.setdefault("aspect_ratio", args.ratio)
    if args.audio:
        metadata["audio"] = True
    if is_h3:
        body.setdefault("ratio", metadata.get("aspect_ratio") or "16:9")
        metadata.setdefault("aspect_ratio", body["ratio"])

    reference_mode = body.get("mode") in ("reference_material", "reference_images", "r2v")
    if is_vidu and name.startswith("vidu-q4") and not images and not reference_videos and not reference_audios:
        raise GatewayError("Vidu Q4 requires at least one image")
    if reference_mode:
        if is_vidu:
            if reference_audios:
                body["mode"] = "reference_material"
                body["audio_urls"] = reference_audios
            else:
                body["mode"] = "reference_images"
        elif is_omni:
            body["mode"] = "r2v"
        else:
            body["mode"] = "reference_material"
    elif is_omni:
        body["mode"] = "r2v" if images else "t2v"

    if images or reference_videos or reference_audios:
        if reference_mode:
            if images:
                body["images"] = images
                metadata["reference_image_urls"] = images
            if reference_videos:
                metadata["reference_video_urls"] = reference_videos
            if reference_audios:
                metadata["reference_audio_urls"] = reference_audios
            if content is None:
                content = [{"type": "text", "text": body.get("prompt", "")}]
                content += [{"type": "image_url", "image_url": {"url": url}, "role": "reference_image"}
                            for url in images]
                content += [{"type": "video_url", "video_url": {"url": url}, "role": "reference_video"}
                            for url in reference_videos]
                content += [{"type": "audio_url", "audio_url": {"url": url}, "role": "reference_audio"}
                            for url in reference_audios]
        elif images:
            if len(images) > 1 and is_h3:
                raise GatewayError(
                    "MiniMax H3 does not support first/last frames; pass --mode reference_material for image references"
                )
            if len(images) > 1 and is_vidu and name.startswith("vidu-q4"):
                raise GatewayError("Vidu Q4 does not support first/last frames; pass --mode reference_images")
            if len(images) == 1:
                body["image"] = images[0]
                metadata["first_frame_image"] = images[0]
            else:
                body["image"] = images[0]
                body["images"] = images
                metadata["first_frame_image"] = images[0]
                metadata["last_frame_image"] = images[1]
                metadata["image_tail"] = images[1]
                if is_kling4:
                    body["mode"] = "i2v_first_last"

            if is_h3:
                content = [{"type": "text", "text": body.get("prompt", "")},
                           {"type": "image_url", "image_url": {"url": images[0]}, "role": "first_frame"}]
                if len(images) > 1:
                    content.append({"type": "image_url", "image_url": {"url": images[1]}, "role": "last_frame"})

    if metadata:
        body["metadata"] = metadata
    if content is not None:
        body["content"] = content
    if not body.get("prompt") and not body.get("content"):
        raise GatewayError("--prompt or --content is required")
    payload = request_json(settings, "POST", "/v1/video/generations", body=body)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    task_id = payload.get("id") or payload.get("task_id") or data.get("task_id")
    if not task_id:
        raise GatewayError(f"missing task id in response: {json.dumps(payload, ensure_ascii=False)[:300]}")
    emit({"ok": True, "task_id": task_id, "status": payload.get("status") or "queued", "model": model})


def handle_video_status(args, settings: dict) -> None:
    task_id = urllib.parse.quote(args.task_id, safe="")
    path = f"/v1/video/generations/{task_id}"
    state = poll(settings, path, args.timeout, args.interval) if args.wait else normalize_video(
        request_json(settings, "GET", path))

    files = []
    if state["status"] == "SUCCESS" and args.download:
        if state["url"]:
            raw = download(settings, state["url"])
        else:
            _, _, raw = request(settings, "GET", f"/v1/videos/{task_id}/content")
        files.append(str(save_bytes(slug(args.task_id, 24), raw)))

    emit({"ok": True, "task_id": args.task_id, "status": state["status"], "progress": state["progress"],
          "url": state["url"], "reason": state["reason"], "files": files})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gateway.py",
        description=f"Video generation skill for {PLATFORM} ({PLATFORM_URL})",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            f"{PLATFORM} · {PLATFORM_URL}\n"
            f"{PLATFORM_DESC_ZH}\n"
            f"{PLATFORM_DESC_EN}\n"
            f"Repository: {REPO_URL}"
        ),
    )
    parser.add_argument("--request-timeout", dest="request_timeout", type=int, default=0,
                        help="override the single-request timeout in seconds")
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="store an API key")
    login.add_argument("--key", required=True)
    login.add_argument("--base-url", default="")
    login.add_argument("--group", default="")

    sub.add_parser("config", help="show resolved settings")

    models = sub.add_parser("models", help="list video models")
    models.add_argument("--refresh", action="store_true")

    model = sub.add_parser("model", help="show or set the default model")
    model_sub = model.add_subparsers(dest="action", required=True)
    model_sub.add_parser("show", help="show the configured default model")
    model_set = model_sub.add_parser("set", help="pin a default model in config.json")
    model_set.add_argument("model_id")

    resolve = sub.add_parser("resolve", help="map an alias to a model id")
    resolve.add_argument("alias")

    video = sub.add_parser("video", help="video generation tasks")
    video_sub = video.add_subparsers(dest="action", required=True)

    create = video_sub.add_parser("create")
    create.add_argument("--prompt", default="")
    create.add_argument("--model", default="")
    create.add_argument("--duration", type=int, default=None)
    create.add_argument("--seconds", default="")
    create.add_argument("--size", default="")
    create.add_argument("--mode", default="")
    create.add_argument("--ratio", default="")
    create.add_argument("--width", type=int, default=None)
    create.add_argument("--height", type=int, default=None)
    create.add_argument("--image", action="append", default=[])
    create.add_argument("--images", action="append", default=[])
    create.add_argument("--reference-video", dest="reference_video", action="append", default=[])
    create.add_argument("--reference-audio", dest="reference_audio", action="append", default=[])
    create.add_argument("--audio", action="store_true")
    create.add_argument("--content", default="")
    create.add_argument("--metadata", default="")
    create.add_argument("--group", default="")

    status = video_sub.add_parser("status")
    status.add_argument("task_id")
    status.add_argument("--wait", action="store_true")
    status.add_argument("--timeout", type=int, default=900)
    status.add_argument("--interval", type=int, default=5)
    status.add_argument("--download", action="store_true")

    sub.add_parser("doctor", help="verify credentials and connectivity")
    return parser


DISPATCH = {
    ("login", None): handle_login,
    ("config", None): handle_config,
    ("models", None): handle_models,
    ("model", "show"): handle_model,
    ("model", "set"): handle_model,
    ("resolve", None): handle_resolve,
    ("video", "create"): handle_video_create,
    ("video", "status"): handle_video_status,
    ("doctor", None): handle_doctor,
}


def main(argv: list | None = None) -> None:
    args = build_parser().parse_args(argv)
    current = settings()
    if getattr(args, "request_timeout", 0) > 0:
        current["timeout"] = args.request_timeout
    try:
        DISPATCH[(args.command, getattr(args, "action", None))](args, current)
    except GatewayError as err:
        fail(err.code or "request_failed", err.message, err.status)
    except KeyboardInterrupt:
        fail("interrupted", "cancelled by user")
    except Exception as err:
        fail("internal_error", f"{type(err).__name__}: {err}")


if __name__ == "__main__":
    main()
