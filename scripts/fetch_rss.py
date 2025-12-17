#!/usr/bin/env python3
"""
AI Unfiltered - RSS Feed Fetcher
Fetches articles from curated RSS feeds and stores in SQLite database.
Includes LLM-based scoring for research papers to filter signal from noise.
"""

import feedparser
import sqlite3
import hashlib
import yaml
import os
import json
import re
from datetime import datetime, timezone
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.parent
FEEDS_FILE = ROOT_DIR / "feeds.yaml"
DB_FILE = ROOT_DIR / "data" / "articles.db"

# LLM scoring config
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
ENABLE_LLM_SCORING = bool(OPENAI_API_KEY)


def init_db():
    """Initialize SQLite database with articles table."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            source TEXT NOT NULL,
            category TEXT NOT NULL,
            published TEXT,
            fetched TEXT NOT NULL,
            summary TEXT,
            score REAL DEFAULT 0,
            tier INTEGER DEFAULT 2
        )
    """)
    
    # Add score and tier columns if they don't exist (migration)
    try:
        cursor.execute("ALTER TABLE articles ADD COLUMN score REAL DEFAULT 0")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE articles ADD COLUMN tier INTEGER DEFAULT 2")
    except:
        pass
    
    # Index for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_published ON articles(published DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON articles(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_score ON articles(score DESC)")
    
    conn.commit()
    return conn


def generate_id(url: str) -> str:
    """Generate unique ID from URL."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def parse_date(entry) -> str:
    """Extract and normalize publication date from feed entry."""
    for field in ['published_parsed', 'updated_parsed', 'created_parsed']:
        if hasattr(entry, field) and getattr(entry, field):
            try:
                dt = datetime(*getattr(entry, field)[:6])
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def clean_summary(summary: str, max_length: int = 300) -> str:
    """Clean and truncate summary text."""
    if not summary:
        return ""
    clean = re.sub(r'<[^>]+>', '', summary)
    clean = re.sub(r'\s+', ' ', clean).strip()
    if len(clean) > max_length:
        clean = clean[:max_length].rsplit(' ', 1)[0] + "..."
    return clean


def score_research_paper(title: str, summary: str) -> float:
    """
    Use LLM to score research paper relevance and impact.
    Returns score 0-10. Higher = more important.
    """
    if not ENABLE_LLM_SCORING:
        return 5.0  # Default middle score if no API key
    
    try:
        from openai import OpenAI
        client = OpenAI()
        
        prompt = f"""Score this AI research paper from 0-10 based on:
- Novelty (is this a new approach or incremental?)
- Impact (will this matter to practitioners?)
- Relevance (is this about LLMs, Chinese AI, open source, or security?)

Title: {title}
Abstract: {summary[:500]}

Respond with ONLY a number 0-10. High scores (8-10) for:
- New model architectures or training methods
- Chinese AI developments (DeepSeek, Qwen, etc.)
- Security/safety research
- Significant benchmarks or evaluations

Low scores (0-3) for:
- Minor incremental improvements
- Narrow domain applications
- Survey papers without new contributions

Score:"""

        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0
        )
        
        score_text = response.choices[0].message.content.strip()
        score = float(re.search(r'[\d.]+', score_text).group())
        return min(10, max(0, score))
        
    except Exception as e:
        print(f"      LLM scoring failed: {e}")
        return 5.0


def fetch_feed(feed_config: dict, conn: sqlite3.Connection) -> int:
    """Fetch a single RSS feed and store new articles."""
    name = feed_config['name']
    url = feed_config['url']
    category = feed_config['category']
    max_per_day = feed_config.get('max_per_day', 30)
    tier = feed_config.get('tier', 2)
    requires_scoring = feed_config.get('requires_scoring', False)
    
    print(f"  Fetching: {name}")
    
    try:
        feed = feedparser.parse(url)
        
        if feed.bozo and not feed.entries:
            print(f"    ⚠ Error parsing feed: {feed.bozo_exception}")
            return 0
        
        cursor = conn.cursor()
        new_count = 0
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Check how many articles from this source we already have today
        cursor.execute("""
            SELECT COUNT(*) FROM articles 
            WHERE source = ? AND published LIKE ?
        """, (name, f"{today}%"))
        today_count = cursor.fetchone()[0]
        remaining_slots = max(0, max_per_day - today_count)
        
        # For scoring feeds, collect candidates first
        candidates = []
        
        for entry in feed.entries[:30]:
            url = entry.get('link', '')
            if not url:
                continue
            
            article_id = generate_id(url)
            
            # Check if already exists
            cursor.execute("SELECT id FROM articles WHERE id = ?", (article_id,))
            if cursor.fetchone():
                continue
            
            title = entry.get('title', 'Untitled')
            summary_raw = entry.get('summary', entry.get('description', ''))
            
            # Skip scheduled maintenance events (not real incidents)
            skip_keywords = ['SCHEDULED', 'scheduled maintenance', 'Scheduled -', 'maintenance window']
            if any(kw.lower() in (title + ' ' + summary_raw).lower() for kw in skip_keywords):
                continue
            
            published = parse_date(entry)
            summary = clean_summary(summary_raw)
            fetched = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            
            candidates.append({
                'id': article_id,
                'title': title,
                'url': url,
                'published': published,
                'summary': summary,
                'fetched': fetched,
                'score': 5.0
            })
        
        # Score candidates if required
        if requires_scoring and ENABLE_LLM_SCORING and candidates:
            print(f"    Scoring {len(candidates)} papers...")
            for c in candidates:
                c['score'] = score_research_paper(c['title'], c['summary'])
                print(f"      {c['score']:.1f} - {c['title'][:50]}...")
            
            # Sort by score and take top ones
            candidates.sort(key=lambda x: x['score'], reverse=True)
            candidates = [c for c in candidates if c['score'] >= 6.0][:remaining_slots]
        else:
            candidates = candidates[:remaining_slots]
        
        # Insert candidates
        for c in candidates:
            cursor.execute("""
                INSERT INTO articles (id, title, url, source, category, published, fetched, summary, score, tier)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (c['id'], c['title'], c['url'], name, category, c['published'], c['fetched'], c['summary'], c['score'], tier))
            new_count += 1
        
        conn.commit()
        print(f"    ✓ Added {new_count} new articles")
        return new_count
        
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        return 0


def main():
    """Main entry point."""
    print("=" * 50)
    print("AI Unfiltered - RSS Fetcher")
    print(f"LLM Scoring: {'Enabled' if ENABLE_LLM_SCORING else 'Disabled'}")
    print("=" * 50)
    
    with open(FEEDS_FILE, 'r') as f:
        config = yaml.safe_load(f)
    
    feeds = config.get('feeds', [])
    print(f"\nLoaded {len(feeds)} feeds from config\n")
    
    conn = init_db()
    
    total_new = 0
    for feed in feeds:
        new = fetch_feed(feed, conn)
        total_new += new
    
    conn.close()
    
    print("\n" + "=" * 50)
    print(f"Done! Added {total_new} new articles total")
    print("=" * 50)


if __name__ == "__main__":
    main()
