---
title: "统一内存 Unified Memory"
kind: concept
created: 2026-08-16
---

# 统一内存 (Unified Memory) APU 推理

## 面试定义（可直接背）
> "Unified memory is an architecture where CPU and GPU share the same physical RAM pool — there's no PCIe copy and no separate VRAM, so an APU can load models far larger than any consumer GPU's VRAM, limited only by total system RAM."

## 为什么 Strix Halo 适合跑大模型
- 64GB 内存 CPU/GPU 共享，`-ngl 99` 全量 offload 一个 16-18GB 的模型毫无压力
- 独显方案要装下同样模型需要 24GB+ VRAM（RTX 4090 级），APU 用普通内存就解决了
- 代价：内存带宽（~256GB/s 级）远低于独显 GDDR6X（~1TB/s）→ **推理是带宽瓶颈，所以天生偏慢**

## 由此推出的选型逻辑
带宽瓶颈场景下的速度公式：每 token 时间 ≈ 激活参数字节数 ÷ 带宽
- **MoE 模型是 APU 绝配**：总参数吃容量（内存够大），激活参数定速度（4B 激活 = 小模型的带宽需求）
- **Speculative decoding 收益大**：一次前向验证多个 token，摊薄带宽成本
- 本机实测：26B-A4B MoE + MTP = 60-78 t/s，同平台稠密 27B 只有 ~18 t/s

## Related

- [[moe-mixture-of-experts|MoE (Mixture of Experts)]]
- [[speculative-decoding|Speculative Decoding]]
- [[vulkan-vs-rocm-后端|Vulkan vs ROCm 后端]]
- [[gemma4-26b-本地部署实战|Gemma4-26B 本地部署实战]]
