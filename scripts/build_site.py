#!/usr/bin/env python3
"""
AI Unfiltered - Static Site Generator
Generates minimal HTML pages from SQLite database.
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path
from html import escape
from collections import defaultdict

# Paths
ROOT_DIR = Path(__file__).parent.parent
DB_FILE = ROOT_DIR / "data" / "articles.db"
DOCS_DIR = ROOT_DIR / "docs"

# Site config
SITE_NAME = "AI Unfiltered"
SITE_DESCRIPTION = "Chinese AI • Open Source • Security • Incidents. Signal, not noise."
ARTICLES_PER_PAGE = 100
MAX_PER_SOURCE = 5  # Maximum articles per source per page


def get_articles(conn, category=None, limit=ARTICLES_PER_PAGE):
    """Fetch articles from database with per-source limits."""
    cursor = conn.cursor()
    
    if category:
        cursor.execute("""
            SELECT id, title, url, source, category, published, summary
            FROM articles
            WHERE category = ?
            ORDER BY published DESC
            LIMIT ?
        """, (category, limit * 3))  # Fetch more to allow filtering
    else:
        cursor.execute("""
            SELECT id, title, url, source, category, published, summary
            FROM articles
            ORDER BY published DESC
            LIMIT ?
        """, (limit * 3,))  # Fetch more to allow filtering
    
    all_articles = cursor.fetchall()
    
    # Apply per-source limit
    source_counts = defaultdict(int)
    filtered_articles = []
    
    for article in all_articles:
        source = article[3]  # source is at index 3
        if source_counts[source] < MAX_PER_SOURCE:
            filtered_articles.append(article)
            source_counts[source] += 1
        
        if len(filtered_articles) >= limit:
            break
    
    return filtered_articles


def get_categories(conn):
    """Get all categories with article counts."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM articles
        GROUP BY category
        ORDER BY count DESC
    """)
    return cursor.fetchall()


def format_date(date_str):
    """Format date for display."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%b %d")
    except:
        return date_str[:10] if date_str else ""


