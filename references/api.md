# 接口与返回形态

## 请求里都放了什么

命令行会把网关认识的几种写法一起发过去，渠道读它支持的那份。

- 一张图：`image`，加 `metadata.first_frame_image`。
- 两张图：`image`、`images`、`metadata.first_frame_image`、`metadata.last_frame_image`、`metadata.image_tail`。
- 原生帧角色：`content[]` 里带 `role: first_frame` / `role: last_frame`。
- 多参考：`mode: reference_material`、`images`、`metadata.reference_image_urls`，以及带 `role: reference_image` / `reference_video` / `reference_audio` 的 `content[]`。

## 接口

提交：

```
POST /v1/video/generations
{ "id": "...", "task_id": "...", "object": "video", "model": "...", "status": "queued", "progress": 0, "created_at": 1710000000 }
```

镜像上游的渠道返回的是 `{ "code": 200, "success": true, "data": { "task_id": "...", "status": "processing" } }`。命令行三种 task id 位置都能读。`status` 是 `queued`，不是 `pending`。

轮询：

```
GET /v1/video/generations/{task_id}
{ "code": "success", "data": { "task_id": "...", "status": "SUCCESS", "progress": "100%", "result_url": "https://..." } }
```

状态是大写：`SUBMITTED`、`QUEUED`、`IN_PROGRESS`、`SUCCESS`、`FAILURE`。有的渠道在 `result_url` 给直链，有的只给网关代理：

```
GET /v1/videos/{task_id}/content
```

这个接口认 API token 或会话 Cookie，`result_url` 为空时命令行会走它。

OpenAI 兼容的形式不一样：状态小写，地址在 `metadata.url`。
