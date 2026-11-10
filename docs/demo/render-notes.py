import html, re, sys
src, dst = sys.argv[1], sys.argv[2]
out = []
for line in open(src).read().splitlines():
    e = html.escape(line)
    e = re.sub(r"\[(\d\d:\d\d)\]", r'<span class="t">\1</span>', e)
    e = re.sub(r"(frame_\d+\.jpg)", r'<code>\1</code>', e)
    e = re.sub(r"Said: &quot;(.*?)&quot;", r'<i>Said: “\1”</i>', e)
    if line.startswith("### "): out.append(f"<h3>{e[4:]}</h3>")
    elif line.startswith("## "): out.append(f"<h2>{e[3:]}</h2>")
    elif line.startswith("# "): out.append(f"<h1>{e[2:]}</h1>")
    elif re.match(r"\d+\. ", line):
        n, rest = e.split(". ", 1); out.append(f'<p class="i"><b>{n}</b><span>{rest}</span></p>')
    elif line.strip(): out.append(f"<p>{e}</p>")
css = """body{margin:0;background:#fff;font:15px/1.5 -apple-system,Helvetica,Arial,sans-serif;color:#1f2328}
.w{box-sizing:border-box;width:900px;padding:28px 36px}h1{font-size:20px;margin:0 0 6px;padding-bottom:10px;border-bottom:1px solid #d1d9e0}
h2{font-size:17px;margin:22px 0 4px;padding-bottom:6px;border-bottom:1px solid #d1d9e0}h3{font-size:14px;margin:14px 0 4px;color:#59636e}
.i{display:flex;gap:10px;margin:4px 0}.i b{min-width:18px;text-align:right}.t{font:12px ui-monospace,Menlo,monospace;background:#eef1fb;color:#2948c7;padding:1px 6px;border-radius:4px;margin-right:6px}
i{color:#59636e}code{font:12px ui-monospace,Menlo,monospace;background:#f1f3f5;padding:1px 5px;border-radius:4px}"""
open(dst,"w").write(f"<!doctype html><meta charset=utf-8><style>{css}</style><div class=w>{''.join(out)}</div>")
