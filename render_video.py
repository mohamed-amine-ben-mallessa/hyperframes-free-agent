#!/usr/bin/env python3
"""
render_video.py — turn a storyboard JSON into a HyperFrames composition (index.html).

The storyboard is the deterministic contract between the LLM and the renderer.
The LLM only ever produces this JSON; this file owns all the (bug-prone) animation
code, so the output is reliable regardless of which model wrote the script.

Storyboard schema (see storyboard.schema.json):
{
  "title": "...",
  "format": "landscape" | "portrait",
  "duration": 60,
  "colors": { "canvas","ink","muted","accent" },   # optional, sensible defaults
  "scenes": [
    { "type": "hero",     "kicker": "...", "title": "...", "accentWord": "..." },
    { "type": "statement","title": "...", "accentWord": "..." },
    { "type": "cards",    "title": "...", "items": [ {"name","desc"}, ... ] },
    { "type": "stats",    "lead": "...", "stats": [ {"value":65,"label":"..."} ], "footer": "..." },
    { "type": "terminal", "kicker": "...", "lines": [ {"cmd":"..."} | {"ok":"..."} ] },
    { "type": "cta",      "title": "...", "links": ["...","..."] }
  ]
}
"""
import json, html, os, sys

DEFAULT_COLORS = {"canvas": "#F0EEE6", "ink": "#262624", "muted": "#6F6E66", "accent": "#D97757",
                  "hairline": "#DCD8CC", "surface": "#FAF9F5", "on_accent": "#FBF7F0"}

def esc(s):
    return html.escape(str(s))

def accentize(title, accent_word):
    """Wrap accentWord in <span class=accent> inside title (case-insensitive, first hit)."""
    if not accent_word:
        return esc(title)
    t = esc(title); aw = esc(accent_word)
    i = t.lower().find(aw.lower())
    if i < 0:
        return t
    return t[:i] + f'<span class="accent">{t[i:i+len(aw)]}</span>' + t[i+len(aw):]

