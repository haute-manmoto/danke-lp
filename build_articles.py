#!/usr/bin/env python3
"""
build_articles.py — だんけLP 記事自動更新スクリプト

使い方:
  cd danke_lp
  python3 build_articles.py

articles.json に記事を追加してからこのスクリプトを実行すると、
以下が自動更新される:
  - index.html          : TOPページ の Articles セクション（最新4本）
  - articles/index.html : 記事一覧（最新順）
  - articles/*/index.html: 各記事の Related Articles（関連度順）
                           + Related セクション全体のラッパー
                           + store-info-compact / footer / script（共通テンプレート）

新記事を追加するワークフロー:
  1. articles/[slug]/index.html を _template.html から作成
  2. articles.json にエントリを追加
  3. python3 build_articles.py を実行
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
# 共通テンプレート（全記事ページで統一）
# ─────────────────────────────────────────

# Related Articles セクション（カード部分は {cards} で置換）
RELATED_SECTION = """\
<!-- ===================== RELATED ARTICLES ===================== -->
<section style="background:var(--dark); padding:clamp(3rem,6vw,5rem) clamp(1rem,4vw,2rem);">
  <div style="max-width:900px; margin:0 auto;">
    <h2 style="color:var(--light); text-align:center; margin-bottom:2rem; font-family:var(--font-heading);">
      <span data-lang="en">More Articles</span>
      <span data-lang="zh">更多文章</span>
      <span data-lang="ko">더 많은 기사</span>
    </h2>
    <div class="articles-grid" style="padding:0;">
<!-- RELATED_START -->
{cards}
<!-- RELATED_END -->
    </div>
  </div>
</section>"""

# 記事ページ末尾の共通ブロック（store-info + footer + script）
ARTICLE_SUFFIX = """\

<!-- ===================== STORE INFO COMPACT ===================== -->
<section class="store-info-compact">
  <div class="store-info-compact-inner">
    <div class="store-info-compact-item">
      <svg class="compact-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
        <circle cx="12" cy="10" r="3"/>
      </svg>
      <div>
        <h4>
          <span data-lang="en">Address</span>
          <span data-lang="zh">地址</span>
          <span data-lang="ko">주소</span>
        </h4>
        <p>
          <span data-lang="en">Nishida Bldg 1F, 1-12-3 Tenjinbashi, Kita-ku, Osaka</span>
          <span data-lang="zh">大阪府大阪市北区天神桥1-12-3 西田大楼 1F</span>
          <span data-lang="ko">오사카부 오사카시 기타구 텐진바시 1-12-3 니시다빌딩 1F</span>
        </p>
      </div>
    </div>
    <div class="store-info-compact-item">
      <svg class="compact-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12 6 12 12 16 14"/>
      </svg>
      <div>
        <h4>
          <span data-lang="en">Hours</span>
          <span data-lang="zh">营业时间</span>
          <span data-lang="ko">영업시간</span>
        </h4>
        <p>
          <span data-lang="en">Mon–Sat 17:30–23:00<br>Closed Sun &amp; Holidays</span>
          <span data-lang="zh">周一至周六 17:30–23:00<br>周日及节假日休息</span>
          <span data-lang="ko">월–토 17:30–23:00<br>일요일·공휴일 휴무</span>
        </p>
      </div>
    </div>
    <div class="store-info-compact-item">
      <svg class="compact-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/>
      </svg>
      <div>
        <h4>
          <span data-lang="en">Telephone</span>
          <span data-lang="zh">电话</span>
          <span data-lang="ko">전화</span>
        </h4>
        <p><a href="tel:06-6882-6675">06-6882-6675</a></p>
      </div>
    </div>
    <div class="store-info-compact-item">
      <svg class="compact-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <rect x="2" y="6" width="20" height="12" rx="2"/>
        <path d="M2,10 L22,10"/>
      </svg>
      <div>
        <h4>
          <span data-lang="en">Access</span>
          <span data-lang="zh">交通</span>
          <span data-lang="ko">교통</span>
        </h4>
        <p>
          <span data-lang="en">5 min walk from JR Osaka-Tenmangu Sta. or Minami-Morimachi Sta.</span>
          <span data-lang="zh">从JR大阪天满宫站或地铁南森町站步行5分钟</span>
          <span data-lang="ko">JR 오사카텐만구역 또는 미나미모리마치역에서 도보 5분</span>
        </p>
        <a href="https://www.google.com/maps/search/笑門酒房+だんけ+天神橋" target="_blank" rel="noopener noreferrer" class="compact-cta" style="margin-top:0.75rem;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="width:16px; height:16px;">
            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
            <circle cx="12" cy="10" r="3"/>
          </svg>
          <span data-lang="en">Google Maps</span>
          <span data-lang="zh">谷歌地图</span>
          <span data-lang="ko">구글 지도</span>
        </a>
      </div>
    </div>
  </div>
