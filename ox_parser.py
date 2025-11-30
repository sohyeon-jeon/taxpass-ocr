from bs4 import BeautifulSoup
import json
import re

html = open("parse_data/output_17_43_fix.htm", encoding="utf-8").read()
soup = BeautifulSoup(html, "html.parser")

circled_map = {
    "①": 1, "②": 2, "③": 3, "④": 4, "⑤": 5,
    "⑥": 6, "⑦": 7, "⑧": 8, "⑨": 9, "⑩": 10,
    "⑪": 11, "⑫": 12, "⑬": 13, "⑭": 14, "⑮": 15,
    "⑯": 16, "⑰": 17, "⑱": 18, "⑲": 19, "⑳": 20,
    "㉑": 21, "㉒": 22, "㉓": 23, "㉔": 24, "㉕": 25
}


# -------------------------------------------------------------
# Helper
# -------------------------------------------------------------
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

for theme in themes[:7]:

    theme_name = theme["theme_name"]
    blocks = theme["contents"]

    # 문제 시작 index 수집
    problem_positions = []
    for idx, tag in enumerate(blocks):
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

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                tds = row.find_all("td")
                texts = [clean(td) for td in tds]
                # print(texts)

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
                if len(texts) == 4 and texts[0] in ("O", "X"):
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

        # =============================================
        # (B) P 기반 파싱 — 테이블이 없을 때만 실행
        # =============================================
        temp_problem = {}
        temp_answer = {}

        if not tables:
            for b in problem_block:

                if b.name != "p":
                    continue

                text = clean(b)

                print('text', text)

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
                    print('dddd', m)

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
print(json.dumps(results, ensure_ascii=False, indent=2))
