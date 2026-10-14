#!/usr/bin/env python3
"""Generic Batch Runner for MiniMax H3 Motion Transfer.

Handles uploading clips, triggering H3 4-step Turbo inference on remote RTX 5090 ComfyUI,
monitoring progress, auto-recovering from worker sleep/cooling, downloading results,
and maintaining persistent checkpoint progress.
"""

import argparse
import glob
import json
import os
import sys
import time
import urllib.request
import urllib.error

sys.path.insert(0, "/home/lide/.agents/skills/ai-video-character-pipeline/scripts")
import remote_bridge

def build_workflow(ref_image_name, clip_filename, frame_count, prompt_text, seed=42001, width=768, height=1344):
    return {
        "1": {
            "inputs": {"image": ref_image_name},
            "class_type": "LoadImage"
        },
        "2": {
            "inputs": {
                "video": f"hinata_clips/{clip_filename}",
                "force_rate": 24.0,
                "force_size": "Disabled",
                "custom_width": 0,
                "custom_height": 0,
                "frame_load_cap": frame_count,
                "skip_first_frames": 0,
                "select_every_nth": 1
            },
            "class_type": "VHS_LoadVideo"
        },
        "10": {
            "inputs": {
                "unet_name": "minimax_h3_hybrid_fl2va_ref2va_b25-49-int8.safetensors",
                "weight_dtype": "default"
            },
            "class_type": "UNETLoader"
        },
        "11": {
            "inputs": {
                "clip_name": "qwen3vl_32b_minimax_h3_ultra_uncensored_heretic_int8_convrot.safetensors",
                "type": "minimax",
                "device": "default"
            },
            "class_type": "CLIPLoader"
        },
        "12": {
            "inputs": {"vae_name": "minimax_h3_video_vae_int8_convrot.safetensors"},
            "class_type": "VAELoader"
        },
        "13": {
            "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"},
            "class_type": "VAELoader"
        },
        "14": {
            "inputs": {
                "lora_name": "minimax_h3_fl2v_turbo_4step_v1.1_768p_comfyui_bf16.safetensors",
                "strength_model": 1.0,
                "model": ["10", 0]
            },
            "class_type": "LoraLoaderModelOnly"
        },
        "20": {
            "inputs": {
                "clip": ["11", 0],
                "vae": ["12", 0],
                "audio_vae": ["13", 0],
                "ref_image_size": "match",
                "width": width,
                "height": height,
                "length": frame_count,
                "ref_images.ref_image_1": ["1", 0],
                "ref_videos.ref_video_1": ["2", 0],
                "ref_video_audios.ref_video_audio_1": ["2", 2],
                "prompt": prompt_text
            },
            "class_type": "MiniMaxH3ReferenceToVideo"
        },
        "30": {
            "inputs": {"sampler_name": "res_multistep"},
            "class_type": "KSamplerSelect"
        },
        "31": {
            "inputs": {
                "scheduler": "simple",
                "steps": 4,
                "denoise": 1.0,
                "model": ["14", 0]
            },
            "class_type": "BasicScheduler"
        },
        "32": {
            "inputs": {
                "model": ["14", 0],
                "conditioning": ["20", 0]
            },
            "class_type": "BasicGuider"
        },
        "33": {
            "inputs": {"noise_seed": seed},
            "class_type": "RandomNoise"
        },
        "34": {
            "inputs": {
                "noise": ["33", 0],
                "guider": ["32", 0],
                "sampler": ["30", 0],
                "sigmas": ["31", 0],
                "latent_image": ["20", 1]
            },
            "class_type": "SamplerCustomAdvanced"
        },
        "40": {
            "inputs": {
                "samples": ["34", 0],
                "vae": ["12", 0]
            },
            "class_type": "VAEDecode"
        },
        "41": {
            "inputs": {
                "samples": ["34", 0],
                "vae": ["13", 0]
            },
            "class_type": "VAEDecodeAudio"
        },
        "50": {
            "inputs": {
                "fps": 24.0,
                "bit_depth": 8,
                "color_space": "sRGB",
                "codec": "none",
                "images": ["40", 0],
                "audio": ["41", 0]
            },
            "class_type": "CreateVideo"
        },
        "51": {
            "inputs": {
                "filename_prefix": f"motion_transfer/{clip_filename.replace('.mp4', '')}",
                "format": "auto",
                "codec": "auto",
                "video": ["50", 0]
            },
            "class_type": "SaveVideo"
        }
    }

def wait_for_worker(comfy_host):
    while True:
        try:
            req = urllib.request.urlopen(f"http://{comfy_host}/system_stats", timeout=4)
            if req.status == 200:
                return True
        except Exception:
            pass
        print(f"[*] Worker {comfy_host} is offline / cooling down. Waiting 15s...", flush=True)
        time.sleep(15)

def run_clip(comfy_host, clips_dir, output_dir, ref_image_name, prompt_text, clip_num, total_clips, frame_count, width=768, height=1344):
    clip_filename = f"clip_{clip_num:03d}.mp4"
    local_src = os.path.join(clips_dir, clip_filename)
    local_dst = os.path.join(output_dir, f"transferred_{clip_num:03d}.mp4")
    remote_src = f"C:/Users/lide/ComfyUI/input/hinata_clips/{clip_filename}"

    if os.path.exists(local_dst) and os.path.getsize(local_dst) > 100000:
        print(f"[{clip_num}/{total_clips}] {local_dst} exists. Skipping.", flush=True)
        return True

    print(f"\n[*] Processing [{clip_num}/{total_clips}] {clip_filename} ({frame_count} frames)", flush=True)
    t0 = time.time()

    remote_bridge.cmd_upload(type("Args", (), {"local": local_src, "remote": remote_src})())

    seed = 42000 + clip_num
    prompt_wf = build_workflow(ref_image_name, clip_filename, frame_count, prompt_text, seed, width, height)
    payload = {"prompt": prompt_wf}

    req = urllib.request.Request(
        f"http://{comfy_host}/prompt",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read())
        prompt_id = res.get("prompt_id")
    print(f"[+] Prompt submitted! ID: {prompt_id}", flush=True)

    poll_start = time.time()
    out_filename = None
    subfolder = "motion_transfer"

    while True:
        time.sleep(5)
        try:
            h_req = urllib.request.urlopen(f"http://{comfy_host}/history/{prompt_id}", timeout=10)
            h_data = json.loads(h_req.read())
            if prompt_id in h_data:
                item = h_data[prompt_id]
                outputs = item.get("outputs", {})
                if "51" in outputs and "images" in outputs["51"]:
                    out_info = outputs["51"]["images"][0]
                    out_filename = out_info["filename"]
                    subfolder = out_info.get("subfolder", "motion_transfer")
                    print(f"[+] Generation complete: {out_filename}", flush=True)
                    break
        except Exception:
            pass

        elapsed = time.time() - poll_start
        if int(elapsed) % 20 == 0:
            print(f"[*] Waiting on prompt {prompt_id}... ({int(elapsed)}s)", flush=True)
        if elapsed > 600:
            raise TimeoutError(f"Job {prompt_id} timed out after 600s")

    remote_out = f"C:/Users/lide/ComfyUI/output/{subfolder}/{out_filename}".replace("//", "/")
    print(f"[*] Downloading: {remote_out} -> {local_dst}", flush=True)
    remote_bridge.cmd_download(type("Args", (), {"remote": remote_out, "local": local_dst})())
    print(f"[+] Finished {clip_filename} in {time.time()-t0:.1f}s!", flush=True)
    return True
