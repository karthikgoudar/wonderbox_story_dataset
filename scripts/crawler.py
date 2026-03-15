#!/usr/bin/env python3
"""crawler.py

Collect raw children's story text from web pages and save to raw/<source>/.

This script only downloads and extracts plain story text — it does not
perform any AI analysis or metadata extraction.

Requirements implemented: requests, BeautifulSoup, argparse, pathlib, hashlib, re
"""

from pathlib import Path
import argparse
import hashlib
import re
import time
from typing import List

import requests
from bs4 import BeautifulSoup


# Configuration
MIN_WORDS = 80
MAX_WORDS = 1500
PARA_MIN_WORDS = 4

# Log file to track crawled URLs (kept next to this script)
CRAWL_LOG = Path(__file__).parent / "crawler_urls.txt"


def fetch_page(url: str, timeout: int = 15) -> str:
    """Download a webpage and return HTML text.

    Raises requests.RequestException on failure.
    """
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def extract_story_text(html: str) -> str:
    """Extract story text from HTML.

    Prefer <article> or <main>, otherwise collect <p> tags. Drop very short
    paragraphs and join them with blank lines.
    """
    soup = BeautifulSoup(html, "html.parser")

    container = soup.find("article") or soup.find("main")
    if container:
        paras = container.find_all("p")
    else:
        paras = soup.find_all("p")

    paragraphs: List[str] = []
    for p in paras:
        text = p.get_text(separator=" ", strip=True)
        if len(text.split()) >= PARA_MIN_WORDS:
            paragraphs.append(text)

    return "\n\n".join(paragraphs).strip()


def clean_text(text: str) -> str:
    """Light cleaning: remove common mojibake sequences and normalize whitespace."""
    if not text:
        return text
    # common garbled sequences often seen in scraped pages
    text = text.replace('â', "'")
    text = text.replace('â', '-')
    text = text.replace('â', '—')
    text = text.replace('\xa0', ' ')
    # collapse spaces and multiple blank lines
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def valid_length(text: str) -> bool:
    words = len(text.split())
    return MIN_WORDS <= words <= MAX_WORDS


def is_duplicate(url: str) -> bool:
    """Check if URL already exists in crawl log."""
    if not CRAWL_LOG.exists():
        return False
    try:
        seen = {line.strip() for line in CRAWL_LOG.read_text(encoding="utf-8").splitlines()}
    except Exception:
        return False
    return url.strip() in seen


def record_url(url: str) -> None:
    """Append a URL to the crawl log to prevent future duplicates."""
    CRAWL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with CRAWL_LOG.open("a", encoding="utf-8") as fh:
        fh.write(url.strip() + "\n")


