#!/usr/bin/env python3
"""Webページを自動で操作して、字幕付きの「使い方動画」を録画する。

使い方:
    python3 scripts/record_guide.py guides/sample.json
    → out/sample.mp4 ができる

台本（JSON）の形:
{
  "url": "https://example.com",          最初に開くページ
  "size": [1280, 800],                   画面の大きさ（省略可）
  "steps": [
    {"caption": "字幕", "do": "wait"},
    {"caption": "字幕", "do": "click", "target": "text=料金", "mark": "box"},
    {"caption": "字幕", "do": "hover", "target": "#menu", "mark": "ring"},
    {"caption": "字幕", "do": "point", "target": ".price"},            カーソルを置くだけ
    {"caption": "字幕", "do": "scroll", "y": 600},                    下へ600px（上は -600）
    {"caption": "字幕", "do": "scroll", "target": "#faq"},            その場所まで
    {"caption": "字幕", "do": "type", "target": "input[type=search]", "text": "ボタン"},
    {"caption": "字幕", "do": "key", "key": "Escape"},
    {"caption": "字幕", "do": "goto", "url": "https://example.com/about"}
  ]
}

- target は Playwright の書き方（"text=見出しの文字"、CSSセレクタ、"role=button[name=送る]" など）
- mark: "box"（四角で囲む）/ "ring"（青い丸）/ "none"。click の標準は ring、hover・point は box
- sec: その手順で止まる秒数。省略すると字幕の長さから決める
- caption を省くと、前の字幕を出したまま進む。"" にすると字幕を消す
"""
import json, math, sys, time, shutil, subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent

OVERLAY_JS = r"""
(() => {
  if (window.__g) return;
  const css = `
  #__g{position:fixed;inset:0;pointer-events:none;z-index:2147483647;font-family:"Hiragino Sans","Hiragino Kaku Gothic ProN","Noto Sans JP",sans-serif}
  #__g .cur{position:absolute;left:0;top:0;width:28px;height:28px;transform:translate(-200px,-200px);transition:transform var(--t,700ms) cubic-bezier(.65,0,.35,1);filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))}
  #__g .ring{position:absolute;width:26px;height:26px;margin:-13px 0 0 -13px;border-radius:50%;background:rgba(80,120,255,.45);border:2px solid rgba(60,100,255,.9);opacity:0;transform:scale(.4);transition:opacity .2s,transform .35s cubic-bezier(.22,1,.36,1)}
  #__g .ring.on{opacity:1;transform:scale(1)}
  #__g .box{position:absolute;border:3px solid #F0562E;border-radius:10px;box-shadow:0 0 0 6px rgba(240,86,46,.18);opacity:0;transition:opacity .25s}
  #__g .box.on{opacity:1}
  #__g .cap{position:absolute;left:50%;bottom:28px;transform:translate(-50%,8px);max-width:78%;padding:12px 22px;border-radius:12px;background:rgba(28,28,30,.88);color:#fff;font-size:22px;font-weight:700;line-height:1.5;text-align:center;letter-spacing:.02em;opacity:0;transition:opacity .3s,transform .3s cubic-bezier(.22,1,.36,1)}
  #__g .cap.on{opacity:1;transform:translate(-50%,0)}`;
  const mount = () => {
    if (document.getElementById('__g')) return;
    const st = document.createElement('style'); st.textContent = css;
    const g = document.createElement('div'); g.id = '__g';
    g.innerHTML = `<svg class="cur" viewBox="0 0 24 24"><path d="M4 2l15 11-6.5 1.2L16 21l-3 1.4-3.4-6.8L4 20z" fill="#111" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/></svg><div class="ring"></div><div class="box"></div><div class="cap"></div>`;
    document.documentElement.append(st, g);
    const s = window.__gstate || {x: -200, y: -200, cap: ''};
    const cur = g.querySelector('.cur'); cur.style.setProperty('--t', '0ms');
    cur.style.transform = `translate(${s.x}px,${s.y}px)`;
    if (s.cap) { const c = g.querySelector('.cap'); c.textContent = s.cap; c.classList.add('on'); }
  };
  window.__g = {
    mount,
    move(x, y, ms) { mount(); const c = document.querySelector('#__g .cur'); c.style.setProperty('--t', ms + 'ms'); c.style.transform = `translate(${x}px,${y}px)`; },
    ring(x, y) { const r = document.querySelector('#__g .ring'); r.style.left = x + 'px'; r.style.top = y + 'px'; r.classList.remove('on'); void r.offsetWidth; r.classList.add('on'); },
    box(b) { const e = document.querySelector('#__g .box'); const p = 6; Object.assign(e.style, {left: (b.x - p) + 'px', top: (b.y - p) + 'px', width: (b.width + p * 2) + 'px', height: (b.height + p * 2) + 'px'}); e.classList.add('on'); },
    clear() { document.querySelectorAll('#__g .ring,#__g .box').forEach(e => e.classList.remove('on')); },
    cap(t) { mount(); const c = document.querySelector('#__g .cap'); if (!t) { c.classList.remove('on'); return; } if (c.textContent === t && c.classList.contains('on')) return; c.classList.remove('on'); setTimeout(() => { c.textContent = t; c.classList.add('on'); }, 120); },
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
})();
"""


