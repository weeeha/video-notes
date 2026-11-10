#!/usr/bin/env python3
"""video-notes.py: turn a narrated screen recording into a timestamped transcript plus frames, locally.

  video-notes.py "<video>"                # transcript (reuses <video>.srt if present) + one frame per segment
  video-notes.py "<video>" --model turbo  # re-transcribe with a bigger whisper model when base is garbled
  video-notes.py "<video>" --every 10     # add a frame every N seconds on top of the segment frames
  video-notes.py "<video>" --max-frames 30
  video-notes.py "<video>" --max-row 5     # shorter rows, more frames, for fast talk over fast screen changes

Writes next to the video, in <stem>.notes/:
  transcript.srt        whisper output (or a copy of the existing .srt)
  transcript.md         one row per merged segment: n | mm:ss | what was said | frame file
  frame_mmss.jpg        1600px-wide stills at each segment start (+0.6 s so the cursor has landed)
Nothing leaves the machine: whisper runs on CPU from ~/.cache/whisper, ffmpeg does the frames.
The punch list itself is written by the model after it reads transcript.md and the frames.
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def duration(video):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video)])
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        sys.exit(f"ffprobe failed on {video}: {r.stderr.strip()}")


def has_audio(video):
    r = run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(video)])
    return "audio" in r.stdout


def transcribe(video, out, model):
    existing = video.with_suffix(".srt")
    target = out / "transcript.srt"
    if existing.exists() and model == "existing":
        shutil.copy(existing, target)
        return target, f"existing {existing.name}"
    if not shutil.which("whisper"):
        sys.exit("whisper CLI not on PATH (pip install openai-whisper); pass an .srt next to the video instead")
    r = run(["whisper", str(video), "--model", model, "--output_format", "srt", "--output_dir", str(out),
             "--fp16", "False", "--verbose", "False"])
    if r.returncode:
        sys.exit(f"whisper failed: {r.stderr.strip()[-800:]}")
    produced = out / (video.stem + ".srt")
    if produced.exists():
        produced.rename(target)
    return target, f"whisper --model {model}"


def parse_srt(path):
    txt = path.read_text(errors="replace")
    segs = []
    for block in re.split(r"\n\s*\n", txt.strip()):
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        m = re.match(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", lines[1] if "-->" in lines[1] else lines[0])
        if not m:
            continue
        h, mi, s, ms, h2, mi2, s2, ms2 = map(int, m.groups())
        start = h * 3600 + mi * 60 + s + ms / 1000
        end = h2 * 3600 + mi2 * 60 + s2 + ms2 / 1000
        text = " ".join(l.strip() for l in lines[2:] if "-->" not in l).strip()
        if text:
            segs.append([start, end, text])
    return segs


def merge(segs, gap=3.0, max_len=8.0):
    """Join whisper segments into rows. Each row gets one frame at its start, so a row must stay
    short enough that the screen has not moved on: max_len caps it (was 25 s, which let a short
    clip of steady talk collapse into one row and one frame)."""
    out = []
    for st, en, tx in segs:
        if out and st - out[-1][1] <= gap and en - out[-1][0] <= max_len:
            out[-1][1] = en
            out[-1][2] = (out[-1][2] + " " + tx).strip()
        else:
            out.append([st, en, tx])
    # collapse stutters: a segment whose text repeats the previous one is one note, not two
    dedup = []
    for seg in out:
        if dedup and seg[2].lower() == dedup[-1][2].lower():
            dedup[-1][1] = seg[1]
            continue
        dedup.append(seg)
    return dedup


def mmss(t):
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


def grab(video, t, out, width):
    name = out / f"frame_{mmss(t).replace(':', '')}.jpg"
    if name.exists():
        return name
    r = run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
             "-vf", f"scale={width}:-2", "-q:v", "3", str(name)])
    return name if name.exists() else None


def make_sheets(out, per=4, width=1200):
    """Tile frames 2x2 into sheet_NN.jpg so a first skim costs one read per four frames.
    Text in a sheet is for orientation only; read the single frame when a label must be read."""
    frames = sorted(out.glob("frame_*.jpg"))
    for f in out.glob("sheet_*.jpg"):
        f.unlink()
    for i in range(0, len(frames), per):
        chunk = frames[i:i + per]
        inputs = []
        for f in chunk:
            inputs += ["-i", str(f)]
        n = len(chunk)
        layout = "|".join(["0_0", "w0_0", "0_h0", "w0_h0"][:n])
        tail = "".join(f"[v{k}]" for k in range(n)) + (f"xstack=inputs={n}:layout={layout}[out]" if n > 1 else "null[out]")
        # each tile carries its mm:ss so an item can be traced back to its single frame
        labelled = "".join(
            f"[{k}:v]scale={width}:-2,drawtext=text='{chunk[k].stem[6:8]}\\:{chunk[k].stem[8:10]}':x=12:y=12:"
            f"fontsize=44:fontcolor=white:box=1:boxcolor=black@0.6[v{k}];" for k in range(n))
        plain = "".join(f"[{k}:v]scale={width}:-2[v{k}];" for k in range(n))
        name = out / f"sheet_{i // per + 1:02d}.jpg"
        r = run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", labelled + tail, "-map", "[out]", "-q:v", "3", str(name)])
        if r.returncode:  # drawtext needs fontconfig; fall back to an unlabelled grid
            run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", plain + tail, "-map", "[out]", "-q:v", "3", str(name)])
    return sorted(out.glob("sheet_*.jpg"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--model", default="existing", help="existing (reuse <video>.srt if present, else base.en) | base.en | small | medium | turbo")
    ap.add_argument("--every", type=float, default=0, help="extra frame every N seconds")
    ap.add_argument("--max-frames", type=int, default=40)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--max-row", type=float, default=8.0, help="longest merged transcript row in seconds; one frame per row")
    ap.add_argument("--sheet", action="store_true", help="also tile the frames 2x2 into sheet_NN.jpg for a first skim")
    ap.add_argument("--force", action="store_true", help="rebuild even when <stem>.notes/transcript.md is newer than the video")
    a = ap.parse_args()

    video = Path(a.video).expanduser().resolve()
    if not video.exists():
        sys.exit(f"no such file: {video}")
    out = video.with_name(video.stem + ".notes")
    out.mkdir(exist_ok=True)
    dur = duration(video)

    prior = out / "transcript.md"
    if prior.exists() and prior.stat().st_mtime > video.stat().st_mtime and not a.force and a.model == "existing":
        n_frames = len(list(out.glob("frame_*.jpg")))
        if a.sheet and not list(out.glob("sheet_*.jpg")):
            make_sheets(out)
        print(f"{prior}  (reused: newer than the video, {n_frames} frames; --force to rebuild)")
        return

    model = a.model
    if model == "existing" and not video.with_suffix(".srt").exists():
        model = "base.en"
    if not has_audio(video):
        segs, source = [], "no audio track"
    else:
        srt, source = transcribe(video, out, model)
        segs = merge(parse_srt(srt), max_len=a.max_row)

    times = [s[0] for s in segs]
    if a.every:
        times += [t for t in range(0, int(dur), int(a.every))]
    if not times:
        times = [t for t in range(0, int(dur), max(5, int(dur // 12) or 5))]
    times = sorted(set(round(t) for t in times))
    if len(times) > a.max_frames:
        step = len(times) / a.max_frames
        times = [times[int(i * step)] for i in range(a.max_frames)]

    frames = {}
    for t in times:
        f = grab(video, min(t + 0.6, dur - 0.1), out, a.width)
        if f:
            frames[t] = f.name

    md = [f"# {video.name}", "", f"- duration {mmss(dur)}  ·  transcript source: {source}  ·  frames: {len(frames)} in `{out.name}/`",
          "- rows are merged whisper segments; a frame is taken 0.6 s after each row starts", "",
          "| n | time | said | frame |", "|---|---|---|---|"]
    for i, (st, en, tx) in enumerate(segs, 1):
        fr = frames.get(round(st), "")
        md.append(f"| {i} | {mmss(st)} | {tx} | {fr} |")
    if not segs:
        md.append("| - | - | (no speech; frames only) | " + ", ".join(frames.values()) + " |")
    (out / "transcript.md").write_text("\n".join(md) + "\n")
    sheets = make_sheets(out) if a.sheet else []
    print(f"{out}/transcript.md  ({len(segs)} segments, {len(frames)} frames, {len(sheets)} sheets, {source})")


if __name__ == "__main__":
    main()
