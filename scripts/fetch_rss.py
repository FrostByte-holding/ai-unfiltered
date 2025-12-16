#!/usr/bin/env python3
"""
AI Unfiltered - RSS Feed Fetcher
Fetches articles from curated RSS feeds and stores in SQLite database.
"""

import feedparser
import sqlite3
import hashlib
import yaml
import os
from datetime import datetime, timezone
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.parent
FEEDS_FILE = ROOT_DIR / "feeds.yaml"
DB_FILE = ROOT_DIR / "data" / "articles.db"


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
            summary TEXT
        )
    """)
    
    # Index for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_published ON articles(published DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON articles(category)")
    
    conn.commit()
    return conn


def generate_id(url: str) -> str:
    """Generate unique ID from URL."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


def parse_date(entry) -> str:
    """Extract and normalize publication date from feed entry."""
    # Try different date fields
    for field in ['published_parsed', 'updated_parsed', 'created_parsed']:
        if hasattr(entry, field) and getattr(entry, field):
            try:
                dt = datetime(*getattr(entry, field)[:6])
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
    
    # Fallback to now
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def clean_summary(summary: str, max_length: int = 300) -> str:
    """Clean and truncate summary text."""
    if not summary:
        return ""
    
    # Remove HTML tags (simple approach)
    import re
    clean = re.sub(r'<[^>]+>', '', summary)
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    # Truncate
    if len(clean) > max_length:
        clean = clean[:max_length].rsplit(' ', 1)[0] + "..."
    
    return clean


def fetch_feed(feed_config: dict, conn: sqlite3.Connection) -> int:
    """Fetch a single RSS feed and store new articles."""
    name = feed_config['name']
    url = feed_config['url']
    category = feed_config['category']
    max_per_day = feed_config.get('max_per_day', 30)  # Default to 30 if not specified
    
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
        
        # Calculate remaining slots for today
        remaining_slots = max(0, max_per_day - today_count)
        
        for entry in feed.entries[:30]:  # Limit to latest 30 per feed
            # Get URL
            url = entry.get('link', '')
            if not url:
                continue
            
            article_id = generate_id(url)
            
            # Check if already exists
            cursor.execute("SELECT id FROM articles WHERE id = ?", (article_id,))
            if cursor.fetchone():
                continue
            
            # Extract data
            title = entry.get('title', 'Untitled')
            published = parse_date(entry)
            summary = clean_summary(entry.get('summary', entry.get('description', '')))
            fetched = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            
            # Check if we've hit the daily limit for this feed
            if remaining_slots <= 0:
                continue
            
            # Insert
            cursor.execute("""
                INSERT INTO articles (id, title, url, source, category, published, fetched, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (article_id, title, url, name, category, published, fetched, summary))
            
            new_count += 1
            remaining_slots -= 1
        
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
    print("=" * 50)
    
    # Load feeds config
    with open(FEEDS_FILE, 'r') as f:
        config = yaml.safe_load(f)
    
    feeds = config.get('feeds', [])
    print(f"\nLoaded {len(feeds)} feeds from config\n")
    
    # Initialize database
    conn = init_db()
    
    # Fetch all feeds
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
