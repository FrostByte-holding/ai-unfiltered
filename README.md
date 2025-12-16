# AI Unfiltered

Raw AI news. No fluff. Updated every 4 hours.

## What is this?

An automated AI news aggregator that:
- Fetches from 25+ curated RSS feeds every 4 hours
- Covers arXiv papers, Chinese AI, LLM news, and industry updates
- Generates a minimal, fast, static site
- Runs entirely on GitHub Actions (free)
- Costs $0 to operate

## Live Site

**https://frostbyte-holding.github.io/ai-unfiltered/**

## How it works

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  GitHub Action  │────▶│  fetch_rss.py   │────▶│  SQLite DB      │
│  (every 4 hrs)  │     │  (25+ feeds)    │     │  (articles.db)  │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  GitHub Pages   │◀────│  build_site.py  │◀────│  Static HTML    │
│  (free hosting) │     │  (generator)    │     │  (docs/)        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Categories

- **chinese-ai** - DeepSeek, Zhipu, Baidu, Alibaba, ByteDance, etc.
- **research** - arXiv papers (cs.AI, cs.LG, cs.CL)
- **llm** - Large language model news and developments
- **industry** - General AI industry news
- **company** - Official company blogs (OpenAI, Google, DeepMind, etc.)
- **community** - Reddit discussions

## Feeds

See `feeds.yaml` for the full list of sources.

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Fetch latest articles
python scripts/fetch_rss.py

# Build the site
python scripts/build_site.py

# View locally
cd docs && python -m http.server 8000
```

## Adding/Removing Feeds

Edit `feeds.yaml`:

```yaml
feeds:
  - name: "New Source"
    url: "https://example.com/feed.xml"
    category: "industry"  # or: chinese-ai, research, llm, company, community
```

## License

The aggregator code is MIT licensed. All article content belongs to original sources and is linked, not copied.

---

*Built with zero JavaScript, zero frameworks, zero maintenance.*