def generate_html_head(title, description=None):
    """Generate HTML head section."""
    desc = description or SITE_DESCRIPTION
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{escape(desc)}">
    <title>{escape(title)}</title>
    <link rel="alternate" type="application/rss+xml" title="{SITE_NAME} RSS" href="/rss.xml">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html {{ 
            background: #000; 
            color: #e0e0e0; 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
            font-size: 16px;
            line-height: 1.6;
        }}
        body {{ 
            max-width: 800px; 
            margin: 0 auto; 
            padding: 20px;
        }}
        a {{ color: #4af; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        header {{ 
            border-bottom: 1px solid #333; 
            padding-bottom: 20px; 
            margin-bottom: 30px;
        }}
        h1 {{ 
            font-size: 1.5rem; 
            font-weight: normal;
            letter-spacing: 2px;
        }}
        h1 a {{ color: #fff; }}
        .tagline {{ color: #666; font-size: 0.9rem; margin-top: 5px; }}
        nav {{ margin-top: 15px; }}
        nav a {{ 
            margin-right: 15px; 
            color: #888;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        nav a:hover, nav a.active {{ color: #4af; }}
        .article {{ 
            margin-bottom: 25px; 
            padding-bottom: 25px;
            border-bottom: 1px solid #1a1a1a;
        }}
        .article:last-child {{ border-bottom: none; }}
        .article-title {{ 
            font-size: 1.1rem;
            line-height: 1.4;
        }}
        .article-title a {{ color: #fff; }}
        .article-meta {{ 
            margin-top: 8px;
            font-size: 0.8rem;
            color: #666;
        }}
        .article-meta a {{ color: #666; }}
        .article-meta a:hover {{ color: #4af; }}
        .source {{ color: #4af; }}
        .category {{ 
            background: #1a1a1a;
            padding: 2px 8px;
            border-radius: 3px;
            margin-left: 10px;
        }}
        .summary {{
            margin-top: 8px;
            color: #888;
            font-size: 0.9rem;
        }}
        footer {{ 
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #333;
            color: #444;
            font-size: 0.8rem;
        }}
        footer a {{ color: #666; }}
        .updated {{ color: #333; }}
    </style>
</head>
<body>
"""


def generate_header(active_category=None):
    """Generate site header with navigation."""
    return f"""
    <header>
        <h1><a href="/">{SITE_NAME}</a></h1>
        <p class="tagline">{SITE_DESCRIPTION}</p>
        <nav>
            <a href="/" class="{'active' if not active_category else ''}">all</a>
            <a href="/chinese-ai.html" class="{'active' if active_category == 'chinese-ai' else ''}">chinese ai</a>
            <a href="/open-source.html" class="{'active' if active_category == 'open-source' else ''}">open source</a>
            <a href="/security.html" class="{'active' if active_category == 'security' else ''}">security</a>
            <a href="/incidents.html" class="{'active' if active_category == 'incidents' else ''}">incidents</a>
            <a href="/research.html" class="{'active' if active_category == 'research' else ''}">research</a>
            <a href="/rss.xml">rss</a>
        </nav>
    </header>
    <main>
"""


def generate_article_html(article):
    """Generate HTML for a single article."""
    id, title, url, source, category, published, summary = article
    date_str = format_date(published)
    
    html = f"""
        <article class="article">
            <h2 class="article-title">
                <a href="{escape(url)}" target="_blank" rel="noopener">{escape(title)}</a>
            </h2>
            <div class="article-meta">
                <span class="date">{date_str}</span>
                <span class="source">via {escape(source)}</span>
                <a href="/{category}.html" class="category">{category}</a>
            </div>
"""
    if summary:
        html += f'            <p class="summary">{escape(summary)}</p>\n'
    
    html += "        </article>\n"
    return html


def generate_footer():
    """Generate site footer."""
    updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    return f"""
    </main>
    <footer>
        <p>
            <a href="/rss.xml">RSS Feed</a> · 
            Updated every 4 hours · 
            <span class="updated">Last: {updated}</span>
        </p>
        <p>Links to original sources. No content is copied.</p>
    </footer>
</body>
</html>
"""


def generate_llms_txt(conn):
    """Generate llms.txt file for AI agents."""
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM articles')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT MIN(published), MAX(published) FROM articles')
    min_date, max_date = cursor.fetchone()
    
    return f"""# AI Unfiltered

> Chinese AI • Open Source • Security • Incidents. Signal, not noise.

AI Unfiltered is a focused news aggregator covering what matters: Chinese AI developments, open source model releases, AI security incidents, and operational failures. No Reddit noise. No press release recycling. LLM-scored research papers.

## Stats
- Total articles: {total}
- Date range: {min_date[:10] if min_date else 'N/A'} to {max_date[:10] if max_date else 'N/A'}
- Update frequency: Every 4 hours

## Sections

- [All News](https://ai-unfiltered.com/): Latest curated AI news
- [Chinese AI](https://ai-unfiltered.com/chinese-ai.html): DeepSeek, Qwen, Zhipu, Baidu, ByteDance, and Chinese AI ecosystem
- [Open Source](https://ai-unfiltered.com/open-source.html): Model releases (Mistral, LLaMA, Qwen, Yi) and tools (Ollama, vLLM, LangChain)
- [Security](https://ai-unfiltered.com/security.html): Prompt injection, jailbreaks, AI vulnerabilities, and breaches
- [Incidents](https://ai-unfiltered.com/incidents.html): Cloud outages, infrastructure failures, operational reality
- [Research](https://ai-unfiltered.com/research.html): LLM-scored arXiv papers (filtered for impact, not volume)

## Feeds

- [RSS Feed](https://ai-unfiltered.com/rss.xml): Subscribe to get updates
- [llms-full.txt](https://ai-unfiltered.com/llms-full.txt): Full article list for AI agents

## Source

Open source on GitHub: https://github.com/FrostByte-holding/ai-unfiltered
"""


def generate_llms_full_txt(conn):
    """Generate llms-full.txt with all recent articles for AI agents."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT title, url, source, category, published, summary
        FROM articles
        ORDER BY published DESC
        LIMIT 500
    """)
    articles = cursor.fetchall()
    
    content = """# AI Unfiltered - Full Article List

> This file contains recent AI news articles for consumption by LLMs and AI agents.
> Updated every 4 hours. Links to original sources.

"""
    
    current_date = None
    for title, url, source, category, published, summary in articles:
        date_str = published[:10] if published else "Unknown"
        
        if date_str != current_date:
            current_date = date_str
            content += f"\n## {date_str}\n\n"
        
        content += f"### {title}\n"
        content += f"- Source: {source}\n"
        content += f"- Category: {category}\n"
        content += f"- URL: {url}\n"
        if summary:
            content += f"- Summary: {summary}\n"
        content += "\n"
    
    return content


def generate_rss(articles):
    """Generate RSS feed XML."""
    items = ""
    for article in articles[:50]:
        id, title, url, source, category, published, summary = article
        
        # Convert date to RFC 822 format
        try:
            dt = datetime.strptime(published, "%Y-%m-%d %H:%M:%S")
            pub_date = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
        except:
            pub_date = ""
        
        items += f"""
        <item>
            <title>{escape(title)}</title>
            <link>{escape(url)}</link>
            <guid>{escape(url)}</guid>
            <pubDate>{pub_date}</pubDate>
            <source url="{escape(url)}">{escape(source)}</source>
            <category>{escape(category)}</category>
            <description>{escape(summary or '')}</description>
        </item>"""
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
    <channel>
        <title>{SITE_NAME}</title>
        <link>https://ai-unfiltered.com/</link>
        <description>{SITE_DESCRIPTION}</description>
        <language>en-us</language>
        <lastBuildDate>{datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
        <atom:link href="https://ai-unfiltered.com/rss.xml" rel="self" type="application/rss+xml"/>
        {items}
    </channel>
</rss>
"""


def build_page(conn, category=None, filename="index.html"):
    """Build a single HTML page."""
    articles = get_articles(conn, category=category)
    
    title = f"{category.replace('-', ' ').title()} - {SITE_NAME}" if category else SITE_NAME
    
    html = generate_html_head(title)
    html += generate_header(active_category=category)
    
    if not articles:
        html += "        <p>No articles yet. Check back soon.</p>\n"
    else:
        for article in articles:
            html += generate_article_html(article)
    
    html += generate_footer()
    
    filepath = DOCS_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"  ✓ Built {filename} ({len(articles)} articles)")


def main():
    """Main entry point."""
    print("=" * 50)
    print("AI Unfiltered - Site Generator")
    print(f"Max {MAX_PER_SOURCE} articles per source")
    print("=" * 50)
    
    # Ensure docs directory exists
    DOCS_DIR.mkdir(exist_ok=True)
    
    # Check if database exists
    if not DB_FILE.exists():
        print("\n⚠ Database not found. Run fetch_rss.py first.")
        # Create empty index page
        html = generate_html_head(SITE_NAME)
        html += generate_header()
        html += "        <p>No articles yet. Feeds are being fetched...</p>\n"
        html += generate_footer()
        with open(DOCS_DIR / "index.html", 'w') as f:
            f.write(html)
        return
    
    conn = sqlite3.connect(DB_FILE)
    
    print("\nBuilding pages...")
    
    # Build main index
    build_page(conn, filename="index.html")
    
    # Build category pages
    categories = ['chinese-ai', 'open-source', 'security', 'incidents', 'research']
    for cat in categories:
        build_page(conn, category=cat, filename=f"{cat}.html")
    
    # Build RSS feed
    articles = get_articles(conn, limit=50)
    rss = generate_rss(articles)
    with open(DOCS_DIR / "rss.xml", 'w', encoding='utf-8') as f:
        f.write(rss)
    print(f"  ✓ Built rss.xml")
    
    # Build llms.txt files for AI agents
    llms_txt = generate_llms_txt(conn)
    with open(DOCS_DIR / "llms.txt", 'w', encoding='utf-8') as f:
        f.write(llms_txt)
    print(f"  ✓ Built llms.txt")
    
    llms_full = generate_llms_full_txt(conn)
    with open(DOCS_DIR / "llms-full.txt", 'w', encoding='utf-8') as f:
        f.write(llms_full)
    print(f"  ✓ Built llms-full.txt")
    
    # Create .nojekyll file for GitHub Pages
    (DOCS_DIR / ".nojekyll").touch()
    
    conn.close()
    
    print("\n" + "=" * 50)
    print("Done! Site built in /docs")
    print("=" * 50)


if __name__ == "__main__":
    main()
