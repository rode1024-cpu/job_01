"""잡코리아 페이지 구조 점검용 (수동 실행 전용). 결과는 bot/probe/report.txt 에 저장된다.
검색 페이지의 파라미터(지역·정렬·페이지)와 상세 페이지의 본문 위치를 찾는 용도이며, 개인정보나 비밀값은 다루지 않는다."""
import collections
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "Mozilla/5.0 (personal job alert; low frequency)"}
OUT = Path(__file__).parent / "probe" / "report.txt"
lines = []


def log(*a):
    lines.append(" ".join(str(x) for x in a))


def get(url, **kw):
    r = requests.get(url, headers=UA, timeout=(10, 25), **kw)
    log(f"GET {r.url} -> {r.status_code}, {len(r.text)}자")
    return r


def ctx(t, i, n=160):
    return re.sub(r"\s+", " ", t[max(0, i - n):i + n])


def search_report():
    base = "https://www.jobkorea.co.kr/Search/"
    r = get(base, params={"stext": "온라인MD", "tabType": "recruit"})
    t = r.text
    ids = list(dict.fromkeys(re.findall(r"/Recruit/GI_Read/(\d+)", t)))
    log("검색 결과 공고 ID 수:", len(ids), ids[:3])

    log("\n[결과 카드 HTML 샘플]")
    i = t.find("/Recruit/GI_Read/")
    log(re.sub(r"\s+", " ", t[max(0, i - 600):i + 1200]) if i >= 0 else "없음")

    log("\n[검색 페이지 링크의 파라미터 이름]")
    names = collections.Counter()
    samples = {}
    for m in re.finditer(r"[?&;]([A-Za-z_][A-Za-z_0-9]*)=([^&\"'<> ]{0,30})", t):
        names[m.group(1)] += 1
        samples.setdefault(m.group(1), set()).add(m.group(2))
    for k, c in names.most_common(40):
        log(f"  {k} x{c} 예: {sorted(samples[k])[:4]}")

    log("\n[정렬/지역/페이지 관련 문구]")
    seen = 0
    for m in re.finditer(r"(?i)(orderby|order_by|sort|local|area|page_no|pageno)", t):
        log("  ..." + ctx(t, m.start(), 90))
        seen += 1
        if seen >= 18:
            break

    log("\n[폼 입력 요소]")
    soup = BeautifulSoup(t, "html.parser")
    for el in soup.find_all(["input", "select"])[:40]:
        log(f"  {el.name} name={el.get('name')} id={el.get('id')} value={str(el.get('value'))[:30]}")

    log("\n[페이지 넘김 시험]")
    for key in ("Page_No", "page", "pageNo"):
        try:
            r2 = get(base, params={"stext": "온라인MD", "tabType": "recruit", key: 2})
            ids2 = list(dict.fromkeys(re.findall(r"/Recruit/GI_Read/(\d+)", r2.text)))
            log(f"  {key}=2 -> 공고 {len(ids2)}건, 1페이지와 겹침 {len(set(ids) & set(ids2))}건")
        except Exception as e:
            log(f"  {key}=2 실패: {type(e).__name__}")
        time.sleep(2)
    return ids


def detail_report(gid):
    log(f"\n==== 상세 {gid} ====")
    r = get(f"https://www.jobkorea.co.kr/Recruit/GI_Read/{gid}")
    soup = BeautifulSoup(r.text, "html.parser")
    og = soup.find("meta", property="og:title")
    log("og:title:", og.get("content") if og else None)
    text = soup.get_text(" ", strip=True)
    log("본문 길이:", len(text))
    log("앞 400자:", text[:400])
    for kw in ("근무지역", "근무지", "급여", "연봉", "경력", "고용형태", "접수기간", "마감"):
        hits = [n for n in soup.find_all(string=re.compile(kw))][:2]
        for n in hits:
            p = n.parent
            chain = " < ".join(f"{a.name}.{'.'.join(a.get('class', []))[:30]}" for a in [p] + list(p.parents)[:3])
            near = re.sub(r"\s+", " ", p.parent.get_text(" ", strip=True))[:140]
            log(f"[{kw}] {chain} :: {near}")
    log("큰 블록(텍스트 길이순):")
    blocks = [(len(b.get_text(strip=True)), b.name, b.get("id"), ".".join(b.get("class", []))[:40])
              for b in soup.find_all(["div", "section", "article"]) if b.get("id") or b.get("class")]
    for n, name, i, c in sorted(blocks, reverse=True)[:10]:
        log(f"  {n}자 {name} id={i} class={c}")
    log("추천/광고 의심 영역:", [b.get("class") for b in soup.find_all(class_=re.compile("recommend|related|banner|ad", re.I))][:6])


def main():
    try:
        ids = search_report()
        for gid in ids[:2]:
            time.sleep(2)
            detail_report(gid)
    except Exception as e:
        log("오류:", type(e).__name__, str(e)[:200])
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(lines)[:60000], encoding="utf-8")
    print("\n".join(lines)[:3000])


if __name__ == "__main__":
    main()
