---
title: "GGUF"
kind: concept
created: 2026-08-16
---

# GGUF 模型文件格式

## 面试定义（可直接背）
> "GGUF is llama.cpp's binary model format that packs model metadata, the tokenizer, and quantized tensors into a single self-contained file, designed for fast memory-mapped loading and CPU/GPU hybrid inference."

## 结构
```
[Magic "GGUF"] [version] [metadata KV] [tensor info] [tensor data]
```
- **Metadata**：架构名（`general.architecture`）、层数、上下文上限、chat template 等——llama.cpp 靠它自动选架构实现
- **单文件自包含**：不像 safetensors 需要 config.json / tokenizer.json 一堆配套

## 量化档位命名
`Q4_K_M` = 4bit、K-quant 方法、Medium 混合精度（关键层留高精度）。
F16/BF16 是不量化；IQ/imatrix 系是更激进的压缩。

## 实战技巧
- 快速识别一个 .gguf 是什么：`dd if=x.gguf bs=64k count=1 | strings | grep architecture`
- **mmproj（视觉投影）、MTP draft head 也是 GGUF**，只是 architecture 分别是 `clip` 和 draft 头
- 一个模型可以有"融合版"GGUF（MTP 内嵌）和外挂文件两种形态，部署前先搞清楚手里的文件是哪种

## Related

- [[qat-quantization-aware-training|QAT (Quantization-Aware Training)]]
- [[mmproj-多模态投影|mmproj 多模态投影]]
- [[speculative-decoding|Speculative Decoding]]
- [[gemma4-26b-本地部署实战|Gemma4-26B 本地部署实战]]
