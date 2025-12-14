import os
import re
import json
from bs4 import BeautifulSoup
from pykospacing import Spacing

'''
테마: 부가가치세 기초이론 → 문제 수: 4
테마: 부가가치세 납세의무 → 문제 수: 11
테마: 과세기간 &납세지 → 문제 수: 18
테마: 총괄납부 vs 사업자단위과세 → 문제 수: 15
테마: 사업자등록 → 문제 수: 12
테마: 과세 거래(1) → 문제 수: 36
테마: 과세 거래(2) → 문제 수: 25
테마: 재화의 공급의제 → 문제 수: 17
테마: 공급시기 &공급장소 → 문제 수: 28
테마: 영세율 → 문제 수: 49
테마: 면세(1) → 문제 수: 16
테마: 면세(2) → 문제 수: 30
테마: 면세포기 → 문제 수: 5
테마: 영세율 vs 면세 → 문제 수: 6
'''

spacing = Spacing()

html = open("parse_data/부가가치세법 총론.htm", encoding="utf-8").read()
soup = BeautifulSoup(html, "html.parser")

circled_map = {
    "①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5,
    "⑥": 6, "⑦": 7, "⑧": 8, "⑨": 9, "⑩": 10,
    "⑪": 11, "⑫": 12, "⑬": 13, "⑭": 14, "⑮": 15,
    "⑯": 16, "⑰": 17, "⑱": 18, "⑲": 19, "⑳": 20,
    "㉑": 21, "㉒": 22, "㉓": 23, "㉔": 24, "㉕": 25,
    "㉖": 26, "㉗": 27, "㉘": 28, "㉙": 29, "㉚": 30,
    "㉛": 31, "㉜": 32, "㉝": 33, "㉞": 34, "㉟": 35,
    "㊱": 36, "㊲": 37, "㊳": 38, "㊴": 39, "㊵": 40,
    "㊶": 41, "㊷": 42, "㊸": 43, "㊹": 44, "㊺": 45,
    "㊻": 46, "㊼": 47, "㊽": 48, "㊾": 49, "㊿": 50
}

def clean(t):
    return t.get_text(" ", strip=True)

def parse_question_number(text):
    m = re.match(r"^(\d+)\s+(.+)", text)
    if m:
        return int(m.group(1)), text

    if re.match(r"^\d+$", text):
        return int(text), None

    return None, None

def clean_li_without_tables(li):
    li_copy = BeautifulSoup(str(li), "html.parser")
    for t in li_copy.find_all("table"):
        t.decompose()
    return li_copy.get_text(" ", strip=True)

TARGET_KEYS = {"question_title", "raw_text", "explanation"}

CORRECTION_MAP = {
    "。":"O",
    "전 단계 세액공제법": "전단계세액공제법",
    "영리 목적": "영리목적",
    "최종 과세기간 분": "최종과세기간분",
    "농지 개량 작업": "농지개량작업",
    "자기 농지의 확장": "자기농지의 확장",
    "내국법인이상법에": "내국법인이 상법에",
    "계속 등기": "계속등기",
    "광업원 부": "광업 원부",
    "이동통신 역무를": "이동통신역무를",
    "자가주된": "자가 주된",
    "주사업장 총괄납부 신청서": "주사업장총괄납부신청서"
    , "주사업장 총괄납부": "주사업장총괄납부",
    "사업자 단위 과세사업": "사업자단위과세사업",
    "사업자 단위 과세": "사업자단위과세",
    "사업 개시 일": "사업개시일",
    "과세 대상 거래": "과세대상거래",
    "거래 중과세대상거래": "거래 중 과세대상거래"
    , "계속 적•반복적": "계속적•반복적",
    "과 세 거래": "과세거래",
    "등도주된": "등도 주된",
    "부가가 차세 과세 대상": "부가가차세 과세대상",
    "열등관리": "열 등 관리",
    "弓": "여",
    "내 국신용장": "내국신용장"
    , "위하 여": "위하여",
    "선（기 ）적일": "선(기）적일",
    "기성고대금": "기성고 대금",
    "인도 일": "인도일",
    "선발급 시선 발급 특례": "선발급 시 선발급특례"
    , "불문영세율": "불문 영세율",
    "말한 다": "말한다",
    "수출 재화임가공 용역": "수출재화임가공용역"
    , "주한 미국 군": "주한미국군"
    , "와국": "외국"
    , "간이과세포 기 여부": "간이과세포기여부"
    , "내국산 용장": "내국신용장"
    , "공급돠는": "공급되는",
    "상품 중 개용역": "상품중개용역"
    , "내국 신용장": "내국신용장",
    "외국인도 수출": "외국인도수출"
    , "수탁 가공사업자": "수탁가공 사업자"
    , "수출재화임가공용역": "수출재화 임가공용역"
    , "대하여 도": "대하여도",
    "때에도주된": "때에도 주된"
    , "용역으로 서": "용역으로서",
    "원 생산물": "원생산물"
    , "©": ""
    , "®": ""
    , "시 외우 등 고속버스": "시외우등고속버스"
    , "대상이 다": "대상이다"
    , "면세포 기": "면세포기"
}


