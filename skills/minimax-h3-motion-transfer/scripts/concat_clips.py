#!/usr/bin/env python3
"""Lossless Concatenator for Generated Video Clips.

Assembles all transferred clips in numeric order into a continuous,
synchronized final video file.
"""

import argparse
import glob
import os
import subprocess
import sys

def concat_clips(input_dir, output_file, pattern="*.mp4"):
    files = sorted(glob.glob(os.path.join(input_dir, pattern)))
    # filter out any non-clip files or preview files
    clips = [f for f in files if "preview" not in os.path.basename(f) and os.path.getsize(f) > 50000]

    if not clips:
        print(f"[!] No valid clips found in {input_dir}")
        sys.exit(1)

    print(f"[*] Found {len(clips)} clips to concatenate.")
    list_file = os.path.join(input_dir, "concat_manifest.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        output_file
    ]
    print(f"[*] Running ffmpeg concat...")
    subprocess.run(cmd, check=True)
    print(f"[+] Concatenated successfully: {output_file} ({os.path.getsize(output_file)} bytes)")

def main():
    parser = argparse.ArgumentParser(description="Concatenate transferred clips into final video")
    parser.add_argument("input_dir", help="Directory containing transferred mp4 clips")
    parser.add_argument("output_file", help="Destination final mp4 path")
    parser.add_argument("--pattern", default="*.mp4", help="Filename pattern")
    args = parser.parse_args()
    concat_clips(args.input_dir, args.output_file, args.pattern)

if __name__ == "__main__":
    main()
