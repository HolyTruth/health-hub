#!/usr/bin/env python3 -u
"""Translate Wellness Pulse articles to all supported languages using LLM API."""
import sys
sys.stdout.reconfigure(line_buffering=True)

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

API_BASE = "https://token-plan-cn.xiaomimimo.com/v1"
API_KEY = "tp-cjymqs6k6e14rgfosikwxcnukkbojadfgu7ii81lhlnnl5xg"
MODEL = "mimo-v2.5-pro"

LANGUAGES = {
    "zh": {"name": "中文", "native": "中文"},
    "es": {"name": "Spanish", "native": "Español"},
    "pt": {"name": "Portuguese", "native": "Português"},
    "fr": {"name": "French", "native": "Français"},
    "de": {"name": "German", "native": "Deutsch"},
    "ru": {"name": "Russian", "native": "Русский"},
    "ar": {"name": "Arabic", "native": "العربية"},
    "hi": {"name": "Hindi", "native": "हिन्दी"},
    "bn": {"name": "Bengali", "native": "বাংলা"},
    "id": {"name": "Indonesian", "native": "Indonesia"},
}

CONTENT_DIR = "/root/health-hub/content"


def translate_text(text, target_lang, lang_name):
    """Call LLM API to translate text."""
    prompt = f"""Translate the following health blog article from English to {lang_name} ({target_lang}).

RULES:
1. Translate ALL text content (title, description, summary, body text, FAQ questions and answers)
2. DO NOT translate:
   - YAML frontmatter keys (title:, description:, etc. — keep the keys in English)
   - Markdown syntax (#, ##, -, *, [], (), |, ---)
   - URLs and file paths
   - Technical/medical terms that are commonly used in English (e.g., NF-κB, COX-2, CRP, EPA, DHA, hs-CRP, GABA, SCFA, omega-3, probiotics, curcumin, etc.)
   - Author names and journal names in citations (e.g., "Smith et al., 2023, JAMA")
   - Numbers and units (mg, mL, %, IU)
   - HTML tags if any
3. Keep the EXACT same markdown structure (headings, lists, tables, links, bold)
4. For internal links like `/posts/slug-name/`, keep the slug in English
5. Translate naturally — this should read like a native {lang_name} health article, not a machine translation
6. Keep the frontmatter format as YAML with --- delimiters

Here is the article to translate:

{text}"""

    data = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 8000,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }

    req = urllib.request.Request(
        f"{API_BASE}/chat/completions",
        data=data,
        headers=headers,
        method="POST",
    )

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"]
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError) as e:
            print(f"  Attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
            else:
                raise


def translate_article(article_file, target_lang, lang_name):
    """Translate a single article to target language."""
    src_path = os.path.join(CONTENT_DIR, "en", "posts", article_file)
    dst_dir = os.path.join(CONTENT_DIR, target_lang, "posts")
    dst_path = os.path.join(dst_dir, article_file)

    if os.path.exists(dst_path):
        print(f"  Skip (exists): {article_file} -> {target_lang}")
        return True

    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"  Translating {article_file} -> {lang_name}...")
    translated = translate_text(content, target_lang, lang_name)

    # Clean up: remove any markdown code fences the LLM might add
    translated = re.sub(r'^```(?:yaml|markdown)?\s*\n?', '', translated)
    translated = re.sub(r'\n?```\s*$', '', translated)

    os.makedirs(dst_dir, exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(translated)

    print(f"  Done: {dst_path}")
    return True


def main():
    articles = [f for f in os.listdir(os.path.join(CONTENT_DIR, "en", "posts")) if f.endswith(".md")]
    articles.sort()

    if len(sys.argv) > 1:
        # Translate specific article
        articles = [a for a in articles if sys.argv[1] in a]

    if len(sys.argv) > 2:
        # Translate to specific language only
        target_langs = {sys.argv[2]: LANGUAGES[sys.argv[2]]}
    else:
        target_langs = LANGUAGES

    total = len(articles) * len(target_langs)
    done = 0

    print(f"Translating {len(articles)} articles to {len(target_langs)} languages ({total} total)")

    for article in articles:
        print(f"\n=== {article} ===")
        for lang_code, lang_info in target_langs.items():
            try:
                translate_article(article, lang_code, lang_info["name"])
                done += 1
                print(f"  Progress: {done}/{total}")
                time.sleep(0.5)  # rate limit
            except Exception as e:
                print(f"  ERROR: {e}")

    print(f"\n=== Complete: {done}/{total} translations ===")


if __name__ == "__main__":
    main()