def clean_text(text: str, remove_all_spaces=False) -> str:
    """문자열 전처리 규칙 정의"""
    if text is None:
        return text

    # 1) HTML 제거
    text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)

    # 2) 문장 맨 앞의 circled 번호 제거
    # 기존 circled 숫자 제거 + 일반 숫자 제거
    text = re.sub(r"^(?:[①-㊿]|\d+[.)]?)\s*", "", text)

    # 3) 중복 공백 제거
    text = re.sub(r"\s+", " ", text).strip()

    # 4) circled 번호 뒤 공백 정리
    text = re.sub(r"(①|②|③|④|⑤|⑥|⑦|⑧|⑨|⑩)\s+", r"\1 ", text)

    # 5) 띄어쓰기 및 맞춤법 처리
    text = spacing(text.replace(" ", ""))

    # 6) 단어 교정 단계 추가(단어치환)
    for wrong, right in CORRECTION_MAP.items():
        text = text.replace(wrong, right)

    return text


def preprocess(obj):
    """특정 속성만 전처리하는 재귀 함수"""

    # dict → 내부 key/value 재귀 처리
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            # k가 대상 속성이면 clean_text 적용
            if k in TARGET_KEYS and isinstance(v, str):
                new_obj[k] = clean_text(v)
            else:
                new_obj[k] = preprocess(v)
        return new_obj

    # list → 요소마다 재귀 처리
    if isinstance(obj, list):
        return [preprocess(item) for item in obj]

    # 그 외 (int, None 등) → 그대로 반환
    return obj


# -------------------------------------------------------------
# 1) Theme 블록 분리
# -------------------------------------------------------------
all_tags = soup.find_all(["p", "table", "ul"])

themes = []
current_theme = None
current_blocks = []

i = 0
N = len(all_tags)

while i < N:
    tag = all_tags[i]

    if tag.name == "p" and clean(tag) == "Theme":
        if current_theme:
            themes.append({
                "theme_name": current_theme,
                "contents": current_blocks
            })
            current_blocks = []

        current_theme = clean(all_tags[i + 1])
        i += 2
        continue

    if current_theme:
        current_blocks.append(tag)

    i += 1

if current_theme:
    themes.append({
        "theme_name": current_theme,
        "contents": current_blocks
    })

