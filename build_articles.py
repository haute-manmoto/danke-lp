#!/usr/bin/env python3
"""
build_articles.py — だんけLP 記事自動更新スクリプト

使い方:
  cd danke_lp
  python3 build_articles.py

articles.json に記事を追加してからこのスクリプトを実行すると、
以下が自動更新される:
  - index.html         : TOPページ の Articles セクション（最新4本）
  - articles/index.html: 記事一覧（最新順）
  - articles/*/index.html: 各記事の Related Articles（関連度順）
"""

import json
import re
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
ARTICLES_JSON = BASE_DIR / "articles.json"
INDEX_HTML    = BASE_DIR / "index.html"
LIST_HTML     = BASE_DIR / "articles" / "index.html"
ARTICLES_DIR  = BASE_DIR / "articles"
TOP_N         = 4   # TOPページに表示する記事数
RELATED_N     = 3   # 記事ページに表示する関連記事数


# ─────────────────────────────────────────
# HTML 生成ヘルパー
# ─────────────────────────────────────────

def card_top(a, prefix="articles/"):
    """TOPページ用カード（article-card--light, 日付テキストのみ）"""
    return f"""      <a href="{prefix}{a['slug']}/" class="article-card article-card--light">
        <div class="article-card-thumb">
          <img src="images/{a['thumb']}" alt="{a['title']['en']}" loading="lazy" width="800" height="800">
        </div>
        <div class="article-card-body">
          <time class="article-card-date">{a['date']}</time>
          <h3 class="article-card-title">
            <span data-lang="en">{a['title']['en']}</span>
            <span data-lang="zh">{a['title']['zh']}</span>
            <span data-lang="ko">{a['title']['ko']}</span>
          </h3>
          <p class="article-card-excerpt">
            <span data-lang="en">{a['excerpt']['en']}</span>
            <span data-lang="zh">{a['excerpt']['zh']}</span>
            <span data-lang="ko">{a['excerpt']['ko']}</span>
          </p>
        </div>
      </a>"""


def card_list(a):
    """記事一覧ページ用カード（reveal アニメーション付き）"""
    return f"""      <a href="{a['slug']}/" class="article-card reveal" style="text-decoration:none;">
        <div class="article-card-thumb">
          <img src="../images/{a['thumb']}" alt="{a['title']['en']}" loading="lazy">
        </div>
        <div class="article-card-body">
          <span class="article-card-tag">
            <span data-lang="en">{a['tag']['en']}</span>
            <span data-lang="zh">{a['tag']['zh']}</span>
            <span data-lang="ko">{a['tag']['ko']}</span>
          </span>
          <h3 class="article-card-title">
            <span data-lang="en">{a['title']['en']}</span>
            <span data-lang="zh">{a['title']['zh']}</span>
            <span data-lang="ko">{a['title']['ko']}</span>
          </h3>
          <p class="article-card-excerpt">
            <span data-lang="en">{a['excerpt']['en']}</span>
            <span data-lang="zh">{a['excerpt']['zh']}</span>
            <span data-lang="ko">{a['excerpt']['ko']}</span>
          </p>
          <time class="article-card-date" datetime="{a['date']}">{a['date']}</time>
        </div>
      </a>"""


def card_related(a):
    """記事ページ下部の Related Articles 用カード"""
    return f"""      <a href="../{a['slug']}/" class="article-card reveal" style="text-decoration:none;">
        <div class="article-card-thumb">
          <img src="../../images/{a['thumb']}" alt="{a['title']['en']}" loading="lazy">
        </div>
        <div class="article-card-body">
          <span class="article-card-tag">
            <span data-lang="en">{a['tag']['en']}</span>
            <span data-lang="zh">{a['tag']['zh']}</span>
            <span data-lang="ko">{a['tag']['ko']}</span>
          </span>
          <h3 class="article-card-title">
            <span data-lang="en">{a['title']['en']}</span>
            <span data-lang="zh">{a['title']['zh']}</span>
            <span data-lang="ko">{a['title']['ko']}</span>
          </h3>
          <p class="article-card-excerpt">
            <span data-lang="en">{a['excerpt']['en']}</span>
            <span data-lang="zh">{a['excerpt']['zh']}</span>
            <span data-lang="ko">{a['excerpt']['ko']}</span>
          </p>
          <time class="article-card-date" datetime="{a['date']}">{a['date']}</time>
        </div>
      </a>"""


# ─────────────────────────────────────────
# 関連記事スコア計算
# ─────────────────────────────────────────

def related_score(a, b):
    """キーワード一致数でスコアを算出（多いほど関連性が高い）"""
    return len(set(a["keywords"]) & set(b["keywords"]))


def get_related(articles, current_slug, n=RELATED_N):
    """current_slug の記事に最も関連性の高い n 本を返す"""
    others = [a for a in articles if a["slug"] != current_slug]
    current = next(a for a in articles if a["slug"] == current_slug)
    scored = sorted(
        others,
        key=lambda a: (related_score(current, a), a["date"]),
        reverse=True
    )
    return scored[:n]


# ─────────────────────────────────────────
# HTML 書き換え
# ─────────────────────────────────────────

def replace_between(content, start_marker, end_marker, new_inner):
    """start_marker と end_marker の間のテキストを new_inner で置換"""
    pattern = re.compile(
        re.escape(start_marker) + r".*?" + re.escape(end_marker),
        re.DOTALL
    )
    replacement = f"{start_marker}\n{new_inner}\n{end_marker}"
    result, count = pattern.subn(replacement, content)
    if count == 0:
        raise ValueError(f"Markers not found: {start_marker!r}")
    return result


def update_file(path, start_marker, end_marker, new_inner):
    path = Path(path)
    content = path.read_text(encoding="utf-8")
    updated = replace_between(content, start_marker, end_marker, new_inner)
    path.write_text(updated, encoding="utf-8")
    print(f"  Updated: {path.relative_to(BASE_DIR.parent)}")


# ─────────────────────────────────────────
# メイン処理
# ─────────────────────────────────────────

def main():
    # articles.json 読み込み（日付降順）
    articles = json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
    articles.sort(key=lambda a: a["date"], reverse=True)

    # 1. TOPページ: 最新 TOP_N 本
    print(f"\n[TOP] Updating {INDEX_HTML.name} (newest {TOP_N})")
    top_cards = "\n".join(card_top(a) for a in articles[:TOP_N])
    update_file(INDEX_HTML, "<!-- TOP_ARTICLES_START -->", "<!-- TOP_ARTICLES_END -->", top_cards)

    # 2. 記事一覧: 全記事（最新順）
    print(f"\n[LIST] Updating articles/index.html ({len(articles)} articles)")
    list_cards = "\n".join(card_list(a) for a in articles)
    update_file(LIST_HTML, "<!-- ARTICLES_LIST_START -->", "<!-- ARTICLES_LIST_END -->", list_cards)

    # 3. 各記事ページ: Related Articles
    print(f"\n[RELATED] Updating {len(articles)} article pages")
    for article in articles:
        article_html = ARTICLES_DIR / article["slug"] / "index.html"
        if not article_html.exists():
            print(f"  SKIP (not found): {article['slug']}")
            continue
        related = get_related(articles, article["slug"])
        related_cards = "\n".join(card_related(a) for a in related)
        update_file(article_html, "<!-- RELATED_START -->", "<!-- RELATED_END -->", related_cards)

    print(f"\n✓ Done! {len(articles)} articles processed.")
    print(f"  TOP page shows: {', '.join(a['slug'] for a in articles[:TOP_N])}")


if __name__ == "__main__":
    main()
