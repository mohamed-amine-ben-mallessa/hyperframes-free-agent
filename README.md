<h1 align="center">🎥 HyperFrames Free Agent</h1>

<p align="center">
  <b>Type a prompt. Get a 60-second launch video. Powered by free AI models — no paid API, no cloud render.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/AI-OpenRouter%20free%20tier-6566F1?logo=openai&logoColor=white" alt="OpenRouter free">
  <img src="https://img.shields.io/badge/render-HyperFrames-blue" alt="HyperFrames">
  <img src="https://img.shields.io/badge/python-%E2%89%A53.8-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/output-MP4%20landscape%20%2F%20portrait-success" alt="Output">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="MIT">
</p>

<p align="center">
  <sub>
    🎬 <a href="https://hyperframes.heygen.com">HyperFrames</a> &nbsp;·&nbsp;
    🧠 <a href="https://openrouter.ai">OpenRouter</a> (free cascade) &nbsp;·&nbsp;
    🐤 <a href="https://claude.com/claude-code">Claude Code</a>-ready &nbsp;·&nbsp;
    🏢 built by <a href="https://sollea-ai.com">Sollea AI</a>
  </sub>
</p>

---

Every "AI video generator" wants your credit card. This one runs on **OpenRouter's free model tier** and renders locally with **HyperFrames** — the open-source HTML→video engine.

```bash
python agent.py "An open-source MCP server for the official France Travail job API"
hyperframes render --format mp4
```

→ a real, directed launch video: hero scale typography, an animated install terminal, count-up stats, cinematic zoom-blur transitions. No voice-over, no watermark, no per-render fee.

## Why it actually works (and most LLM-video tools don't)

The free models **never write animation code** — that's where they fail (broken GSAP timing, empty frames, overlaps). Instead:

```
prompt ──► free LLM cascade ──► STORYBOARD JSON ──► deterministic template ──► HyperFrames ──► MP4
           (writes structure)    (the contract)      (owns all the bug-prone     (local render)
                                                       animation code)
```

The LLM only does what it's good at — **structure and copy**. The renderer owns the timeline. Result: reliable output regardless of which model answered.

## The free model cascade

It tries capable **`:free`** OpenRouter models in order, falling back on rate-limits/errors so you almost always get a result:

```
llama-3.3-70b → qwen3-next-80b → gemma-4-31b → gpt-oss-120b → nemotron-3-super-120b → hermes-3-405b
```

All free. Bring your own free key from [openrouter.ai](https://openrouter.ai).

## Quick start

```bash
# 1. free key from openrouter.ai
export OPENROUTER_API_KEY=sk-or-...

# 2. prompt → storyboard → composition (index.html)
python agent.py "your product pitch here" --format landscape
#   --format portrait  for reels / TikTok / shorts (1080×1920)

# 3. render with HyperFrames
hyperframes render --format mp4      # or --format gif
```

You get `storyboard.json` (the editable plan) and `index.html` (the composition). Tweak the JSON and re-render anytime.

## What the agent produces

A storyboard with a launch arc the renderer understands:

| Scene type | Renders as |
|------------|-----------|
| `hero` / `statement` | Full-frame headline, one accent word |
| `cards` | Side-by-side (or stacked, portrait) feature cards |
| `stats` | Count-up numbers (real figures from your prompt) |
| `terminal` | Animated install terminal, typed line by line |
| `cta` | Closing line + link pills |

All deterministic, lint-clean, and render-safe.

## Requirements

- **Python ≥ 3.8** (standard library only — no pip install)
- A free **[OpenRouter API key](https://openrouter.ai)**
- The **[HyperFrames CLI](https://hyperframes.heygen.com)** (`npm i -g hyperframes`) for rendering

## Files

```
agent.py            prompt → free LLM cascade → validated storyboard JSON → index.html
render_video.py     storyboard JSON → deterministic HyperFrames composition (all the animation code)
storyboard.json     the generated, editable plan (LLM output)
```

## Make it yours

- Edit `storyboard.json` directly and re-run `render_video.py storyboard.json`.
- Add scene types in `render_video.py`.
- Swap the cascade via `FREE_CASCADE` in `agent.py`.

## Credits

Built on **[HyperFrames](https://hyperframes.heygen.com)** (HeyGen, open-source HTML→video) and **[OpenRouter](https://openrouter.ai)** free tier. Works great driven from **[Claude Code](https://claude.com/claude-code)** and any agent. Made by **[Sollea AI](https://sollea-ai.com)**.

> Independent open-source project. Not affiliated with HeyGen, OpenRouter, Anthropic, or France Travail. Logos and trademarks belong to their respective owners.

## License

MIT — see [LICENSE](./LICENSE).
