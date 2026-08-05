#!/usr/bin/env python3
"""
Сборка блоков T123 БЕЗ внешнего хостинга: стили и скрипт едут внутрь Тильды,
ассеты — на CDN Тильды. Отличие от build-tilda-split.py, где CSS/JS/картинки
тянутся с GitHub Pages.

Зачем: GitHub Pages в РФ периодически недоступен без VPN. Если он не открылся,
у части аудитории страница остаётся без стилей и без фотографий — то есть
рекламный трафик уходит в пустоту. Тильдовский CDN такой проблемы не имеет.

Как пользоваться:
  1. Прогнать без карты ссылок — соберутся style/script-блоки и список файлов,
     которые надо загрузить в Тильду (assets-to-upload.txt).
  2. Загрузить файлы в Тильду, собрать ссылки в tilda-assets.json:
       { "assets/hero/hero-camp2-700.webp": "https://static.tildacdn.com/...", ... }
  3. Прогнать снова — соберутся все блоки уже с тильдовскими ссылками.

Порядок вставки на странице: сначала СТИЛИ (иначе на долю секунды покажется
нестилизованный текст), потом блоки разметки, СКРИПТ — последним.
"""
import json
import re
from pathlib import Path

BASE = Path(__file__).parent
LIMIT = 30000            # лимит символов на блок T123
MAP_FILE = BASE / "tilda-assets.json"
OUT = BASE / "tilda-standalone"
OUT.mkdir(exist_ok=True)

html = (BASE / "index.html").read_text(encoding="utf-8")
css = (BASE / "styles.css").read_text(encoding="utf-8")
js = (BASE / "script.js").read_text(encoding="utf-8")


# ---------- 1. Чистка CSS -----------------------------------------------
def minify_css(s):
    """Комментарии и лишние пробелы прочь. Комментарии в styles.css подробные
    (в них причины решений), поэтому чистим только копию для Тильды —
    исходник остаётся читаемым."""
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.DOTALL)
    s = re.sub(r"\s*\n\s*", "\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\s*([{};:,])\s*", r"\1", s)
    s = re.sub(r";}", "}", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()


css_min = minify_css(css)


# ---------- 2. Карта ассетов ---------------------------------------------
asset_map = {}
if MAP_FILE.exists():
    asset_map = json.loads(MAP_FILE.read_text(encoding="utf-8"))

used = sorted(set(
    re.findall(r'(?:src|href)="(assets/[^"]+)"', html)
    + [u.strip().split()[0] for a in re.findall(r'(?:srcset|imagesrcset)="([^"]+)"', html)
       for u in a.split(",") if u.strip().startswith("assets/")]
))
missing = [a for a in used if a not in asset_map]


# ---------- 3. Подстановка ссылок в разметку ------------------------------
body = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL).group(1)
body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)


def sub_single(m):
    attr, path = m.group(1), m.group(2)
    return f'{attr}="{asset_map.get(path, path)}"'


def sub_set(m):
    attr, val = m.group(1), m.group(2)
    out = []
    for item in val.split(","):
        item = item.strip()
        if not item:
            continue
        bits = item.split(None, 1)
        url = asset_map.get(bits[0], bits[0])
        out.append(url + ((" " + bits[1]) if len(bits) > 1 else ""))
    return f'{attr}="' + ", ".join(out) + '"'


body = re.sub(r'(href|src)="(assets/[^"]+)"', sub_single, body)
body = re.sub(r'(srcset|imagesrcset)="([^"]+)"', sub_set, body)

# стили и скрипт теперь внутри Тильды — внешние подключения не нужны
body = re.sub(r'<link rel="stylesheet"[^>]*styles\.css[^>]*>\s*', "", body)
body = re.sub(r'<script[^>]*script\.js[^>]*></script>\s*', "", body)


# ---------- 4. Анти-mojibake ---------------------------------------------
def to_entities(text):
    return "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in text)


# ---------- 5. Нарезка ----------------------------------------------------
def split_css(text, limit):
    """Режем по границам правил, а не посреди селектора — иначе половина
    правила в одном блоке, половина в другом, и оба ломаются."""
    parts, cur = [], ""
    for chunk in re.findall(r"[^}]*}|[^}]+$", text):
        if len(cur) + len(chunk) > limit - 4000 and cur:
            parts.append(cur)
            cur = ""
        cur += chunk
    if cur:
        parts.append(cur)
    return parts


FONT_LINK = re.search(r'<link[^>]+fonts\.googleapis\.com/css2[^>]*>', html).group(0)

HEAD = f"""<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
{FONT_LINK}
"""

files = []
for i, part in enumerate(split_css(css_min, LIMIT), 1):
    head = HEAD if i == 1 else ""
    files.append((f"style-{i}.html", head + "<style>\n" + part + "\n</style>\n"))

# разметка — теми же границами секций, что и в основном сборщике
def pos(patt):
    m = re.search(patt, body)
    if not m:
        raise SystemExit(f"Не нашёл: {patt}")
    return m.start()


cuts = [0, pos(r'<section[^>]*id="workouts"'), pos(r'<section[^>]*id="results"'),
        pos(r'<section[^>]*class="rates-banner"'), pos(r'<section[^>]*id="fifteen"'), len(body)]
labels = ["топбар+шапка+меню+hero+вожатые", "музыка+что внутри", "отзывы",
          "баннер+тарифы", "15 минут+помощь+футер"]
for i in range(5):
    files.append((f"block-{i+1}.html", to_entities(body[cuts[i]:cuts[i+1]])))

files.append(("script.html", "<script>\n" + js + "\n</script>\n"))

for name, content in files:
    (OUT / name).write_text(content, encoding="utf-8")

(OUT / "assets-to-upload.txt").write_text(
    "Загрузить в Тильду и вписать ссылки в tilda-assets.json:\n\n" +
    "\n".join(f"{'  OK  ' if a in asset_map else '  --  '}{a}" for a in used) +
    f"\n\nвсего {len(used)}, уже есть ссылок: {len(used) - len(missing)}\n",
    encoding="utf-8")

print(f"Готово → {OUT}")
for name, content in files:
    n = len(content)
    flag = "OK" if n < LIMIT else "!! ПРЕВЫШЕН ЛИМИТ"
    print(f"  {name:16} {n:>7,} chars ({n/1024:5.1f} KB)  {flag}")
print(f"\nАссетов в разметке: {len(used)}, без тильдовских ссылок: {len(missing)}")
if missing:
    print("Пока не заменены (останутся относительными путями!):")
    for a in missing[:6]:
        print("   ", a)
    if len(missing) > 6:
        print(f"    … ещё {len(missing)-6}")
    print(f"Список целиком: {OUT/'assets-to-upload.txt'}")
