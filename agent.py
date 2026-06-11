#!/usr/bin/env python3
"""
agent.py — prompt → launch-video storyboard, using a FREE OpenRouter model cascade.

Flow:
  prompt → LLM (free cascade, falls back across models) → validated storyboard JSON
         → render_video.build() → index.html → (you run) hyperframes render

The LLM only writes the STRUCTURED STORYBOARD (text/structure), never animation code,
so the result is reliable regardless of which free model answers.

Env: OPENROUTER_API_KEY
"""
import json, os, re, sys, time, urllib.request, urllib.error
import render_video

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free, capable models on OpenRouter — tried in order, fall back on error/ratelimit.
# Verified available on the free tier. Override with --model or the OPENROUTER_MODELS env (comma list).
FREE_CASCADE = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "google/gemma-4-31b-it:free",
    "openai/gpt-oss-120b:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
]

SYSTEM = """You are a launch-video art director. Given a product/topic, you output a STORYBOARD as strict JSON for a 60-second, no-voiceover video. You write ONLY the structure and copy — never code.

Rules:
- 8 to 11 scenes following a launch arc: hook → problem → reveal → what-it-is → proof/stats → demo → install → close/CTA.
- Copy is SHORT and punchy (a hero line is <= 9 words). One accent word per hero/statement scene.
- Use real, concrete details from the prompt. No lorem ipsum.
- Numbers in stats must be plausible integers.

Output JSON ONLY (no markdown), matching this shape:
{
 "title": str,
 "format": "landscape" | "portrait",
 "duration": 60,
 "colors": { "canvas":"#hex","ink":"#hex","muted":"#hex","accent":"#hex" },
 "scenes": [
   {"type":"hero","kicker":str,"title":str,"accentWord":str},
   {"type":"statement","title":str,"accentWord":str},
   {"type":"cards","kicker":str,"items":[{"name":str,"desc":str}]},
   {"type":"stats","lead":str,"stats":[{"value":int,"label":str}],"footer":str},
   {"type":"terminal","kicker":str,"lines":[{"cmd":str},{"ok":str}]},
   {"type":"cta","title":str,"links":[str]}
 ]
}
Pick scene types that fit the product. Keep colors warm (never pure #fff or #000)."""

def call_openrouter(model, prompt, api_key, timeout=90):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(OPENROUTER_URL, data=body, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/hyperframes-free-agent",
        "X-Title": "hyperframes-free-agent",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    if not d.get("choices"):
        raise ValueError(f"no choices: {str(d)[:120]}")
    msg = d["choices"][0].get("message", {})
    content = msg.get("content")
    # some models return reasoning + content, or content as a list of parts
    if isinstance(content, list):
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    if not content:
        content = msg.get("reasoning") or ""
    if not content:
        raise ValueError(f"empty content: {str(d['choices'][0])[:120]}")
    return content

def extract_json(text):
    """Be tolerant: strip code fences, grab the outermost {...}."""
    text = text.strip()
    text = re.sub(r"^```(json)?|```$", "", text, flags=re.MULTILINE).strip()
    i, j = text.find("{"), text.rfind("}")
    if i >= 0 and j > i:
        text = text[i:j+1]
    return json.loads(text)

def validate(sb):
    assert isinstance(sb.get("scenes"), list) and sb["scenes"], "no scenes"
    sb.setdefault("format", "landscape")
    sb.setdefault("duration", 60)
    for s in sb["scenes"]:
        assert "type" in s, "scene missing type"
    return sb

def generate_storyboard(prompt, api_key, fmt="landscape"):
    full_prompt = f"Format: {fmt}\nProduct / topic:\n{prompt}"
    last_err = None
    for model in FREE_CASCADE:
        try:
            print(f"  → {model}", file=sys.stderr)
            raw = call_openrouter(model, full_prompt, api_key)
            sb = validate(extract_json(raw))
            sb["format"] = fmt
            print(f"  ✓ storyboard from {model} ({len(sb['scenes'])} scenes)", file=sys.stderr)
            return sb
        except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, AssertionError, KeyError, ValueError, TypeError) as e:
            last_err = e
            print(f"  ✗ {model}: {type(e).__name__} {str(e)[:80]}", file=sys.stderr)
            time.sleep(1)
    raise RuntimeError(f"all free models failed; last error: {last_err}")

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Generate a HyperFrames launch video from a prompt (free models).")
    ap.add_argument("prompt", help="What the video is about (product, pitch, repo…).")
    ap.add_argument("--format", choices=["landscape", "portrait"], default="landscape")
    ap.add_argument("--out", default="index.html")
    ap.add_argument("--storyboard", default="storyboard.json", help="where to save the generated JSON")
    args = ap.parse_args()

    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        sys.exit("Set OPENROUTER_API_KEY (free key at openrouter.ai).")

    print("Generating storyboard with the free model cascade…", file=sys.stderr)
    sb = generate_storyboard(args.prompt, key, args.format)
    json.dump(sb, open(args.storyboard, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(args.out, "w", encoding="utf-8").write(render_video.build(sb))
    print(f"\n✓ storyboard → {args.storyboard}")
    print(f"✓ composition → {args.out}")
    print(f"\nNow render it:\n  hyperframes render --format mp4")

if __name__ == "__main__":
    main()
