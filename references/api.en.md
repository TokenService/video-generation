# Endpoints and response shapes

## Payload shapes

The CLI sends every shape the gateway understands at once; the serving channel reads the one it supports.

- Single frame: `image`, plus `metadata.first_frame_image`.
- Two frames: `image`, `images`, `metadata.first_frame_image`, `metadata.last_frame_image`, `metadata.image_tail`.
- Native frame roles: `content[]` with `role: first_frame` / `role: last_frame`.
- Multi-reference: `mode: reference_material`, `images`, `metadata.reference_image_urls`, and `content[]` with `role: reference_image` / `reference_video` / `reference_audio`.

## Endpoints and response shapes

Submit:

```
POST /v1/video/generations
{ "id": "...", "task_id": "...", "object": "video", "model": "...", "status": "queued", "progress": 0, "created_at": 1710000000 }
```

An upstream-mirroring channel returns `{ "code": 200, "success": true, "data": { "task_id": "...", "status": "processing" } }` instead. The CLI accepts `id`, top-level `task_id`, and `data.task_id`. `status` is `queued`, not `pending`.

Poll:

```
GET /v1/video/generations/{task_id}
{ "code": "success", "data": { "task_id": "...", "status": "SUCCESS", "progress": "100%", "result_url": "https://..." } }
```

Status values here are uppercase: `SUBMITTED`, `QUEUED`, `IN_PROGRESS`, `SUCCESS`, `FAILURE`. Some channels return a direct signed URL in `result_url`; others return the gateway proxy:

```
GET /v1/videos/{task_id}/content
```

Accepts either an API token or a session cookie. The CLI falls back to it when `result_url` is empty.

The OpenAI-compatible alias has a different shape: lowercase status, URL under `metadata.url`.
