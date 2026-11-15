---
name: video-generation
description: Submits and polls asynchronous video generation tasks through one AI gateway, with Seedance 2.0, Veo 3.1, Sora 2, Kling, MiniMax H3, Vidu, Gemini Omni, and Muse models. Use for text-to-video, image-to-video, first/last frame control, and multi-reference material. Platform: New.bi (https://api.new.bi), a professional, stable, and reliable AI model aggregation gateway.
metadata:
  version: 1.1.0
---

[中文](SKILL.md) · **English**

# Video Generation

Asynchronous tasks: submit, get a task id, poll until a terminal state, then download.

## When to use

- Text to video.
- Image to video or first/last frame control.
- Multi-reference material: keep a subject, scene, or style from supplied images, videos, or audio.
- The user asks for duration, resolution, aspect ratio, or a specific model.

## When not to use

- Still images. This tool only makes video.
- Music or speech, which are out of scope here.

## Prerequisites

Resolve the API key in this order (first match wins):

1. `config.json` in this project root
2. `AIGW_VIDEO_API_KEY`
3. `AIGW_API_KEY`
4. `OPENAI_API_KEY`

```bash
python3 scripts/gateway.py login --key sk-xxx
python3 scripts/gateway.py models
```

## Which models are available

By family:

| Family | Model | Notes |
| --- | --- | --- |
| ByteDance Seedance | Seedance 2.5, Seedance 2.0 (Standard, Fast, Mini) | multi-reference, native audio |
| Google Veo | Veo 3.1 (Standard, Fast, Components) | cinematic, multi-image consistency |
| Google Gemini Omni | Gemini Omni | generation and edits |
| OpenAI | Sora 2 | general |
| Kling | Kling | general |
| MiniMax | MiniMax H3 | 768P tiers, no first/last frame |
| MiniMax | MiniMax Hailuo 2.3 | image-to-video |
| Vidu | Vidu Q3 Turbo | image-to-video |
| Others | Muse Video, HappyHorse 1.0, Grok Imagine Video | fallbacks |

Run `models` for the available ids and prices. Pass `--model <id>` for one call, or `model set <id>` to write `model` into `config.json`; editing that file works too. In `models`, `price` above 0 is a fixed per-call price; `price` 0 with `ratio` above 0 bills by ratio. The two are not directly comparable.

`--base-url` writes the gateway address into `config.json`. Resolution order: `config.json`, `AIGW_VIDEO_BASE_URL`, `AIGW_BASE_URL`, then the packaged default in `scripts/defaults.json`.

## Set a default model

```bash
python3 scripts/gateway.py model set veo3.1   # pin the default model
python3 scripts/gateway.py model show                     # show the current default
```

Every submit uses it when `--model` is omitted; `--model` still overrides per call. The value lives in `model` inside `config.json`; editing the file directly works too.

## Reference material must be on the public internet

Providers fetch references by URL. The gateway passes the string through verbatim; it does not read local files.

- A local path, `file://` URL, or attachment path will fail or be ignored. Upload the file to a public host first and pass the resulting `https://` URL.
- The URL must open without authentication or cookies. Signed URLs work until they expire; keep the TTL longer than the generation time.
- Supported hosts include object storage (S3, R2, OSS, COS), CDNs, and public image hosts. A local server on `localhost` is not reachable by the provider.
- Base64 data URIs are model-specific. Prefer a public URL unless the model is known to accept data URIs.
- Videos and audio used as reference material must be public URLs for every provider.
- Keep reference files small. Large originals and some hosts fail with a download error from the provider side even when the URL opens fine in a browser. If a submit fails with a message about downloading the material, resize the file, re-host it, and retry with a different URL.

A failed reference download surfaces as a task-level failure with a message about the material, not as a 400. Read the failure reason before blaming the parameters.

Reference video and reference audio are optional capabilities and many channels reject them with `unsupported reference video` or a generic generation failure; the charge is refunded. Treat reference images as the portable option and verify video/audio references with a probe before a production run.

If the user only has a local file, say so and upload it before calling this skill.

## Capability modes

Three input modes exist. Availability differs by model and by the channel serving it, so never assume one model has a feature because another does.

| Mode | Input | Flags |
| --- | --- | --- |
| Text to video | prompt only | `--prompt` |
| First/last frame | exactly two images | `--image` twice |
| Multi-reference | any mix of images, videos, audio | `--mode reference_material` with `--images` / `--reference-video` / `--reference-audio` |

Mode names differ per provider:

| Model family | Reference mode | First/last mode |
| --- | --- | --- |
| Seedance, MiniMax H3 | `reference_material` | not supported on H3 |
| Kling 4.0 | `reference_material` or `reference_images` | `i2v_first_last` |
| Vidu Q4 | `reference_images`; `reference_material` plus `audio_urls` when audio is supplied | not supported |
| Gemini Omni | `r2v` | not documented |

The CLI normalizes these values from `--mode reference_material`: Vidu without audio becomes `reference_images`, Vidu with audio gets `reference_material` plus `audio_urls`, Gemini Omni becomes `r2v`, and Kling 4.0 first/last becomes `i2v_first_last`. H3 and Vidu Q4 first/last requests are rejected instead of silently producing a text-only video.

Capabilities are not predictable from the model name alone. Discover the model list, then probe with the cheapest settings before a production run:

1. `models` and pick the lowest price tier.
2. Use the shortest duration and the lowest resolution the model accepts.
3. Submit a probe with distinctive reference material, then inspect the first frame.
4. Only then run the real task.

If a probe ignores the references, the serving channel is text-only for that model id. Try another model id in the same family before concluding the gateway is broken.

## Commands

```bash
# Text to video
python3 scripts/gateway.py video create --prompt "a red panda walking through bamboo, cinematic" \
  --model <model> --duration 6

# First and last frame (exactly two --image values)
python3 scripts/gateway.py video create --model <model> \
  --prompt "a smooth cinematic transition between the two frames" \
  --image https://cdn.example.com/first.jpg --image https://cdn.example.com/last.jpg \
  --duration 6

# Multi-reference images
python3 scripts/gateway.py video create --model <model> --mode reference_material \
  --prompt "the cat from image 1 and the pug from image 2 walk together in a park" \
  --images https://cdn.example.com/cat.jpg --images https://cdn.example.com/pug.jpg \
  --seconds 4

# Multi-reference with video and audio
python3 scripts/gateway.py video create --model <model> --mode reference_material \
  --prompt "put the animal from image 2 into the scene of image 1" \
  --images https://cdn.example.com/scene.jpg --images https://cdn.example.com/animal.jpg \
  --reference-video https://cdn.example.com/motion.mp4 \
  --reference-audio https://cdn.example.com/bgm.mp3 --seconds 4

# Poll once, then wait and download
python3 scripts/gateway.py video status <task_id>
python3 scripts/gateway.py video status <task_id> --wait --download
```

## Parameters

| Flag | Required | Notes |
| --- | --- | --- |
| `--prompt` | yes unless `--content` | Text description. |
| `--model` | no | Exact model id from `models`. Defaults to the configured model. |
| `--duration` | no | Integer seconds. Fractional values are not supported. |
| `--seconds` | no | Duration as a string, used by some providers. |
| `--size` | no | `720p`, `1080p`, `2k`, or `WxH`. MiniMax H3 uses the uppercase enum `480P`, `768P`, `2K`; the CLI uppercases the value automatically. |
| `--ratio` | no | Aspect ratio such as `16:9` or `9:16`; also written to `metadata.aspect_ratio`. |
| `--width` / `--height` | no | Pixel dimensions for providers that take numbers. |
| `--image` | no | Repeatable. One value is a first frame; two values are first plus last. H3 and Vidu Q4 do not accept first/last frames. |
| `--images` | no | Repeatable. Reference image URLs for multi-reference mode. |
| `--reference-video` | no | Repeatable. Public video URLs, used with `--mode reference_material`. Vidu Q4 does not accept reference video. |
| `--reference-audio` | no | Repeatable. Public audio URLs, used with `--mode reference_material`. Vidu Q4 sends these as top-level `audio_urls`. |
| `--mode` | no | `reference_material`, `reference_images`, or `r2v`. The CLI normalizes the value for Vidu, Kling 4.0, and Gemini Omni. |
| `--audio` | no | Ask the provider to generate an audio track when supported. Verified: some models return an AAC stream alongside H.264. |
| `--content` | no | Raw native multimodal array as inline JSON or `@file.json`. Overrides generated content. |
| `--metadata` | no | Extra JSON merged into `metadata`; auto-filled fields are not overwritten. |
| `--group` | no | Route to a billing group. |

Some models reject `size` or ignore `width`/`height`. If a submit returns a 400 about a parameter, drop it and rely on the model default, then re-check the output resolution.

MiniMax H3 takes numeric `width`/`height` in addition to the uppercase `size` enum, and requires a top-level `ratio` for text-to-video. When `--ratio` is omitted the CLI sends `16:9`. H3 ships standard and 768P tiers; run `models` for the ids.

Payload shapes, endpoints, and response fields are in [references/api.en.md](references/api.en.md).

## Task state

The submit response carries the task id. Keep it: `video status <task_id>` polls that task at any time, and `--wait` polls until it reaches a terminal status. Nothing is written locally.

## Cost control

- Probe with the shortest duration and the lowest resolution tier.
- Higher resolution tiers can cost roughly twice the entry tier.
- Failed or timed-out tasks refund the pre-deducted quota.

## Errors

| Status | Meaning | Action |
| --- | --- | --- |
| 400 | Invalid parameter, unsupported capability, or unfetchable reference URL | Drop the rejected field, make references public, or switch models. |
| 401 | Missing or invalid key | Re-run `login`, then `doctor`. |
| 402 | Insufficient quota | Top up. |
| 429 | Concurrency cap | Back off and retry. |
| 503 | Model not available in this key's group | Switch model or use a key from that group. |
| `FAILURE` | Generation failed | Report `reason`; do not retry blindly. |