def build(storyboard):
    portrait = storyboard.get("format", "landscape").startswith("p")
    W, H = (1080, 1920) if portrait else (1920, 1080)
    dur = float(storyboard.get("duration", 60))
    c = {**DEFAULT_COLORS, **storyboard.get("colors", {})}
    scenes = storyboard.get("scenes", [])
    n = max(1, len(scenes))
    # even time slots with a little hold; transitions overlap via enter/exit
    slot = dur / n

    # ---- render each scene's HTML ----
    scene_html = []
    for idx, sc in enumerate(scenes):
        t = sc.get("type")
        inner = ""
        if t in ("hero", "statement"):
            big = "mega" if t == "hero" else "hero"
            kick = f'<div class="mono kicker">{esc(sc["kicker"])}</div>' if sc.get("kicker") else ""
            inner = f'{kick}<div class="{big}">{accentize(sc.get("title",""), sc.get("accentWord"))}</div>'
        elif t == "cards":
            kick = f'<div class="mono kicker">{esc(sc["kicker"])}</div>' if sc.get("kicker") else ""
            cards = "".join(
                f'<div class="card"><div class="nm"><span class="dot"></span>{esc(it.get("name",""))}</div>'
                f'<div class="ds">{esc(it.get("desc",""))}</div></div>'
                for it in sc.get("items", [])[:3])
            inner = f'{kick}<div class="cards">{cards}</div>'
        elif t == "stats":
            lead = f'<div class="lead">{esc(sc["lead"])}</div>' if sc.get("lead") else ""
            stats = "".join(
                f'<div class="stat"><div class="v" data-count="{int(s.get("value",0))}">0</div>'
                f'<div class="k">{esc(s.get("label",""))}</div></div>'
                for s in sc.get("stats", [])[:4])
            foot = f'<div class="lead" style="margin-top:40px;font-size:26px">{esc(sc["footer"])}</div>' if sc.get("footer") else ""
            inner = f'{lead}<div class="stats">{stats}</div>{foot}'
        elif t == "terminal":
            kick = f'<div class="mono kicker">{esc(sc["kicker"])}</div>' if sc.get("kicker") else ""
            lines = ""
            for li in sc.get("lines", []):
                if "cmd" in li:
                    lines += f'<div class="tline"><span class="pmt">$</span> <span class="cmd">{esc(li["cmd"])}</span></div>'
                elif "ok" in li:
                    lines += f'<div class="tline"><span class="ok">{esc(li["ok"])}</span></div>'
            inner = (f'{kick}<div class="term-wrap"><div class="term-bar">'
                     f'<span class="tl r"></span><span class="tl y"></span><span class="tl g"></span>'
                     f'<span class="term-title">zsh</span></div><div class="term-body">{lines}</div></div>')
        elif t == "cta":
            links = "".join(f'<div class="repo"><span class="dot"></span>{esc(l)}</div>' for l in sc.get("links", []))
            inner = f'<div class="mega" style="margin-bottom:36px">{esc(sc.get("title",""))}</div><div class="repos">{links}</div>'
        else:
            inner = f'<div class="hero">{esc(sc.get("title",""))}</div>'
        scene_html.append(f'<section class="scene" id="s{idx}">{inner}</section>')

    # ---- build the GSAP timeline (deterministic, no overlap, no empty frames) ----
    js = ["const tl=gsap.timeline({paused:true});const eIn='power3.out';",
          "gsap.set('.scene',{opacity:0,visibility:'hidden',scale:1.06,filter:'blur(14px)'});",
          "function enter(s,t){tl.set(s,{visibility:'visible'},t).fromTo(s,{opacity:0,scale:1.06,filter:'blur(14px)'},{opacity:1,scale:1,filter:'blur(0px)',duration:0.55,ease:'power2.out'},t);}",
          "function exit(s,t){tl.to(s,{opacity:0,scale:0.94,filter:'blur(12px)',duration:0.5,ease:'power2.in'},t).set(s,{visibility:'hidden'},t+0.5);}",
          "function flash(t){tl.fromTo('#flash',{opacity:0},{opacity:0.5,duration:0.1},t).to('#flash',{opacity:0,duration:0.22},t+0.1);}",
          "tl.to('#grain',{backgroundPosition:'160px 160px',duration:%g,ease:'none'},0);" % dur]
    for idx, sc in enumerate(scenes):
        t0 = idx * slot
        tEnter = t0
        tExit = t0 + slot - 0.4
        sel = f"#s{idx}"
        if idx == 0:
            js.append(f"tl.set('{sel}',{{visibility:'visible',opacity:1,scale:1,filter:'blur(0px)'}},0);")
        else:
            js.append(f"enter('{sel}',{tEnter:.2f});")
        # per-element reveals
        js.append(f"tl.from('{sel} .kicker',{{opacity:0,y:14,duration:0.5}},{tEnter+0.1:.2f});")
        js.append(f"tl.from('{sel} .mega,{sel} .hero',{{opacity:0,y:30,duration:0.7,ease:eIn}},{tEnter+0.2:.2f});")
        if sc.get("type") == "cards":
            js.append(f"tl.from('{sel} .card',{{opacity:0,y:40,duration:0.55,stagger:0.2,ease:eIn}},{tEnter+0.4:.2f});")
        if sc.get("type") == "stats":
            js.append(f"tl.from('{sel} .stat',{{opacity:0,y:24,duration:0.5,stagger:0.12,ease:eIn}},{tEnter+0.4:.2f});")
            # count-up
            js.append(f"document.querySelectorAll('{sel} .v').forEach(el=>{{const o={{n:0}},tgt=+el.dataset.count;tl.to(o,{{n:tgt,duration:1.3,ease:'power2.out',onUpdate:()=>{{el.textContent=Math.round(o.n);}}}},{tEnter+0.6:.2f});}});")
        if sc.get("type") == "terminal":
            js.append(f"tl.from('{sel} .term-wrap',{{opacity:0,y:26,duration:0.55,ease:eIn}},{tEnter+0.3:.2f});")
            js.append(f"{{const L=document.querySelectorAll('{sel} .tline');L.forEach((el,i)=>tl.to(el,{{opacity:1,duration:0.25,ease:'none'}},{tEnter+0.6:.2f}+i*0.7));}}")
        if sc.get("type") == "cta":
            js.append(f"tl.from('{sel} .repo',{{opacity:0,y:24,duration:0.55,stagger:0.18,ease:'back.out(1.4)'}},{tEnter+0.7:.2f});")
        if idx < len(scenes) - 1:
            js.append(f"exit('{sel}',{tExit:.2f});")
            js.append(f"flash({tExit+0.35:.2f});")
    js.append("window.__timelines=window.__timelines||{};window.__timelines['main']=tl;")
    timeline = "\n".join(js)

    portrait_css = PORTRAIT_CSS if portrait else ""
    return HTML_TEMPLATE.format(W=W, H=H, dur=dur, c=c, scenes="\n".join(scene_html),
                                timeline=timeline, portrait_css=portrait_css,
                                title=esc(storyboard.get("title", "Launch")))

PORTRAIT_CSS = """
  html,body{width:1080px;height:1920px;} #stage{width:1080px;height:1920px;}
  .scene{padding:0 70px;} .hero{font-size:13vw;} .mega{font-size:20vw;}
  .cards{flex-direction:column;} .card{width:940px;}
  .stats{flex-direction:column;gap:40px;} .stat .v{font-size:18vw;}
"""

