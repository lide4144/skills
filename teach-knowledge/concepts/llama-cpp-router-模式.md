---
title: "llama.cpp Router 模式"
kind: concept
created: 2026-08-16
---

# llama.cpp Router 模式 vs 单模型模式

## 两种 serving 形态
| | 单模型模式 | Router 模式 |
|---|---|---|
| 启动 | `llama-server -m model.gguf` | `llama-server --models-dir models --models-preset models.ini` |
| 模型加载 | 启动时加载，常驻 | **按需加载**（on-demand），第一个请求才拉起 |
| 请求 model 字段 | **被忽略**，发什么都行 | 必须**精确匹配**预设名，否则 400 not found |
| 模型 id | 带路径：`models\xxx.gguf` | 预设名（= models.ini section 名 / 文件基名） |
| 适用 | 单客户端专用 | 多模型切换、Pi `/llama` 集成 |

## models.ini 预设（--models-preset）
```ini
version = 1
[模型名]                    ; section 名 = router 里的模型 id
mmproj = models/xxx.gguf    ; ⚠ 相对服务器工作目录,不相对 --models-dir
model-draft = drafts/xx.gguf
temp = 0.6
```
- 命令行传入的 `-c` / `-ngl` 等全局参数会被 router 继承给每个模型实例
- section 名就是 API 里的模型 id，可以起短别名（如 `[gemma4]`）

## 踩过的坑（重要）
1. **路径解析**：`mmproj` / `model-draft` 按字面路径相对**工作目录**解析，写裸文件名会报 "failed to open GGUF file"
2. **模型名不匹配**：Web UI 把上次用的模型名存 localStorage。单模型模式存的是带路径 id，切到 router 后就报 not found → 重新在下拉框选一次模型即可
3. 查 router 当前认哪些名字：`curl localhost:8001/v1/models`

## Related

- [[mmproj-多模态投影|mmproj 多模态投影]]
- [[speculative-decoding|Speculative Decoding]]
- [[vulkan-vs-rocm-后端|Vulkan vs ROCm 后端]]
- [[gemma4-26b-本地部署实战|Gemma4-26B 本地部署实战]]
