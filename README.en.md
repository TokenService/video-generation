# video-generation

[中文](README.md) · **English**

Provided by [New.bi](https://api.new.bi), a professional, stable, and reliable AI model aggregation gateway.

Asynchronous video generation CLI for an AI gateway. Use it as a standalone tool or as an agent skill.

- Text-to-video, image-to-video, first/last frame control
- Multi-reference material: images, video, audio
- Submit, poll, download in one command chain

See [SKILL.en.md](SKILL.en.md) for capability boundaries and verified behaviour.

## Layout

```
video-generation/
├── SKILL.md              Chinese skill doc
├── SKILL.en.md           English skill doc
├── README.md
├── README.en.md
├── config.json           credential and default model, never committed
├── references/
│   ├── api.md          reference
│   └── api.en.md
└── scripts/
    ├── gateway.py        single entry point, video code only
    ├── models.json       alias table and category rules
    └── defaults.json     packaged gateway address and timeout
```

## Quick start

```bash
python3 scripts/gateway.py login --key sk-xxx
python3 scripts/gateway.py models
python3 scripts/gateway.py model set veo3.1
python3 scripts/gateway.py video create --prompt "a red panda walking through bamboo" --duration 5
python3 scripts/gateway.py video status <task_id> --wait --download
```

Files land in `outputs/video/<YYYY-MM-DD>/`, relative to the skill directory. Reference material must be a public `https://` URL. `AIGW_OUTPUT_DIR` changes the output root; `AIGW_STATE_HOME` relocates `~/.aigw` (model cache and task records). `config.json` sits in the skill directory; relative paths in commands resolve from your working directory.

## Supported models

| Family | Model |
| --- | --- |
| Seedance | Seedance 2.5, Seedance 2.0 (Standard, Fast, Mini) |
| Veo | Veo 3.1 (Standard, Fast, Components) |
| Gemini Omni | Gemini Omni |
| Sora | Sora 2 |
| Kling / Vidu | Kling, Vidu Q3 Turbo |
| MiniMax | MiniMax H3, MiniMax Hailuo 2.3 |
| Others | Muse Video, HappyHorse 1.0, Grok Imagine Video |

Run `models` for the available ids and prices. Pass `--model <id>` for one call, or `model set <id>` to write `model` into `config.json`; editing that file works too. In `models`, `price` above 0 is a fixed per-call price; `price` 0 with `ratio` above 0 bills by ratio. The two are not directly comparable.

## Search terms

AI video generator, text to video, image to video, first and last frame, multi-reference, Seedance 2.0, Veo 3.1, Sora 2, Kling, Vidu, MiniMax H3, Gemini Omni, AI ad clip, AI storyboard, short video footage, video continuation.

## Commands

| Command | Purpose |
| --- | --- |
| `login` / `config` / `doctor` | Credential and connectivity. |
| `models` | List video models visible to this key. |
| `model show` / `model set <id>` | Show or pin the default model. |
| `resolve <alias>` | Map an alias to concrete model ids. |
| `video create` | Submit a task, returns the task id. |
| `video status` | Check status; `--wait` polls, `--download` saves the file. |

## Credentials

Resolution order, first match wins: `config.json` → `AIGW_VIDEO_API_KEY` → `AIGW_API_KEY` → `OPENAI_API_KEY`. `base_url` follows the same chain and falls back to `scripts/defaults.json`.

Every command prints JSON; failures return `{"ok": false, "error": {...}}` and exit non-zero.

## Requirements

Python 3.9 or newer. No third-party packages.
