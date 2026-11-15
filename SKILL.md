---
name: video-generation
description: 提交并轮询异步视频生成任务，可选 Seedance 2.0、Veo 3.1、Sora 2、Kling、MiniMax H3、Vidu、Gemini Omni、Muse 等模型。支持文生视频、图生视频、首尾帧和多参考。 平台：New.bi（https://api.new.bi），专业、稳定、可靠的大模型聚合中转平台。
metadata:
  version: 1.1.0
---

**中文** · [English](SKILL.en.md)

# 视频生成

异步任务：提交拿到 task id，轮询到结束，再下载。

## 什么时候用

- 文生视频。
- 图生视频，或者指定首帧、尾帧。
- 多参考：从给过来的图片、视频、音频里保留主体、场景或风格。
- 用户说了时长、分辨率、画幅或具体模型。

## 什么时候不用

- 静态图片，这里只做视频。
- 音乐或语音，这些不在这个工具里。

## 准备

密钥按顺序查找，先用找到的：

1. 项目根目录 `config.json` 里的 `api_key`
2. `AIGW_VIDEO_API_KEY`
3. `AIGW_API_KEY`
4. `OPENAI_API_KEY`

```bash
python3 scripts/gateway.py login --key sk-xxx
python3 scripts/gateway.py models
```

## 能用哪些模型

按系列分：

| 系列 | 型号 | 特点 |
| --- | --- | --- |
| 字节 Seedance | Seedance 2.5、Seedance 2.0（标准、Fast、Mini） | 多参考，原生音频 |
| Google Veo | Veo 3.1（标准、Fast、Components） | 电影感，多图一致性 |
| Google Gemini Omni | Gemini Omni | 生成与改片 |
| OpenAI | Sora 2 | 通用 |
| 可灵 | Kling | 通用 |
| MiniMax | MiniMax H3 | 768P 档，不支持首尾帧 |
| MiniMax | MiniMax Hailuo 2.3 | 图生视频 |
| Vidu | Vidu Q3 Turbo | 图生视频 |
| 其他 | Muse Video、HappyHorse 1.0、Grok Imagine Video | 备选 |

用 `models` 查可用模型和价格。单次指定用 `--model <id>`；固定默认用 `model set <id>`，它写进项目根目录 `config.json` 的 `model` 字段，也可以直接改这个文件。 `models` 里 `price` 大于 0 是按次固定价，`price` 为 0 且 `ratio` 大于 0 是按倍率计费，两者不能直接比大小。

## 固定默认模型

```bash
python3 scripts/gateway.py model set veo3.1
python3 scripts/gateway.py model show
```

设置后提交不带 `--model` 都用它，`--model` 仍可临时覆盖。值写在项目根目录 `config.json` 的 `model` 字段，手改这个文件也一样。

## 素材必须能在公网打开

上游按 URL 去抓素材，网关只把这个地址原样转过去，读不到本地文件。

- 本地路径、`file://`、附件路径都会失败或被忽略。先传到公网，再传 `https://` 地址。
- 地址要能免登录直接打开。签名地址可以，但有效期要比生成时间长。
- 对象存储、CDN、公开图床都行。`localhost` 上游访问不到。
- base64 data URI 只有部分模型接受，不确定就用公网地址。
- 参考视频和参考音频，所有上游都要求公网地址。
- 文件别太大。大文件和某些域名会从上游那边下载失败，即使浏览器能打开。报素材下载失败时，压缩后换个地址再试。

素材下载失败看起来是任务失败，带一条素材相关的说明，不是 400。先读原因，再怀疑参数。

参考视频、参考音频是可选能力，很多渠道直接拒绝，报 `unsupported reference video` 或一句笼统的生成失败，钱会退回。稳妥的做法是用参考图片，视频和音频先小成本试一次。

用户手上只有本地文件时，先说清楚需要先传公网，再调用。

## 三种输入方式

| 方式 | 输入 | 参数 |
| --- | --- | --- |
| 文生视频 | 只有提示词 | `--prompt` |
| 首尾帧 | 正好两张图 | `--image` 传两次 |
| 多参考 | 图片、视频、音频随意组合 | `--mode reference_material` 加 `--images` / `--reference-video` / `--reference-audio` |

各家的模式名不一样：

| 模型 | 多参考 | 首尾帧 |
| --- | --- | --- |
| Seedance、MiniMax H3 | `reference_material` | H3 不支持 |
| Kling 4.0 | `reference_material` 或 `reference_images` | `i2v_first_last` |
| Vidu Q4 | `reference_images`；带音频时是 `reference_material` 加 `audio_urls` | 不支持 |
| Gemini Omni | `r2v` | 没文档 |

命令行会把 `reference_material` 自动转成各家要求的值。H3 和 Vidu Q4 请求首尾帧会直接报错，不会悄悄生成一个纯文字视频。

