#!/usr/bin/env python3
"""
Сборка блоков T123 для walk-walk.ru/summer_camp2 (интенсив «Летний лагерь»).

Tilda T123 — лимит ~30 000 символов на блок. Кириллица в T123 часто рендерится
как mojibake → вся не-ASCII кодируется в HTML-сущности &#NNNN; (раздувает ~1.85×).
Поэтому HTML режется на несколько блоков. CSS/JS — внешние ссылки на GitHub Pages.
assets/ → абсолютные URL на CDN (сейчас страница ходит только на CDN Тильды,
локальных ассетов нет — правила ниже оставлены на будущее, когда появятся фото).

Блоки:
- Блок 1: head-хинты + топбар + шапка + меню + hero + «Для кого» + «Что это»
- Блок 2: музыкальные пластинки
- Блок 3: отзывы участниц
- Блок 4: баннер тарифов + тарифы
- Блок 5: вожатский отряд (карусель) — по просьбе заказчика стоит ПОСЛЕ тарифов
- Блок 6: «15 минут» + помощь + футер + sticky-cta + back-to-top + <script>
"""
import re
from pathlib import Path

BASE = Path(__file__).parent
# TODO: подтвердить имя репозитория GitHub Pages для этого лендинга
CDN = "https://npopko55-cmd.github.io/summer-camp"
VER = "camp-O"

html = (BASE / "index.html").read_text(encoding="utf-8")
body = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL).group(1)

# 1. Комментарии прочь, assets → CDN
body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
body = re.sub(r'(href|src)="(assets/[^"]+)"', lambda m: f'{m.group(1)}="{CDN}/{m.group(2)}"', body)
# srcset/imagesrcset — список «путь дескриптор, путь дескриптор». Отдельным
# правилом, потому что общий regex выше ловит только одиночный путь в кавычках.
# Пропустишь — браузер возьмёт srcset (он приоритетнее src), упрётся в
# относительный путь и картинка не отрисуется вообще. Ровно так и случилось
# с hero после перевода на srcset.
def _abs_srcset(m):
    attr, val = m.group(1), m.group(2)
    parts = []
    for item in val.split(','):
        item = item.strip()
        if not item:
            continue
        bits = item.split(None, 1)
        url = bits[0]
        rest = (' ' + bits[1]) if len(bits) > 1 else ''
        if url.startswith('assets/'):
            url = f'{CDN}/{url}'
        parts.append(url + rest)
    return f'{attr}="' + ', '.join(parts) + '"'
body = re.sub(r'(srcset|imagesrcset)="([^"]+)"', _abs_srcset, body)
body = re.sub(r"url\((['\"])(assets/[^'\")]+)\1\)", lambda m: f"url({m.group(1)}{CDN}/{m.group(2)}{m.group(1)})", body)
body = re.sub(r"url\((assets/[^'\")]+)\)", lambda m: f"url({CDN}/{m.group(1)})", body)

# 2. Границы секций (RAW, до encoding)
def pos(patt):
    m = re.search(patt, body)
    if not m:
        raise SystemExit(f"Не нашёл: {patt}")
    return m.start()

# Порядок секций (по прототипу Miro):
# hero(+мини-пункты) → вожатский отряд → музыка → что внутри → отзывы → тарифы → 15 минут → помощь
p_work   = pos(r'<section[^>]*id="workouts"')
p_res    = pos(r'<section[^>]*id="results"')
p_banner = pos(r'<section[^>]*class="rates-banner"')
p_couns  = pos(r'<section[^>]*id="counselors"')   # теперь ПОСЛЕ тарифов
p_fifteen= pos(r'<section[^>]*id="fifteen"')

part_a  = body[:p_work]              # топбар+шапка+меню+hero+«Для кого»+«Что это»
part_b0 = body[p_work:p_res]         # музыкальные пластинки
part_b1 = body[p_res:p_banner]       # отзывы участниц
part_b2 = body[p_banner:p_couns]     # баннер тарифов + тарифы
part_b3 = body[p_couns:p_fifteen]    # вожатский отряд (карусель)
tail    = body[p_fifteen:]           # 15 минут + помощь + футер + sticky + script

# 3. Анти-mojibake: не-ASCII → &#NNNN;
def to_entities(text):
    return "".join(c if ord(c) < 128 else f"&#{ord(c)};" for c in text)

part_a, part_b0, part_b1, part_b2, part_b3, tail = map(
    to_entities, (part_a, part_b0, part_b1, part_b2, part_b3, tail))

# 4. Head-хинты (шрифты те же: Unbounded + Inter; hero-картинка — с CDN Тильды)
HERO_IMG = f"{CDN}/assets/hero/hero-camp2-700.webp"
HEAD_HINTS = f"""<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link rel="preconnect" href="https://npopko55-cmd.github.io" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Unbounded:wght@500;600&family=Inter:wght@400;500;600&display=swap&subset=latin,cyrillic" rel="stylesheet" />
<link rel="preload" as="image" href="{HERO_IMG}" fetchpriority="high"
      imagesrcset="{CDN}/assets/hero/hero-camp2-700.webp 700w, {CDN}/assets/hero/hero-camp2-900.webp 900w, {CDN}/assets/hero/hero-camp2-1100.webp 1100w"
      imagesizes="(max-width: 900px) 85vw, 38vw" />
<link rel="stylesheet" href="{CDN}/styles.css?v={VER}" />
"""
TAIL_SCRIPT = f'\n<script src="{CDN}/script.js?v={VER}"></script>\n'

block1 = HEAD_HINTS + "\n" + part_a + "\n"
block2 = part_b0
block3 = part_b1
block4 = part_b2
block5 = part_b3
block6 = tail + TAIL_SCRIPT

(BASE / "tilda-block-1.html").write_text(block1, encoding="utf-8")
(BASE / "tilda-block-2.html").write_text(block2, encoding="utf-8")
(BASE / "tilda-block-3.html").write_text(block3, encoding="utf-8")
(BASE / "tilda-block-4.html").write_text(block4, encoding="utf-8")
(BASE / "tilda-block-5.html").write_text(block5, encoding="utf-8")
(BASE / "tilda-block-6.html").write_text(block6, encoding="utf-8")

def sz(s):
    n = len(s)
    ok = "OK помещается" if n < 30000 else "!! ПРЕВЫШЕН ЛИМИТ 30000"
    return f"{n:,} chars ({n/1024:.1f} KB)  {ok}"

print("Готово")
print(f"  tilda-block-1.html: {sz(block1)}  — топбар+шапка+меню+hero+для кого+что это")
print(f"  tilda-block-2.html: {sz(block2)}  — музыкальные пластинки")
print(f"  tilda-block-3.html: {sz(block3)}  — отзывы участниц")
print(f"  tilda-block-4.html: {sz(block4)}  — баннер тарифов+тарифы")
print(f"  tilda-block-5.html: {sz(block5)}  — вожатский отряд (карусель)")
print(f"  tilda-block-6.html: {sz(block6)}  — 15 минут+помощь+футер+sticky+script")
print(f"  Лимит T123: 30 000 chars / блок. CSS/JS — с {CDN}")