def save_story(url: str, text: str, raw_base: Path, source: str) -> Path:
    """Save story text with metadata header into raw/<source>/filename.txt.

    Filename format: <slug>_<sha1prefix>.txt
    """
    slug_source = url.split("//", 1)[-1]
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", slug_source).strip("-")
    if not slug:
        slug = "story"
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    filename = f"{slug}_{h}.txt"

    dest = raw_base / source
    dest.mkdir(parents=True, exist_ok=True)
    out_path = dest / filename

    header = f"# Source: {url}\n# Fetched: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n\n"
    out_path.write_text(header + text, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch story webpages into raw folder")
    parser.add_argument("--url", help="Single URL to crawl")
    parser.add_argument("--urls-file", help="File with one URL per line")
    parser.add_argument("--source", default="crawler_websites", help="Raw subfolder name")
    parser.add_argument("--raw-dir", default="raw", help="Base raw directory")
    args = parser.parse_args()

    # If no URL arguments are provided, default to a `urls.txt` placed
    # next to this script (so running without args will use that file).
    if not args.url and not args.urls_file:
        default_urls = Path(__file__).parent / "urls.txt"
        if default_urls.exists():
            args.urls_file = str(default_urls)

    repo_root = Path(__file__).parent.parent
    raw_base = repo_root / args.raw_dir

    urls: List[str] = []
    if args.url:
        urls.append(args.url.strip())

    if args.urls_file:
        p = Path(args.urls_file)
        if not p.exists():
            p = Path(__file__).parent / args.urls_file
        if p.exists():
            try:
                for raw_line in p.read_text(encoding="utf-8").splitlines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    # allow comments in the urls file
                    if line.startswith('#'):
                        continue
                    # only accept http(s) URLs
                    if not re.match(r'https?://', line):
                        print(f"Skipping non-URL line in {p}: {line}")
                        continue
                    urls.append(line)
            except Exception as e:
                print(f"Failed to read urls file {p}: {e}")
        else:
            print(f"URLs file not found: {args.urls_file}")

    if not urls:
        print("No URLs provided. Use --url or --urls-file.")
        return

    for url in urls:
        try:
            if is_duplicate(url):
                print("Skipped: duplicate URL")
                continue

            html = fetch_page(url)
            extracted = extract_story_text(html)
            cleaned = clean_text(extracted)

            if not cleaned:
                print(f"Skipped: no story text found at {url}")
                record_url(url)
                continue

            if not valid_length(cleaned):
                print("Skipped: story too short or too long")
                record_url(url)
                continue

            out = save_story(url, cleaned, raw_base, args.source)
            print(f"Saved: {out}")
            record_url(url)

        except Exception as e:
            print(f"Failed to fetch {url}: {e}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Simple web crawler to fetch story text and save as raw text files.

Usage:
  python scripts/crawler.py --url <URL> --source crawler_websites

The script uses `requests` and `bs4` to fetch pages and extracts paragraphs.
"""
import argparse
import hashlib
import os
import re
import time
import html
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-").lower()


def extract_story_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Prefer article or main tags
    container = soup.find("article") or soup.find("main")
    if container:
        paragraphs = container.find_all("p")
    else:
        # fallback: choose all paragraph text
        paragraphs = soup.find_all("p")

    texts = [p.get_text(separator=" ", strip=True) for p in paragraphs]
    # Simple heuristic: drop very short lines
    texts = [t for t in texts if len(t.split()) > 3]
    return "\n\n".join(texts).strip()


def fetch_html(url: str) -> str:
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.text


def save_text(text: str, url: str, dest_dir: str) -> str:
    parsed = urlparse(url)
    base = parsed.netloc.replace(".", "_")
    name = slugify(parsed.path or parsed.netloc)
    if not name:
        name = base

    #!/usr/bin/env python3
    """crawler.py

    Simple crawler to fetch children's story pages, extract story text and
    save cleaned plain-text files into the repository `raw/` folder.

    This script intentionally only collects raw story text; it does NOT perform
    any AI analysis, classification, or metadata extraction — those steps are
    handled separately by `metadata_extractor.py`.

    Usage examples:
      python scripts/crawler.py --url https://example.com/story --source crawler_websites
      python scripts/crawler.py --urls-file scripts/urls.txt --source aesop_fables
    """

    import argparse
    import hashlib
    import re
    import time
    from pathlib import Path
    from typing import List

    import requests
    from bs4 import BeautifulSoup


    # ----------------------------- Configuration ------------------------------
    # Minimum and maximum word counts for a valid story
    MIN_WORDS = 80
    MAX_WORDS = 1500

    # Keep paragraphs that have more than this many words
    PARA_MIN_WORDS = 4

    # File used to track crawled URLs (located next to this script)
    CRAWLED_LOG = Path(__file__).parent / "crawler_urls.txt"


    def slugify(text: str) -> str:
        """Create a filesystem-friendly slug from text (URL path or title)."""
        text = re.sub(r"[^a-zA-Z0-9_-]", "-", text)
        text = re.sub(r"-+", "-", text)
        return text.strip("-").lower()


    def fetch_page(url: str, timeout: int = 15) -> str:
        """Download page HTML. Raises requests.RequestException on failure."""
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text


    def extract_story_text(html: str) -> str:
        """Extract story text from HTML using BeautifulSoup.

        Prefers <article> or <main>, falls back to <p> tags. Drops very short
        paragraphs and returns joined paragraphs separated by blank lines.
        """
        soup = BeautifulSoup(html, "html.parser")

        container = soup.find("article") or soup.find("main")
        if container:
            paras = container.find_all("p")
        else:
            paras = soup.find_all("p")

        texts: List[str] = []
        for p in paras:
            t = p.get_text(separator=" ", strip=True)
            if len(t.split()) >= PARA_MIN_WORDS:
                texts.append(t)

        return "\n\n".join(texts).strip()


    def clean_text(text: str) -> str:
        """Simple cleanup: unescape entities, collapse whitespace, strip garbage."""
        if not text:
            return text

        # replace common mojibake sequences if present
        replacements = {
            'â': "'", 'â': '-', 'â': '—', 'â': '"', 'â': '"', '\xa0': ' '
        }
        for k, v in replacements.items():
            text = text.replace(k, v)

        # collapse runs of spaces and trim
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()


    def is_duplicate(url: str) -> bool:
        """Return True if URL exists in the crawl log file."""
        if not CRAWLED_LOG.exists():
            return False
        try:
            seen = CRAWLED_LOG.read_text(encoding="utf-8").splitlines()
        except Exception:
            return False
        return url.strip() in (s.strip() for s in seen)


    def record_url(url: str) -> None:
        """Append a crawled URL to the crawl log file."""
        CRAWLED_LOG.parent.mkdir(parents=True, exist_ok=True)
        with CRAWLED_LOG.open("a", encoding="utf-8") as fh:
            fh.write(url.strip() + "\n")


    def save_story(url: str, text: str, raw_base: Path, source: str) -> Path:
        """Write the story text to a file under raw/<source>/ with metadata header.

        Filenames are generated from a slug of the URL path + short SHA1.
        """
        parsed_path = url.split("//", 1)[-1]  # naive path for slug
        name = slugify(parsed_path)
        if not name:
            name = "story"
        h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
        filename = f"{name}_{h}.txt"

        dest_dir = raw_base / source
        dest_dir.mkdir(parents=True, exist_ok=True)
        out_path = dest_dir / filename

        header = f"# Source: {url}\n# Fetched: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n\n"
        out_path.write_text(header + text, encoding="utf-8")
        return out_path


    def valid_length(text: str) -> bool:
        words = len(text.split())
        return MIN_WORDS <= words <= MAX_WORDS


    def main() -> None:
        parser = argparse.ArgumentParser(description="Fetch story webpages into raw folder")
        parser.add_argument("--url", help="Single URL to crawl")
        parser.add_argument("--urls-file", help="File with one URL per line")
        parser.add_argument("--source", default="crawler_websites", help="Raw subfolder name")
        parser.add_argument("--raw-dir", default="raw", help="Base raw directory")
        args = parser.parse_args()

        # compute repo-root raw folder (script is in scripts/)
        repo_root = Path(__file__).parent.parent
        raw_base = repo_root / args.raw_dir

        urls: List[str] = []
        if args.url:
            urls.append(args.url.strip())
        if args.urls_file:
            p = Path(args.urls_file)
            # allow relative filenames from repo root and script dir
            if not p.exists():
                p = Path(__file__).parent / args.urls_file
            if p.exists():
                try:
                    urls += [line.strip() for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
                except Exception as e:
                    print(f"Failed to read urls file {p}: {e}")
            else:
                print(f"URLs file not found: {args.urls_file}")

        if not urls:
            print("No URLs provided. Use --url or --urls-file.")
            return

        for url in urls:
            try:
                if is_duplicate(url):
                    print("Skipped: duplicate URL")
                    continue

                html = fetch_page(url)
                raw = extract_story_text(html)
                raw = clean_text(raw)

                if not raw:
                    print(f"Skipped: no story text found at {url}")
                    record_url(url)
                    continue

                if not valid_length(raw):
                    print("Skipped: story too short or too long")
                    record_url(url)
                    continue

                out = save_story(url, raw, raw_base, args.source)
                print(f"Saved: {out}")
                # record successful crawl to avoid duplicates in the future
                record_url(url)

            except Exception as e:
                print(f"Failed to fetch {url}: {e}")


    if __name__ == "__main__":
        main()
    if args.url:
        urls.append(args.url)

    # If a urls file was provided (or default exists next to script), try to read it.
    if args.urls_file:
        urls_path = os.path.expanduser(args.urls_file)
        if os.path.exists(urls_path):
            with open(urls_path, "r", encoding="utf-8") as fh:
                urls.extend([l.strip() for l in fh if l.strip()])
        else:
            # only warn if the file was explicitly provided (not the default),
            # otherwise silently continue to check for --url
            if args.urls_file != default_urls:
                print(f"URLs file not found: {urls_path}")

    if not urls:
        print("No URLs provided. Use --url or --urls-file (see scripts/urls.txt).")
        return

    visited = set()
    for u in urls:
        to_visit = [u]
        while to_visit:
            cur = to_visit.pop(0)
            if cur in visited:
                continue
            visited.add(cur)
            try:
                html = fetch_html(cur)
                soup = BeautifulSoup(html, "html.parser")
                text = clean_text(extract_story_text(html))
                if is_story_page(soup, text):
                    saved = save_text(text, cur, dest_dir)
                    print(f"Saved: {saved}")
                else:
                    # treat as index/landing page: find candidate story links and fetch them
                    candidates = find_story_links(soup, cur, max_links=25)
                    if not candidates:
                        # fallback: still save whatever text we have (may be useful)
                        if text:
                            text = clean_text(text)
                            saved = save_text(text, cur, dest_dir)
                            print(f"Saved (fallback): {saved}")
                        else:
                            print(f"No story content found at {cur}")
                    else:
                        print(f"Found {len(candidates)} candidate links on {cur}; queuing them")
                        # add candidates to front of queue to process them next
                        for c in candidates:
                            if c not in visited:
                                to_visit.insert(0, c)
            except Exception as e:
                print(f"Failed to fetch {cur}: {e}")


if __name__ == "__main__":
    main()
