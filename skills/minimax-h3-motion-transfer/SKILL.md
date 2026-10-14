---
name: minimax-h3-motion-transfer
description: 基于 MiniMax H3 (Ref2VA / FL2VA) 与 Qwen-VL 的长视频分段动作迁移工坊。包含：源视频下载与高质量音频提取、≤80帧(73帧黄金网格)分片切分、三视图人设特征锁定、远程 RTX 5090 算力机 ComfyUI API 调度与 4-step Turbo 极速扩散采样、音画同步与全自动断点续传拼接，实现将舞蹈/长视频的人物 100% 替换为指定角色，且绝不爆显存。
---

# MiniMax H3 长视频分段动作迁移流水线 (Motion Transfer Workshop)

本技能沉淀了基于 **MiniMax H3 (Ref2VA / FL2VA)**、**Qwen3-VL 32B** 以及 **4-step Turbo LoRA** 的端到端动作迁移生产级工程方案。通过分段切片、角色人设三视图强约束、远程主力机（RTX 5090）调度与自愈式心跳轮询，实现将长视频（如 3~5 分钟舞蹈挑战、真人动作、剧情表演）中的人物 100% 动作复刻并替换为指定角色资产，且彻底规避扩散模型长序列显存溢出（OOM）问题。

---

## 一、端到端全链路架构 (Architecture)

```
[原始长视频 (MP4)] ──┬──> 【音频分离】 ──> audio_full.wav (48kHz/32kHz)
                     └──> 【帧切片工程】 ──> clip_001.mp4 ~ clip_N.mp4 (每段严格 ≤80帧)
                                            │
[角色定妆三视图 (PNG)] ──────────────────────┼──> 【远程 RTX 5090 算力机 ComfyUI】
                                            │     ├── Qwen3-VL 32B 语义与人设对齐
                                            │     ├── MiniMax H3 Hybrid INT8 基模
                                            │     ├── 4-step Turbo LoRA 极速采样
                                            │     └── 双流 VAE 视频+立体声音频解码
                                            │
                                            ▼
                                   【批量回传与断点续传】
                                            │
                                            ▼
                                   【无缝重组拼合成片】 ──> 最终长视频 (MP4)
```

---

## 二、视频切片工程规范（17k+5 黄金网格）

### 1. 为什么必须切片且严格 ≤ 80 帧？
- **时序扩散显存爆炸**：MiniMax H3 的 3D 注意力机制在处理长序列时显存呈超线性增长。未经切片的长视频会在第 345 帧遭遇质量悬崖，且极易在 24GB 显存下单帧 OOM。
- **17k + 5 时序网格铁律**：MiniMax H3 的时序潜空间下采样因子为 4，首帧独占 1 个潜帧，故最适帧数严格遵循公式：
  $$L = 17k + 5$$
  - 当 $k = 4$ 时，帧数为 **73 帧**（约 3.0 秒），这是兼顾时序动态稳定性、生成速度与显存安全的最佳甜点位（$73 \le 80$）。

### 2. 音视频同步切片命令
使用配套脚本 `scripts/split_video.py`：
```bash
python scripts/split_video.py <source_video.mp4> <output_dir> --frames 73
```
- 自动提取 48kHz 无损 PCM WAV 音频；
- 采用 `-c:v libx264 -crf 17 -preset fast` 逐帧精确切割；
- 输出切片清单 `manifest.json` 与无缝拼接索引 `concat_list.txt`。

---

## 三、角色三视图人设强约束

### 1. 参考图规范
- 必须使用纯白底的高保真三视图人设表（正面直立、侧面立面、背面立面），推荐分辨率 `1536×1024`；
- 人设图需清晰呈现角色的特征锚点（如发型齐刘海、瞳色瞳孔、服饰细节、腿饰、鞋履）；
- 在 MiniMax H3 工作流中作为 `<Picture 1>` 输入，设置 `ref_image_size: "match"`。

---

## 四、动作迁移提示词六段式模板

为确保模型理解「仅替换人物，100% 继承动作与背景」，提示词必须采用如下标准结构：

