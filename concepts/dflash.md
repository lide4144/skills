---
title: "DFlash"
kind: concept
created: 2026-08-16
---

# DFlash 草稿器（block-diffusion drafter）

## 面试定义（可直接背）
> "DFlash is a standalone block-diffusion draft model (~0.4B) for speculative decoding that proposes a whole block of tokens in a single parallel forward pass, instead of drafting autoregressively token by token."

## 与 MTP / DSpark 的区别
| | MTP | DFlash | DSpark |
|---|---|---|---|
| 草稿器 | 主模型自带预测头 | 独立 block-diffusion 模型（~0.4B） | 独立半自回归 + Markov head + confidence head |
| 起草方式 | 自回归逐个猜 | **一次前向并行出整块** | 并行出块 + 置信度调度验证长度 |
| 来源 | 模型厂商训练自带 | z-lab（arXiv 2602.06036） | DeepSeek V4 生产方案（arXiv 2607.05147） |
| llama.cpp | `--spec-type draft-mtp` | `--spec-type draft-dflash -md <drafter.gguf>` | 代码已合并，GGUF 生态薄，主场 vLLM/SGLang |

## 完整排查结论（llama.cpp build 10448, 2026-08 多轮实测）
- **Vulkan 后端：DFlash 草稿器图必崩**（首个请求静默死，exit 5 无日志；`-fa on` 崩更快）。26B/35B 两个模型、Q8/BF16 两种草稿均复现 → **是 Vulkan drafter 实现坏了，不是配置问题**
- **ROCm 后端：DFlash 正常工作**（"以前成功过"的记忆指向 ROCm）
- **CPU 草稿器（`-ngld 0`）**：稳定但草稿太慢，净减速（22-38 t/s vs 裸跑 58）
- **关键参数 `--spec-draft-p-min 0.75`**：默认值被上游改成 0.00（issue #25908，肇因提交 d14ce3da "MTP clean-up" #23269），草稿器永远不提前退出 → 低置信内容硬猜 → 接受率崩。ROCm 上加 p-min 0.75 后接受率从 **27% → 92%**
- ROCm + DFlash + n-max 8 + p-min 0.75（Qwen3.6-35B-A3B）：短文 72.7 / 长文 54.9 / 代码 65 t/s，对比 ROCm 裸跑 +43%/+9%
- **已知冲突：投机解码 + 视觉输入 = 500 错误**（上游已知问题域，参见 open PR #25144）。要视觉就别开投机

## 教训
1. 排查顺序：换后端 > 换草稿精度 > 调参数——崩溃类问题先隔离后端
2. 关注上游默认值变更（p-min 0.75→0.00 这种静默 breaking change）
3. 接受率 <50% 的投机解码是负优化，看 `timings.draft_n_accepted/draft_n`

## Related

- [[speculative-decoding|Speculative Decoding]]
- [[vulkan-vs-rocm-后端|Vulkan vs ROCm 后端]]
- [[gguf|GGUF]]
- [[gemma4-26b-本地部署实战|Gemma4-26B 本地部署实战]]
