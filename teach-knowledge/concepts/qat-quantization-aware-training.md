---
title: "QAT (Quantization-Aware Training)"
kind: concept
created: 2026-08-16
---

# QAT (Quantization-Aware Training) 量化感知训练

## 面试定义（可直接背）
> "Quantization-Aware Training simulates low-precision quantization during training itself, so the model learns weights that are robust to quantization error — unlike PTQ (Post-Training Quantization), which quantizes a finished model and pays an accuracy penalty."

## PTQ vs QAT
| | PTQ (训练后量化) | QAT (量化感知训练) |
|---|---|---|
| 时机 | 训练完之后压 | 训练中就模拟量化 |
| 质量损失 | 有，越低 bit 越明显 | 极小，模型已"适应"低精度 |
| 成本 | 便宜，谁都能做 | 贵，要训练方（Google）自己做 |

## 实战意义
Gemma4 是 Google 官方 QAT 到 ~4bit 的模型，所以**只发 Q4_K_M 一个量化档**：
- 更高精度（Q6/Q8）：多花 40-100% 磁盘和带宽，质量几乎零提升 → 没意义
- 更低精度（Q3/Q2）：反而会浪费 QAT 对齐好的 4bit 甜点

选量化档的第一原则：**先看模型是不是 QAT 原生低 bit**，是的话直接拿官方甜点档，不用纠结。

## Related

- [[gguf|GGUF]]
- [[moe-mixture-of-experts|MoE (Mixture of Experts)]]
- [[gemma4-26b-本地部署实战|Gemma4-26B 本地部署实战]]
