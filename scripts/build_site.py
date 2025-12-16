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

# Paths
ROOT_DIR = Path(__file__).parent.parent
DB_FILE = ROOT_DIR / "data" / "articles.db"
DOCS_DIR = ROOT_DIR / "docs"

# Site config
SITE_NAME = "AI Unfiltered"
SITE_DESCRIPTION = "Raw AI news. No fluff. Updated every 4 hours."
ARTICLES_PER_PAGE = 100


def get_articles(conn, category=None, limit=ARTICLES_PER_PAGE):
    """Fetch articles from database."""
    cursor = conn.cursor()
    
    if category:
        cursor.execute("""
            SELECT id, title, url, source, category, published, summary
            FROM articles
            WHERE category = ?
            ORDER BY published DESC
            LIMIT ?
        """, (category, limit))
    else:
        cursor.execute("""
            SELECT id, title, url, source, category, published, summary
            FROM articles
            ORDER BY published DESC
            LIMIT ?
        """, (limit,))
    
    return cursor.fetchall()


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
            <a href="/research.html" class="{'active' if active_category == 'research' else ''}">research</a>
            <a href="/llm.html" class="{'active' if active_category == 'llm' else ''}">llm</a>
            <a href="/industry.html" class="{'active' if active_category == 'industry' else ''}">industry</a>
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
        <link>https://frostbyte-holding.github.io/ai-unfiltered/</link>
        <description>{SITE_DESCRIPTION}</description>
        <language>en-us</language>
        <lastBuildDate>{datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>
        <atom:link href="https://frostbyte-holding.github.io/ai-unfiltered/rss.xml" rel="self" type="application/rss+xml"/>
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
    categories = ['chinese-ai', 'research', 'llm', 'industry', 'company', 'community']
    for cat in categories:
        build_page(conn, category=cat, filename=f"{cat}.html")
    
    # Build RSS feed
    articles = get_articles(conn, limit=50)
    rss = generate_rss(articles)
    with open(DOCS_DIR / "rss.xml", 'w', encoding='utf-8') as f:
        f.write(rss)
    print(f"  ✓ Built rss.xml")
    
    # Create .nojekyll file for GitHub Pages
    (DOCS_DIR / ".nojekyll").touch()
    
    conn.close()
    
    print("\n" + "=" * 50)
    print("Done! Site built in /docs")
    print("=" * 50)


if __name__ == "__main__":
    main()
