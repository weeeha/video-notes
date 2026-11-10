---
name: video-notes
description: Turn a narrated screen recording, a product demo or any video the user points at into a timestamped, numbered punch list with stills, all on this machine. Use when the user says "check the video file", "I left feedback as a video", "I recorded feedback", "watch this video", "analyze this demo", or drops a .mov, .mp4 or .webm path.
---

# Video Notes

The user records feedback as a screen recording while talking through it: one pass, a few
minutes, often repeating a point when the cursor lags. The deliverable is a punch list another
session can execute without watching the video. Whisper and ffmpeg run locally; no video or
audio is sent to a cloud speech or vision API.

## Steps

1. **Run the helper** (it sits next to this file).
   ```bash
   python3 "<this skill's folder>/video-notes.py" "<video>"
   ```
   It reuses `<video>.srt` when one sits next to the file, otherwise runs `whisper --model base.en`
   on CPU (about 2.5 min per 5 min of video on an Apple Silicon laptop). Output lands in
   `<stem>.notes/`: `transcript.md` (one row per merged segment with a frame name) and 1600px
   stills. When `<stem>.notes/` is already newer than the video it is reused as is; `--force`
   rebuilds, `--model turbo` when the base transcript is garbled, `--every 10` for a demo with no
   narration, `--sheet` for 2x2 contact sheets, `--max-frames 40` default.
2. **Read `transcript.md`, then the frames.** With `--sheet`, skim `sheet_NN.jpg` first (four frames
   per read; tiles run left to right, top to bottom, in frame order, so sheet 01 holds frames 1 to 4
   and its top-left tile is the earliest), then read the single frame for every row whose words point
   at the screen ("this area", "here", "these two icons") or whose text must be read. A sheet
   locates; only a single frame is evidence for a label or a size.
3. **Write `<stem>.notes.md` next to the video**, by absolute path, whatever the session's working
   directory is. Shape:
   ```
   # <video name> · <recorded date> · <duration> · <app or URL visible in the frames>

   ## Punch list
   ### <screen region, named as it reads on screen: Left rail, Header, Settings panel>
   1. [mm:ss] <imperative fix in one sentence>. Said: "<short verbatim>". Frame: frame_mmss.jpg
   2. ...

   ## Parked
   <items marked "later", "eventually", "not now", same line shape>

   ## Unclear
   <one line per item that needs the user's answer>
   ```
   Numbering runs through the whole list, so the user can reply "3 and 7". Regions follow the
   order they were visited. A repeated note is one item, with "said 3 times" appended when the
   repetition is the point.
4. **Reply with** the file path, the region headers with item counts, and the first three items.
   Ask nothing unless Unclear has entries.
5. **When the repo that renders the screen is open**, add `## Where in code`: item number to
   file path, found by grepping the component names and labels visible in the frames. Skip the
   section when there is no repo; never guess a path.

## Rules

- Unreadable text in a still is re-grabbed, never inferred: `--width 2400`, or an ffmpeg crop of
  the region.
- The `.notes/` folder and `.notes.md` stay next to the video. Inside a repo that folder must be
  ignored (`.git/info/exclude`), so a large recording never enters git.
- Competitor or product demo: same steps, and the list reads "what they do" instead of "fix".
- Transcription runs with the local Whisper models in `~/.cache/whisper`. No cloud speech API,
  no vision API; the session model reads the stills.

## Done check
- [ ] `transcript.md` produced and every frame read before an item was written
- [ ] `<stem>.notes.md` written: global numbering, regions in visit order, timestamp and frame on every item
- [ ] Repeats collapsed, Parked and Unclear separated from the punch list
- [ ] No video or audio sent off the machine
