---
title: "Speculative Decoding"
kind: concept
created: 2026-08-16
---

# Speculative Decoding 投机解码

## 面试定义（可直接背）
> "Speculative decoding accelerates autoregressive inference by using a small, fast draft model to propose several tokens ahead, which the large target model then verifies in a single parallel forward pass — accepted tokens are kept, so output is identical to the target model's, just faster."

## 解决的问题
LLM 逐 token 生成是**串行**的：生成第 N 个 token 必须等第 N-1 个完成。每步都做一次完整前向，GPU 算力大量闲置（瓶颈在显存带宽而非算力）。

## 工作流程
1. **Draft（起草）**：草稿器快速连猜 k 个 token
2. **Verify（验证）**：大模型**一次并行前向**同时给这 k 个位置打分
3. **Accept/Reject**：逐位比对，接受最长前缀；第一个被拒位置由大模型输出替换，之后的草稿丢弃

关键点：**输出分布与不用投机解码完全一致**——纯加速，不是近似。

```mermaid
sequenceDiagram
    participant D as Draft 草稿器(快)
    participant T as Target 模型(准)
    D->>D: 连猜 k 个 token
    D->>T: 提交草稿 [t1,t2,t3,t4]
    T->>T: 一次并行前向验证 4 个位置
    T-->>D: 接受 t1,t2,t3，拒绝 t4
    Note over T: t4 用大模型自己的采样替换<br/>本轮净产出 4 token / 1 次大模型前向
```

## 三种草稿器方案对比（2026 现状）
| | MTP | DFlash | DSpark |
|---|---|---|---|
| 草稿器 | 主模型自带预测头 | 独立 block-diffusion 模型（~0.4B） | 独立半自回归 + Markov head + confidence head |
| 起草方式 | 自回归逐个猜 | **一次前向并行出整块** | 并行出块 + 置信度调度验证长度 |
| 来源 | 模型厂商训练自带 | z-lab（arXiv 2602.06036） | DeepSeek V4 生产方案（arXiv 2607.05147） |
| llama.cpp | `--spec-type draft-mtp` | `--spec-type draft-dflash -md <drafter.gguf>` | 代码已合并，GGUF 生态薄，主场 vLLM/SGLang |

## 实战结论（Strix Halo APU, llama.cpp build 10448, 2026-08 多轮实测）

**MTP（Gemma4，Vulkan）**：61-78 t/s，接受率 58-88%，稳定 ✅ 生产配置

**DFlash**：ROCm 上可用（+p-min 0.75 后接受率 27%→92%），Vulkan 后端草稿器图必崩，详见 [[dflash|DFlash]]

**教训**：
1. `timings.draft_n_accepted/draft_n` 是健康度核心指标，**接受率 <50% 的投机解码是负优化**
2. 排查顺序：换后端 > 换草稿精度 > 调参数（p-min）——崩溃类问题先隔离后端
3. 关注上游默认值变更（p-min 0.75→0.00 这种静默 breaking change）

## Trade-off
- 多花一份草稿的显存和计算，换主模型前向次数减少
- batch 大、带宽不是瓶颈时收益递减

## Related

- [[moe-mixture-of-experts|MoE (Mixture of Experts)]]
- [[llama-cpp-router-模式|llama.cpp Router 模式]]
- [[vulkan-vs-rocm-后端|Vulkan vs ROCm 后端]]
- [[统一内存-unified-memory|统一内存 Unified Memory]]
- [[gemma4-26b-本地部署实战|Gemma4-26B 本地部署实战]]
- [[dflash|DFlash]]
- [[gguf|GGUF]]
