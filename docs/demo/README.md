# Demo

Rebuilds the README images on macOS (uses `say` and Google Chrome headless).

```bash
./make-demo.sh
```

```bash
python3 ../../skills/video-notes/video-notes.py out/demo-feedback.mp4 --sheet --every 4   # --every 4 matches the README images; not needed since --max-row
```

`app.html` is a made-up sample app. `demo-feedback.notes.md` is the punch list written from that run; `render-notes.py` turns it into the HTML used for `docs/img/punch-list.png`.