</section>

<!-- ===================== FOOTER ===================== -->
<footer class="footer">
  <nav style="margin-bottom:0.75rem; display:flex; gap:1.5rem; justify-content:center; flex-wrap:wrap; font-size:0.85rem;">
    <a href="../../" style="color:var(--amber); text-decoration:none;">Home</a>
    <a href="../../menu/yakitori/" style="color:var(--amber); text-decoration:none;">
      <span data-lang="en">Yakitori</span><span data-lang="zh">烤鸡串</span><span data-lang="ko">야키토리</span>
    </a>
    <a href="../../menu/sake-shochu/" style="color:var(--amber); text-decoration:none;">
      <span data-lang="en">Sake &amp; Shochu</span><span data-lang="zh">清酒·烧酒</span><span data-lang="ko">사케·소주</span>
    </a>
    <a href="../" style="color:var(--amber); text-decoration:none;">
      <span data-lang="en">Articles</span><span data-lang="zh">文章</span><span data-lang="ko">기사</span>
    </a>
  </nav>
  <p>&copy; 笑門酒房 だんけ &mdash; Tenjinbashi, Osaka</p>
</footer>

<!-- ===================== JAVASCRIPT ===================== -->
<script>
(function() {
  'use strict';

  var langBtns = document.querySelectorAll('[data-switch-lang]');
  langBtns.forEach(function(btn) {
    btn.addEventListener('click', function() {
      var lang = this.getAttribute('data-switch-lang');
      document.body.setAttribute('data-active-lang', lang);
      langBtns.forEach(function(b) { b.classList.remove('active'); });
      this.classList.add('active');
    });
  });

  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (!prefersReduced) {
    var reveals = document.querySelectorAll('.reveal');
    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

    reveals.forEach(function(el) {
      if (el.closest('.page-header')) {
        el.classList.add('visible');
      } else {
        observer.observe(el);
      }
    });
  } else {
    document.querySelectorAll('.reveal').forEach(function(el) {
      el.classList.add('visible');
    });
  }

  document.querySelectorAll('a[href^="#"]').forEach(function(a) {
    a.addEventListener('click', function(e) {
      var target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });
})();
</script>
</body>
</html>"""


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


def normalize_article(path, related_cards):
    """
    記事ページの Related セクション以降を標準テンプレートで統一する。
    - Related セクション全体（wrapper含む）を RELATED_SECTION テンプレートで置換
    - store-info-compact / footer / script を ARTICLE_SUFFIX で置換
    """
    path = Path(path)
    content = path.read_text(encoding="utf-8")

    # <article> タグの終わりを探し、それ以降を標準テンプレートで上書き
    article_close = content.rfind("</article>")
    if article_close == -1:
        print(f"  SKIP normalize (no </article>): {path.name}")
        return

    before_related = content[:article_close + len("</article>")]
    new_related = RELATED_SECTION.format(cards=related_cards)
    new_content = before_related + "\n\n" + new_related + ARTICLE_SUFFIX + "\n"

    if new_content != content:
        path.write_text(new_content, encoding="utf-8")
        print(f"  Normalized: {path.relative_to(BASE_DIR.parent)}")


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

    # 3. 各記事ページ: Related セクション + store-info + footer + script を標準化
    print(f"\n[NORMALIZE] Updating {len(articles)} article pages")
    for article in articles:
        article_html = ARTICLES_DIR / article["slug"] / "index.html"
        if not article_html.exists():
            print(f"  SKIP (not found): {article['slug']}")
            continue
        related = get_related(articles, article["slug"])
        related_cards = "\n".join(card_related(a) for a in related)
        normalize_article(article_html, related_cards)

    print(f"\n✓ Done! {len(articles)} articles processed.")
    print(f"  TOP page shows: {', '.join(a['slug'] for a in articles[:TOP_N])}")
    print(f"  store-info / footer / script: all normalized from template")


if __name__ == "__main__":
    main()