```text
subject_definitions:
<Subject 1> is the target character strictly referenced from <Picture 1>. Character identity LOCKED: [角色外貌详细描述，发型、瞳色、五官、服饰每一处细节，严禁使用 vague 词汇]. <Picture 1> serves solely as the visual identity and outfit reference, NOT as the initial frame.
<Subject 2> is the indoor background setting: directly retain the exact room layout, warm ambient lighting, background wall, spatial perspective, and cinematic depth of field from <Video 1>. Inherit only the lighting and environment, NOT the original character from <Video 1>.
<Video 1> is the primary motion reference video: use it as the sole reference for the dancing choreography, hip sways, arm movements, posture, rhythm, camera perspective, and framing.

summary:
[motion transfer + reference generation] The output video performs an exact 1:1 motion transfer based on <Video 1>. Replace the character in <Video 1> with <Subject 1> from <Picture 1>. Replicate 100% of the dancing movements, rhythm, body sway, and camera framing from <Video 1>. Do not add, omit, or alter any body movements or camera angles. Clean background, no UI or watermark.

retention_analysis:
<Subject 1> [Character Name]: facial identity, eyes, hair, costume fully preserved from <Picture 1>.
<Video 1>: dancing choreography, rhythm, body gestures, and camera framing fully preserved.

overall_soundscape:
Synchronized dynamic music and environment audio from <Video 1>. Clean stereo sound.

non_diegetic_music:
N/A
```

---

## 五、远程算力机（RTX 5090）模型与部署

### 1. 模型资产清单
- **UNET**：`minimax_h3_hybrid_fl2va_ref2va_b25-49-int8.safetensors`（20GB）
- **CLIP**：`qwen3vl_32b_minimax_h3_ultra_uncensored_heretic_int8_convrot.safetensors`（26GB）
- **LoRA**：`minimax_h3_fl2v_turbo_4step_v1.1_768p_comfyui_bf16.safetensors`（4步极速推理）
- **Video VAE**：`minimax_h3_video_vae_int8_convrot.safetensors`
- **Audio VAE**：`minimax_h3_audio_vae_fp32.safetensors`

### 2. 守护进程与自愈设计
在 Windows OpenSSH 环境下，直接通过终端启动的进程在 SSH 断开后会被杀死。必须使用 Windows 计划任务实现持久化：
```cmd
schtasks /create /tn "ComfyServer" /tr "C:\Users\lide\ComfyUI\start_comfy_daemon.bat" /sc once /st 23:59 /f
schtasks /run /tn "ComfyServer"
```
同时在调度脚本中内嵌非阻塞心跳探活 `wait_for_worker()`，当算力机因 Windows Update 重启或温控休眠时，脚本会自动挂起等待，绝不浪费重试次数。

---

## 六、批量执行与重组拼接 CLI

### 1. 批量动作迁移
```bash
python scripts/batch_runner.py
```
- 自动读取 `manifest.json`；
- 具备断点续传功能：根据 `batch_progress.json` 自动跳过已完成切片；
- 单段（73 帧）在 RTX 5090 上仅需约 5 分钟，完成后自动拉取至本地。

### 2. 最终视频重组
```bash
python scripts/concat_clips.py <output_clips_dir> <final_output.mp4>
```
使用 FFmpeg 的流复制（Stream Copy）模式无缝组装，零二次转码画质损耗，音画严丝合缝。

---

## 七、防踩坑指南 (Gotchas)

1. **画面宽高比对齐**：若源视频为竖屏 9:16（1080×1920），`MiniMaxH3ReferenceToVideo` 的宽高必须设为 `768×1344`（均为 32 的整数倍）；若设为横屏 `1344×768` 会导致构图严重变形。
2. **音视频轨道匹配**：`VHS_LoadVideo` 的输出第 2 端口（AUDIO）务必连入 `MiniMaxH3ReferenceToVideo` 的 `ref_video_audios.ref_video_audio_1`，确保原生音视频联合生成继承音乐节拍。
3. **消除播放器 UI**：原视频若带有 B 站进度条、播放器控件或 UP 主水印，必须在提示词与 summary 中明确标注“禁止渲染播放器 UI，自动重绘背景材质”，H3 扩散模型将自动剔除杂质。