# -------------------------------------------------------------
# 2) Theme 내부 문제 파싱
# -------------------------------------------------------------
results = []
last_q_num = 0
for theme in themes:
    # print('theme',theme)

    theme_name = theme["theme_name"]
    blocks = theme["contents"]

    # 문제 시작 index 수집
    problem_positions = []
    for idx, tag in enumerate(blocks):
        # print('tag',theme_name,idx,tag)
        text = clean(tag)
        num, title = parse_question_number(text)

        if num is not None:

            if last_q_num == 0:
                if num != 1:
                    continue
            else:
                if num != last_q_num + 1:
                    continue

            last_q_num = num
            problem_positions.append((idx, num, title))

    problem_positions.append((len(blocks), None, None))

    # print('problem_positions',problem_positions)
    # ---------------------------------------------------------
    # 문제 단위 처리
    # ---------------------------------------------------------
    for p in range(len(problem_positions) - 1):

        start_idx, num, title = problem_positions[p]
        end_idx, _, _ = problem_positions[p + 1]

        if title is None:
            if start_idx + 1 < len(blocks) and blocks[start_idx + 1].name == "p":
                title = clean(blocks[start_idx + 1])
            else:
                title = str(num)

        problem_block = blocks[start_idx + 1: end_idx]

        # =============================================
        # (A) table 기반 파싱
        # =============================================
        parsed_items_table = []
        li_idx = 0

        tables = [b for b in problem_block if b.name == "table"]

        uls = [b for b in problem_block if b.name == "ul"]

        ul_li = []
        for u in uls:
            ul_li.extend(u.find_all("li"))

        paragraphs = [b for b in problem_block if b.name == "p"]

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                tds = row.find_all("td")
                texts = [clean(td) for td in tds]
                # print('texts',texts)

                if not texts:
                    continue

                # Case 1: [문장, ①, O]
                if len(texts) == 3 and texts[2] in ("O", "X") and re.match(r"^[①-㊿]+$", texts[1]):
                    index = texts[1]
                    answer = texts[2]

                    circled_index = circled_map[index]
                    #
                    # print('ul_li',ul_li)
                    # print('index',index)
                    # print('circled_index',circled_index)
                    # print(len(ul_li))
                    # print(li_idx)

                    desc = clean_li_without_tables(ul_li[circled_index - len(ul_li) + 1])
                    # print('desc',desc)

                    parsed_items_table.append({
                        "index": index,
                        "raw_text": desc,
                        "answer": answer,
                        "explanation": texts[0]
                    })

                    li_idx += 1
                    continue

                # Case 2: [O, ①, 내용]
                if len(texts) == 3 and texts[0] in ("O", "X"):
                    answer = texts[0]
                    index = texts[1]

                    desc = clean(ul_li[li_idx]) if li_idx < len(ul_li) else texts[2]

                    parsed_items_table.append({
                        "index": index,
                        "raw_text": desc,
                        "answer": answer,
                        "explanation": texts[2]
                    })
                    li_idx += 1
                    continue

                # Case 3: 5칸 구조
                if len(texts) == 5 and texts[-1] in ("O", "X") and re.match(r"^[①-㊿]+$", texts[-2]) and re.match(
                        r"^[①-⑳]+$", texts[0]):
                    index = texts[-2]
                    answer = texts[-1]
                    desc = texts[1]

                    parsed_items_table.append({
                        "index": index,
                        "raw_text": desc,
                        "answer": answer,
                        "explanation": texts[2]
                    })

                    li_idx += 1
                    continue

                if len(texts) == 5 and texts[-1] in ("O", "X") and re.match(r"^[①-⑳]+$", texts[1]) and re.match(
                        r"^[①-⑳]+$", texts[-2]):
                    index = texts[1]
                    answer = texts[-1]
                    desc = texts[0]
                    # print('dd', desc)

                    parsed_items_table.append({
                        "index": index,
                        "raw_text": desc,
                        "answer": answer,
                        "explanation": texts[2]
                    })

                    li_idx += 1
                    continue

                if len(texts) == 5 and texts[0] in ("O", "X") and re.match(r"^[①-㊿]+$", texts[1]) and re.match(
                        r"^[①-㊿]+$", texts[-2]):
                    index = texts[1]
                    answer = texts[0]
                    desc = texts[-1]
                    # print('dd', desc)

                    parsed_items_table.append({
                        "index": index,
                        "raw_text": desc,
                        "answer": answer,
                        "explanation": texts[2]
                    })

                    li_idx += 1
                    continue

                # Case 4: 4칸 구조
                if len(texts) == 4 and texts[0] in ("O", "X") and re.match(r"^[①-㊿]+$", texts[2]):
                    index = texts[2]
                    answer = texts[0]
                    desc = texts[-1]

                    parsed_items_table.append({
                        "index": index,
                        "raw_text": desc,
                        "answer": answer,
                        "explanation": texts[1]
                    })
                    li_idx += 1
                    continue

                # 추가
                if len(texts) == 4 and texts[0] in ("O", "X") and re.match(r"^[①-㊿]+$", texts[1]):
                    index = texts[1]
                    answer = texts[0]
                    desc = texts[-1]

                    parsed_items_table.append({
                        "index": index,
                        "raw_text": desc,
                        "answer": answer,
                        "explanation": texts[2]
                    })
                    li_idx += 1
                    continue

                if len(texts) == 4 and texts[-1] in ("O", "X") and re.match(r"^[①-㊿]+$", texts[0]):
                    # print('tt',texts)

                    index = texts[0]
                    answer = texts[-1]
                    desc = texts[1]

                    parsed_items_table.append({
                        "index": index,
                        "raw_text": desc,
                        "answer": answer,
                        "explanation": texts[2]
                    })
                    li_idx += 1

                    continue

        # =============================================
        # (B) P 기반 파싱 — 테이블이 없을 때만 실행
        # =============================================
        temp_problem = {}
        temp_answer = {}

        for b in paragraphs:

            if b.name != "p":
                continue

            text = clean(b)

            # print('text', text)

            # ---- 문장 중간에 "⑥ X" ----
            m = re.search(r'([①-㊿])\s*([OXox])', text)

            if m:
                index = m.group(1)
                answer = m.group(2).upper()
                explanation = (text[:m.start()] + text[m.end():]).strip()

                temp_answer[index] = {
                    "index": index,
                    "answer": answer,
                    "explanation": explanation
                }
                continue

            # ---- 보기형 "① 내용…" ----
            m = re.match(r'^([①-㊿])\s*(.+)$', text)
            if m:
                index = m.group(1)
                desc = m.group(2).strip()
                # print('dddd', m)

                temp_problem[index] = {
                    "index": index,
                    "raw_text": desc
                }
                continue

        # =============================================
        # (C) table + p 기반 merge
        # =============================================
        merged = {}

        # 1) table 결과
        for item in parsed_items_table:
            merged[item["index"]] = item

        # 2) p 기반 보기
        for idx, v in temp_problem.items():
            if idx not in merged:
                merged[idx] = v
            else:
                merged[idx]["raw_text"] = v["raw_text"]

        # 3) p 기반 정답
        for idx, v in temp_answer.items():
            if idx not in merged:
                merged[idx] = v
            else:
                merged[idx]["answer"] = v["answer"]
                merged[idx]["explanation"] = v["explanation"]

        final_items = [merged[k] for k in sorted(merged.keys())]

        # =============================================
        # 문제 저장
        # =============================================
        results.append({
            "theme": theme_name,
            "question_number": num,
            "question_title": title,
            "items": final_items
        })

# -------------------------------------------------------------
# 출력
# -------------------------------------------------------------
cleaned_result = preprocess(results)

# 숫자기호 -> 숫자로 치환
for q in cleaned_result:
    for item in q.get("items", []):
        idx = item.get("index")
        if isinstance(idx, str) and idx in circled_map:
            item["index"] = circled_map[idx]

print(json.dumps(cleaned_result, ensure_ascii=False, indent=2))

output_dir = "parse_data/output"
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, "부가가치세법 총론.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(cleaned_result, f, ensure_ascii=False, indent=2)

# theme 개수


# 각 theme 안의 item 개수 출력(확인용)
# for theme in results:
#     print(f"테마: {theme['theme']} → 문제 수: {len(theme['items'])}")
#
# theme_count = len(results)
# print("\n총 theme 개수:", theme_count)
