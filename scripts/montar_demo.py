"""Turn grabar_demo.mjs's frames and timeline into a video with the Catrina's voice.

Each frame lasts until the next one (screencasts have irregular timing), and each
calavera's MP3 is placed at the second its audio element started playing.

Usage: python3 scripts/montar_demo.py <rec-dir> <site-dir> <out.mp4>
"""

import json
import os
import subprocess
import sys


def main(rec: str, site: str, out: str) -> None:
    with open(os.path.join(rec, "timeline.json")) as f:
        tl = json.load(f)
    frames = [fr for fr in tl["frames"] if fr["t"] >= tl["start"] - 0.5]
    if not frames:
        sys.exit("no frames recorded")

    # Concat list with per-frame durations; the last frame holds until the end.
    lines = []
    for i, fr in enumerate(frames):
        nxt = frames[i + 1]["t"] if i + 1 < len(frames) else tl["end"]
        lines.append(f"file 'frames/{fr['file']}'\nduration {max(0.001, nxt - fr['t']):.3f}")
    lines.append(f"file 'frames/{frames[-1]['file']}'")  # concat demuxer needs the last file twice
    with open(os.path.join(rec, "frames.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")

    t0 = frames[0]["t"]
    plays = [e for e in tl["events"] if e["kind"] == "play"]
    inputs, filters = [], []
    for k, e in enumerate(plays):
        inputs += ["-i", os.path.join(site, "audio", f"calavera-{e['index'] + 1:02d}.mp3")]
        ms = max(0, int((e["t"] - t0) * 1000))
        filters.append(f"[{k + 1}:a]adelay={ms}|{ms}[a{k}]")
    mix = "".join(f"[a{k}]" for k in range(len(plays)))
    filters.append(f"{mix}amix=inputs={len(plays)}:normalize=0,apad[voz]")

    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y",
         "-f", "concat", "-safe", "0", "-i", os.path.join(rec, "frames.txt"), *inputs,
         "-filter_complex", ";".join(filters),
         "-map", "0:v", "-map", "[voz]",
         "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-c:a", "aac", "-b:a", "192k", "-shortest", out],
        check=True,
    )  # fmt: skip
    print("saved", out)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