def hold_seconds(caption: str) -> float:
    # 日本語で1秒に約7文字読める前提。最低2.2秒
    return max(2.2, len(caption or "") / 7 + 0.8)


def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("ffmpeg が見つかりません。`pip install imageio-ffmpeg` か `brew install ffmpeg` を実行してください")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    spec_path = Path(sys.argv[1])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    W, H = spec.get("size", [1280, 800])
    out_dir = ROOT / "out"; out_dir.mkdir(exist_ok=True)
    tmp = out_dir / "_raw"; shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir()
    name = spec_path.stem

    state = {"x": W * 0.55, "y": H * 0.55, "cap": ""}

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception:
            browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=1,
                                  record_video_dir=str(tmp), record_video_size={"width": W, "height": H},
                                  locale="ja-JP")
        ctx.add_init_script(OVERLAY_JS)
        t0 = time.time()
        page = ctx.new_page()
        page.goto(spec["url"], wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(800)

        def sync_state():
            page.evaluate("s => { window.__gstate = s; }", state)

        def overlay(js, *args):
            page.evaluate("() => window.__g && window.__g.mount()")
            page.evaluate(js, *args) if args else page.evaluate(js)

        overlay("([x,y]) => window.__g.move(x,y,0)", [state["x"], state["y"]])
        page.wait_for_timeout(300)
        start_at = time.time() - t0  # ここから動画を使う

        def move_to(x, y):
            d = math.hypot(x - state["x"], y - state["y"])
            ms = int(min(1100, max(450, d * 1.1)))
            overlay("([x,y,ms]) => window.__g.move(x,y,ms)", [x, y, ms])
            state["x"], state["y"] = x, y; sync_state()
            page.wait_for_timeout(ms + 120)

        def locate(target):
            loc = page.locator(target).first
            loc.scroll_into_view_if_needed(timeout=10000)
            page.wait_for_timeout(250)
            b = loc.bounding_box()
            if not b:
                sys.exit(f"見つかりません: {target}")
            return loc, b

        for i, st in enumerate(spec["steps"], 1):
            do = st.get("do", "wait")
            if "caption" in st:
                state["cap"] = st["caption"]; sync_state()
                overlay("t => window.__g.cap(t)", st["caption"])
            overlay("() => window.__g.clear()")
            hold = st.get("sec", hold_seconds(st.get("caption", "")))
            t_step = time.time()

            if do in ("click", "hover", "point", "type"):
                loc, b = locate(st["target"])
                cx, cy = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
                move_to(cx, cy)
                mark = st.get("mark", "ring" if do == "click" else "box")
                if mark == "box":
                    overlay("b => window.__g.box(b)", b)
                elif mark == "ring":
                    overlay("([x,y]) => window.__g.ring(x,y)", [cx, cy])
                page.wait_for_timeout(450)
                if do == "hover":
                    loc.hover()
                elif do == "click":
                    loc.click()
                    page.wait_for_timeout(300)
                    try: page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception: pass
                elif do == "type":
                    loc.click(); loc.press_sequentially(st["text"], delay=110)
            elif do == "scroll":
                if "target" in st:
                    y = page.locator(st["target"]).first.evaluate("e => e.getBoundingClientRect().top + window.scrollY - 80")
                    page.evaluate("y => window.scrollTo({top:y, behavior:'smooth'})", y)
                else:
                    page.evaluate("d => window.scrollBy({top:d, behavior:'smooth'})", st.get("y", 600))
                page.wait_for_timeout(900)
            elif do == "key":
                page.keyboard.press(st["key"])
            elif do == "goto":
                page.goto(st["url"], wait_until="networkidle", timeout=60000)
            elif do != "wait":
                sys.exit(f"手順{i}: do の値が不明です: {do}")

            rest = hold - (time.time() - t_step)
            if rest > 0:
                page.wait_for_timeout(int(rest * 1000))
            print(f"  {i:>2}. {do:<6} {st.get('caption', '')}")

        overlay("() => { window.__g.clear(); window.__g.cap(''); }")
        page.wait_for_timeout(900)
        video = page.video.path()
        ctx.close(); browser.close()

    out = out_dir / f"{name}.mp4"
    subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", f"{start_at:.2f}", "-i", str(video),
                    "-vf", "scale=1920:-2:flags=lanczos,fps=30", "-c:v", "libx264", "-preset", "slow",
                    "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"完成: {out}")


if __name__ == "__main__":
    main()