能不能用不要猜。先列模型，再用最便宜的参数试：

1. `models`，挑最低价档。
2. 用模型允许的最短时长、最低分辨率。
3. 用一眼能认出来的参考素材提交，看首帧有没有变化。
4. 确认后再跑正式任务。

试的时候参考被忽略，说明这个模型在当前渠道上只支持文生视频。同系列换个型号再试。

## 提交

```bash
# 文生视频
python3 scripts/gateway.py video create --prompt "a red panda walking through bamboo, cinematic" \
  --model <model> --duration 6

# 首尾帧，正好两个 --image
python3 scripts/gateway.py video create --model <model> \
  --prompt "a smooth cinematic transition between the two frames" \
  --image https://cdn.example.com/first.jpg --image https://cdn.example.com/last.jpg \
  --duration 6

# 多参考图片
python3 scripts/gateway.py video create --model <model> --mode reference_material \
  --prompt "the cat from image 1 and the pug from image 2 walk together in a park" \
  --images https://cdn.example.com/cat.jpg --images https://cdn.example.com/pug.jpg \
  --seconds 4

# 多参考，加视频和音频
python3 scripts/gateway.py video create --model <model> --mode reference_material \
  --prompt "put the animal from image 2 into the scene of image 1" \
  --images https://cdn.example.com/scene.jpg --images https://cdn.example.com/animal.jpg \
  --reference-video https://cdn.example.com/motion.mp4 \
  --reference-audio https://cdn.example.com/bgm.mp3 --seconds 4
```

## 查询与下载

```bash
python3 scripts/gateway.py video status <task_id>
python3 scripts/gateway.py video status <task_id> --wait --download
```

提交返回的 task id 自己存好，`video status` 随时可以继续查，`--wait` 一直等到结束（成功或失败）。本地不写任务记录。

## 参数

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `--prompt` | 是，或用 `--content` | 画面描述。 |
| `--model` | 否 | 模型 id，来自 `models`。默认用配置文件里的。 |
| `--duration` | 否 | 整数秒，不支持小数。 |
| `--seconds` | 否 | 字符串时长，给需要字符串的上游用。 |
| `--size` | 否 | `720p`、`1080p`、`2k` 或 `宽x高`。H3 要大写枚举 `480P`、`768P`、`2K`，命令行自动转。 |
| `--ratio` | 否 | `16:9`、`9:16` 这类画幅，同时写进 `metadata.aspect_ratio`。 |
| `--width` / `--height` | 否 | 数字像素尺寸。 |
| `--image` | 否 | 可重复。一张是首帧，两张是首帧加尾帧。H3 和 Vidu Q4 不接受。 |
| `--images` | 否 | 可重复。多参考的图片地址。 |
| `--reference-video` | 否 | 可重复。公网视频地址，配合 `--mode reference_material`。Vidu Q4 不接受。 |
| `--reference-audio` | 否 | 可重复。公网音频地址，配合多参考。Vidu Q4 会转成顶层 `audio_urls`。 |
| `--mode` | 否 | `reference_material`、`reference_images` 或 `r2v`。 |
| `--audio` | 否 | 让上游生成音轨，看模型支持。实测有的模型会返回 H.264 加 AAC。 |
| `--content` | 否 | 原生多模态数组，内联 JSON 或 `@文件`，会覆盖自动生成的内容。 |
| `--metadata` | 否 | 额外 JSON 合进 `metadata`，不覆盖自动填的字段。 |
| `--group` | 否 | 指定计费分组。 |

有的模型不认 `size`，有的忽略 `width`/`height`。报参数 400 时去掉这个参数，用模型默认值，再看产物分辨率。

H3 除了大写 `size`，也认数字 `width`/`height`，文生视频必须有顶层 `ratio`。不给 `--ratio` 时命令行发 `16:9`。H3 有标准、768P 等档位，具体 id 用 `models` 看。

请求体形态、接口地址与返回字段见 [references/api.md](references/api.md)。

## 成本

- 先用最短时长、最低分辨率试。
- 高分辨率档大概贵一倍。
- 失败或超时的任务会退预扣的钱。

## 错误

| 状态 | 原因 | 怎么办 |
| --- | --- | --- |
| 400 | 参数不对、模型不支持，或素材抓不到 | 去掉被拒的参数，素材放公网，或换模型。 |
| 401 | 密钥缺失或无效 | 重新 `login`，跑 `doctor`。 |
| 402 | 余额不足 | 充值。 |
| 429 | 并发到顶 | 等一会重试。 |
| 503 | 这个分组用不了该模型 | 换模型或换密钥。 |
| `FAILURE` | 生成失败 | 把 `reason` 贴出来，别盲目重试。 |
