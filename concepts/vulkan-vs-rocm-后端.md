---
title: "Vulkan vs ROCm 后端"
kind: concept
created: 2026-08-16
---

# Vulkan vs ROCm 推理后端 (AMD 平台)

## 面试定义（可直接背）
> "Vulkan is a cross-vendor GPU compute API that runs anywhere, while ROCm is AMD's native compute stack with theoretically better hardware access — but in practice, operator coverage matters more than the API's theoretical ceiling."

## 本机实测（Strix Halo APU, Gemma4-26B Q4_K_M）
| | Vulkan | ROCm 7.2 |
|---|---|---|
| 短生成 | **77.4 t/s** | 64.3 t/s |
| 长生成 500 tok | **61.3 t/s** | 55.5 t/s |
| 结论 | **赢家，快 10-20%** | top-k 采样回退 CPU 拖后腿 |

## ROCm 慢的原因（日志实锤）
```
W llama_sampler_backend_support: device 'ROCm0' does not have
support for op TOP_K needed for sampler 'top-k'
```
ROCm 后端没实现 `TOP_K` 算子 → 每个 token 的 top-k 采样回退 CPU → 生成循环每步多一次 GPU→CPU 同步。
**教训：后端快慢不只看理论带宽，看你要用的每个 op 有没有在该后端实现。** 日志里 `llama_sampler_backend_support` 的 warning 就是这类问题的信号灯。

## 另一个坑：HIP 运行时来源
日志 `HIP Library Path: C:\Windows\SYSTEM32\amdhip64_7.dll` 说明实际加载的是**显卡驱动自带的 HIP dll**，不是 ROCm 安装目录里那份——版本错配是 ROCm 玄学问题的常见根源。

## Related

- [[统一内存-unified-memory|统一内存 Unified Memory]]
- [[moe-mixture-of-experts|MoE (Mixture of Experts)]]
- [[gemma4-26b-本地部署实战|Gemma4-26B 本地部署实战]]
- [[dflash|DFlash]]
