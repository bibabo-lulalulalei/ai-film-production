# -*- coding: utf-8 -*-
"""Extract a frame from a video with ffmpeg.

Usage:
  python tools/video/ffmpeg_tool.py frame <video> <out.png> [--at S.SS | --tail | --first]
        -> prints the output image path (default: --first)

Requires ffmpeg on PATH (https://www.gyan.dev/ffmpeg/builds/).
Used by the tail-frame chain: after a shot renders, extract its final frame
with --tail to become the next shot's first-frame anchor.
"""
import argparse
import os
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def die(msg, code=1):
    print(f"ERROR: {msg}")
    sys.exit(code)


def extract_frame(path, out, mode, at=None):
    if not os.path.isfile(path):
        die(f"文件不存在: {path}")
    out_dir = os.path.dirname(os.path.abspath(out))
    os.makedirs(out_dir, exist_ok=True)

    if mode == "tail":
        # last decoded frame near EOF (h3.md §6 convention)
        cmd = ["ffmpeg", "-y", "-sseof", "-0.1", "-i", path,
               "-frames:v", "1", out]
    elif mode == "at":
        # -ss before -i = fast seek to the closest keyframe
        cmd = ["ffmpeg", "-y", "-ss", str(at), "-i", path,
               "-frames:v", "1", out]
    else:  # first
        cmd = ["ffmpeg", "-y", "-i", path, "-frames:v", "1", out]

    p = run(cmd)
    if p.returncode != 0 or not os.path.exists(out):
        die(f"抽帧失败: {p.stderr.strip()}")
    return out


def main():
    ap = argparse.ArgumentParser(description="ffmpeg 抽帧工具")
    sub = ap.add_subparsers(dest="command", required=True)

    p_frame = sub.add_parser("frame", help="抽取一帧为图片")
    p_frame.add_argument("video")
    p_frame.add_argument("out", help="输出图片路径，如 09-takes/S001/S001_tail.png")
    where = p_frame.add_mutually_exclusive_group()
    where.add_argument("--at", help="指定时间点（秒）")
    where.add_argument("--tail", action="store_true", help="片尾最后一帧")
    where.add_argument("--first", action="store_true", help="首帧（默认）")

    args = ap.parse_args()
    mode = "tail" if args.tail else ("at" if args.at is not None else "first")
    print(extract_frame(args.video, args.out, mode, args.at))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main()