HTML_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width={W}, height={H}"/><title>{title}</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;700;800&family=Spline+Sans+Mono:wght@400;500;700&display=block" rel="stylesheet"/>
<style>
 *{{box-sizing:border-box;margin:0;padding:0;}}
 html,body{{width:{W}px;height:{H}px;overflow:hidden;background:{c[canvas]};color:{c[ink]};font-family:"Hanken Grotesk",system-ui,sans-serif;}}
 #stage{{position:relative;width:{W}px;height:{H}px;}}
 .scene{{position:absolute;inset:0;display:grid;place-content:center;text-align:center;padding:0 160px;opacity:0;visibility:hidden;will-change:opacity,transform,filter;}}
 .mono{{font-family:"Spline Sans Mono",monospace;letter-spacing:0.26em;text-transform:uppercase;}}
 .accent{{color:{c[accent]};}} .kicker{{font-size:22px;color:{c[accent]};margin-bottom:28px;}}
 .hero{{font-weight:800;font-size:8vw;line-height:1.0;letter-spacing:-0.025em;}}
 .mega{{font-weight:800;font-size:12vw;line-height:0.88;letter-spacing:-0.04em;}}
 .lead{{font-weight:500;font-size:32px;color:{c[muted]};line-height:1.4;}}
 .cards{{display:flex;gap:40px;justify-content:center;margin-top:44px;}}
 .card{{width:540px;padding:42px 46px;text-align:left;border-radius:22px;background:{c[surface]};border:1px solid {c[hairline]};}}
 .card .nm{{font-weight:800;font-size:40px;}} .card .ds{{font-weight:400;font-size:24px;color:{c[muted]};margin-top:12px;line-height:1.5;}}
 .dot{{display:inline-block;width:14px;height:14px;border-radius:50%;background:{c[accent]};margin-right:14px;vertical-align:middle;}}
 .stats{{display:flex;gap:66px;justify-content:center;margin-top:44px;}}
 .stat .v{{font-weight:800;font-size:6vw;line-height:1;}} .stat .k{{font-size:22px;color:{c[muted]};margin-top:10px;}}
 .term-wrap{{width:1220px;justify-self:center;border-radius:18px;overflow:hidden;box-shadow:0 30px 80px rgba(38,38,36,0.18);}}
 .term-bar{{background:#283276;height:50px;display:flex;align-items:center;padding:0 22px;gap:10px;}}
 .tl{{width:14px;height:14px;border-radius:50%;}} .tl.r{{background:#ff5f57;}} .tl.y{{background:#febc2e;}} .tl.g{{background:#28c840;}}
 .term-title{{color:#cfd3ea;font-family:"Spline Sans Mono",monospace;font-size:17px;margin-left:16px;}}
 .term-body{{background:#0f1222;padding:38px 42px;text-align:left;font-family:"Spline Sans Mono",monospace;font-size:25px;line-height:1.7;min-height:340px;}}
 .term-body .pmt{{color:#7c83b8;}} .term-body .cmd{{color:#eef0fb;}} .term-body .ok{{color:#5fd08a;}} .tline{{opacity:0;}}
 .repos{{display:flex;flex-direction:column;gap:16px;align-items:center;}}
 .repo{{font-family:"Spline Sans Mono",monospace;font-size:28px;color:{c[ink]};background:{c[surface]};border:1px solid {c[hairline]};border-radius:999px;padding:18px 38px;}}
 #vignette{{position:absolute;inset:0;pointer-events:none;z-index:60;background:radial-gradient(120% 120% at 50% 46%,transparent 56%,rgba(38,38,36,0.16) 100%);}}
 #grain{{position:absolute;inset:0;pointer-events:none;z-index:61;opacity:0.08;mix-blend-mode:multiply;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");}}
 #flash{{position:absolute;inset:0;z-index:58;pointer-events:none;opacity:0;background:{c[canvas]};}}
 {portrait_css}
</style></head><body>
<div id="stage" data-composition-id="main" data-start="0" data-duration="{dur}" data-width="{W}" data-height="{H}">
{scenes}
<div id="flash"></div><div id="vignette"></div><div id="grain"></div>
</div>
<script>
{timeline}
</script></body></html>"""

def main():
    if len(sys.argv) < 2:
        print("usage: python render_video.py <storyboard.json> [out.html]"); sys.exit(1)
    sb = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2] if len(sys.argv) > 2 else "index.html"
    open(out, "w", encoding="utf-8").write(build(sb))
    print(f"wrote {out} ({sb.get('format','landscape')}, {len(sb.get('scenes',[]))} scenes)")

if __name__ == "__main__":
    main()
