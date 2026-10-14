#!/usr/bin/env python3
"""Video Chunk Splitter for MiniMax H3 Motion Transfer.

Splits any source video into segments strictly <= 80 frames (default 73 frames,
satisfying the H3 temporal grid 17k+5: 4*17+5=73), ensuring zero VRAM overflow.
Extracts both frame-accurate video clips and isolated lossless WAV audio.
"""

import argparse
import json
import os
import subprocess
import sys

def split_video(source_video, output_dir, frames_per_clip=73):
    os.makedirs(output_dir, exist_ok=True)

    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_frames,duration",
        "-of", "json", source_video
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    probe_data = json.loads(res.stdout)
    vstream = probe_data["streams"][0]

    width = int(vstream["width"])
    height = int(vstream["height"])
    fps_parts = vstream["r_frame_rate"].split("/")
    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else float(fps_parts[0])
    total_frames = int(vstream.get("nb_frames", 0))
    duration = float(vstream.get("duration", 0))

    if total_frames == 0 and duration > 0:
        total_frames = int(round(duration * fps))

    print(f"[*] Source: {width}x{height} @ {fps:.2f} fps, {total_frames} frames ({duration:.2f}s)")
    total_clips = (total_frames + frames_per_clip - 1) // frames_per_clip
    print(f"[*] Target chunk size: {frames_per_clip} frames (Total: {total_clips} clips)")

    manifest = []
    concat_lines = []

    for idx in range(total_clips):
        clip_num = idx + 1
        start_frame = idx * frames_per_clip
        end_frame = min((idx + 1) * frames_per_clip, total_frames)
        clip_frames = end_frame - start_frame

        start_time = start_frame / fps
        clip_duration = clip_frames / fps

        clip_filename = f"clip_{clip_num:03d}.mp4"
        clip_path = os.path.join(output_dir, clip_filename)
        audio_filename = f"audio_{clip_num:03d}.wav"
        audio_path = os.path.join(output_dir, audio_filename)

        # Cut video clip with audio
        ff_cmd = [
            "ffmpeg", "-y",
            "-ss", f"{start_time:.4f}",
            "-i", source_video,
            "-t", f"{clip_duration:.4f}",
            "-c:v", "libx264", "-crf", "17", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            clip_path
        ]
        subprocess.run(ff_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Isolated WAV
        ff_audio = [
            "ffmpeg", "-y",
            "-ss", f"{start_time:.4f}",
            "-i", source_video,
            "-t", f"{clip_duration:.4f}",
            "-vn", "-acodec", "pcm_s16le", "-ar", "48000",
            audio_path
        ]
        subprocess.run(ff_audio, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        manifest.append({
            "index": clip_num,
            "start_frame": start_frame,
            "end_frame": end_frame,
            "frame_count": clip_frames,
            "start_time": round(start_time, 4),
            "duration": round(clip_duration, 4),
            "video_file": clip_filename,
            "audio_file": audio_filename
        })
        concat_lines.append(f"file '{clip_filename}'")

        if clip_num % 10 == 0 or clip_num == total_clips:
            print(f"[+] Processed clip {clip_num}/{total_clips}")

    manifest_file = os.path.join(output_dir, "manifest.json")
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    concat_file = os.path.join(output_dir, "concat_list.txt")
    with open(concat_file, "w", encoding="utf-8") as f:
        f.write("\n".join(concat_lines) + "\n")

    print(f"[+] All clips generated in {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="Split video into H3 motion transfer chunks")
    parser.add_argument("source", help="Source MP4 file")
    parser.add_argument("output", help="Output directory")
    parser.add_argument("--frames", type=int, default=73, help="Frames per segment (default: 73, <= 80)")
    args = parser.parse_args()
    split_video(args.source, args.output, args.frames)

if __name__ == "__main__":
    main()
