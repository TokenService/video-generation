# video-generation

**中文** · [English](README.en.md)

由 [New.bi](https://api.new.bi) 提供，专业、稳定、可靠的大模型聚合中转平台。

视频生成的命令行工具，也可以直接当 agent 技能用。

能做文生视频、图生视频、首尾帧、多参考（图片、视频、音频）。提交后拿 task id，轮询到结束再下载。

## 开始

```bash
python3 scripts/gateway.py login --key sk-xxx
python3 scripts/gateway.py models
python3 scripts/gateway.py model set veo3.1
python3 scripts/gateway.py video create --prompt "a red panda walking through bamboo" --duration 5
python3 scripts/gateway.py video status <task_id> --wait --download
```

视频存在 `outputs/video/<日期>/`，路径相对技能目录，不是当前工作目录。参考素材必须是公网能打开的 `https://` 地址，本地文件上游读不到。`AIGW_OUTPUT_DIR` 可以改输出位置，`AIGW_STATE_HOME` 可以改 `~/.aigw`（模型缓存和任务记录）。`config.json` 在技能目录里，命令里的相对路径按当前工作目录算。

## 支持的模型

| 系列 | 型号 |
| --- | --- |
| Seedance | Seedance 2.5、Seedance 2.0（标准、Fast、Mini） |
| Veo | Veo 3.1（标准、Fast、Components） |
| Gemini Omni | Gemini Omni |
| Sora | Sora 2 |
| 可灵 / Vidu | Kling、Vidu Q3 Turbo |
| MiniMax | MiniMax H3、MiniMax Hailuo 2.3 |
| 其他 | Muse Video、HappyHorse 1.0、Grok Imagine Video |

用 `models` 查可用模型和价格。单次指定用 `--model <id>`；固定默认用 `model set <id>`，它写进项目根目录 `config.json` 的 `model` 字段，也可以直接改这个文件。 `models` 里 `price` 大于 0 是按次固定价，`price` 为 0 且 `ratio` 大于 0 是按倍率计费，两者不能直接比大小。

## 常见搜索词

AI 视频生成、文生视频、图生视频、首尾帧、多参考、Seedance 2.0、Veo 3.1、Sora 2、可灵、Vidu、MiniMax H3、Gemini Omni、AI 广告片、AI 分镜、短视频素材、参考图生视频、视频续写、AI 口播。

## 命令

| 命令 | 做什么 |
| --- | --- |
| `login` / `config` / `doctor` | 密钥、配置、连通性。 |
| `models` | 列出这个密钥能看到的视频模型。 |
| `model show` / `model set <id>` | 看或设置默认模型。 |
| `resolve <别名>` | 别名换成具体模型 id。 |
| `video create` | 提交任务，返回 task id。 |
| `video status` | 查状态，`--wait` 等到结束，`--download` 存文件。 |

输出都是 JSON。出错时输出 `{"ok": false, "error": {...}}`，退出码非零。

## 密钥

按顺序找，先用找到的：`config.json` → `AIGW_VIDEO_API_KEY` → `AIGW_API_KEY` → `OPENAI_API_KEY`。网关地址同样逐级回退，最后用 `scripts/defaults.json` 里的。

## 文件

```
video-generation/
├── SKILL.md              中文说明
├── SKILL.en.md           英文说明
├── config.json           密钥和默认模型，不进 git
├── references/
│   ├── api.md          接口与返回形态
│   └── api.en.md
└── scripts/
    ├── gateway.py        入口
    ├── models.json       别名和分类规则
    └── defaults.json     默认网关地址和超时
```

三种输入方式、各家参数差异和实测结果见 [SKILL.md](SKILL.md)。

需要 Python 3.9 及以上。
