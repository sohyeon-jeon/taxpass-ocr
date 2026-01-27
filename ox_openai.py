import os
import re
import json
import base64
import fitz  # PyMuPDF
import openai
from dotenv import load_dotenv

"""
재배치가 완료된 세법 OX 문제 PDF로
Vision OCR을 수행하고, 문제 단위의 구조화된 JSON 데이터를 생성하는 스크립트입니다.
"""

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

PDF_PATH = "data/ox_question/2026_세법_말문제_OX_정리본.pdf"
OUTPUT_DIR = "data/ox_question/ox_json"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_total_pages(pdf_path):
    doc = fitz.open(pdf_path)
    total = doc.page_count
    doc.close()
    return total


TOTAL_PAGES = get_total_pages(PDF_PATH)
TARGET_PAGES = range(1, TOTAL_PAGES + 1)


def pdf_page_to_image(pdf_path, page_number, output_image_path, zoom=2):
    """
    PDF → 이미지
    """
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number - 1)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    pix.save(output_image_path)
    doc.close()


def encode_image(image_path):
    """
    이미지 → base64
    """
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def vision_ocr(base64_image):
    """
    OX 문제 이미지에 대한 Vision OCR 프롬프트

    - 이 프롬프트는 재배치가 완료된 OX 문제 페이지를 대상으로 한다.
    - 문제, 해설, 정답(O/X)의 시각적 순서를 기준으로 OCR을 수행한다.

    [문제 판별 기준]
    - 실제 문제는 반드시 원문자 번호(①②③…㊿)로 시작한다.
    - 단순 안내 문구(예: “다음의 설명 중 옳은 것은…”)는 문제로 취급하지 않는다.
    - 섹션 번호, 테마 제목, 장 번호 등은 모두 무시한다.

    [문제 구성 규칙]
    - 하나의 문제는 아래 순서로 배치되어 있을 수 있다.
      1) 문제 지문
      2) 해설 영역(파란 박스, 존재하지 않을 수 있음)
      3) 정답 표시(O 또는 X)

    [중요 제약]
    - 해설이 없는 문제도 존재할 수 있으며, 이 경우 해설은 빈 값으로 출력해야 한다.
    - 절대 다른 문제의 해설을 추론하거나 가져오지 않는다.
    - 문제 번호나 의미를 기반으로 추론하지 않고,
      오직 위에서 아래로 보이는 순서만 사용한다.

    [출력 형식]
    - 각 문제는 반드시 3줄로 출력한다.
      Q: 문제 지문
      E: 해설(없으면 빈 줄)
      A: O 또는 X

    - JSON이나 추가 텍스트 없이 순수 텍스트만 반환한다.
    - OCR 결과의 한국어 원문을 그대로 유지한다.

    → 이 프롬프트의 목적은
      OCR 결과를 후처리하기 쉬운 고정 포맷으로 안정적으로 추출하는 것이다.
    """
    system_prompt = """
You are an OCR engine.

This image contains multiple OX questions.
The page has ALREADY been rearranged.

IMPORTANT STRUCTURE RULES:

- There are COMMON INSTRUCTION LINES such as:
  "다음의 설명 중 옳은 것은 ○표, 틀린 것은 ×표로 구분하시오."
  These are NOT questions.
  NEVER include them as question text.

- A REAL question ALWAYS:
  - Starts with ANY circled number
    (①②③④⑤⑥⑦⑧⑨⑩⑪⑫…㊿)
  - Contains a specific factual statement to judge O or X

- Section numbers like "03", "04", "Theme", or titles
  are NOT questions and must be ignored.

For EACH REAL question, the visible order MAY be:

1. Question text
   (starts with ANY circled number: ①②③④⑤⑥⑦⑧⑨⑩⑪…㊿)
2. Explanation text (inside the blue box) — MAY BE EMPTY
3. A single answer mark: O or X

CRITICAL RULES:
- Explanation text may NOT exist.
- If no explanation text exists between the question and the answer,
  output an EMPTY explanation.
- NEVER borrow explanation text from another question.
- NEVER treat common instructions as questions.

OUTPUT RULES:
- Read strictly from TOP to BOTTOM.
- Detect a NEW question ONLY when a line starts with a circled number (①②③…㊿).
- For EACH question, output EXACTLY THREE lines in this order:

  Q: <question text WITHOUT common instructions>
  E: <explanation text or empty>
  A: <O or X>

- If explanation does not exist, output:
  E:

- Preserve Korean text exactly.
- Do NOT add extra text.
- Do NOT return JSON.
- Return plain text only.
"""
    response = openai.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract content."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    )

    return response.choices[0].message.content.strip()

def parse_ocr_text_to_items(ocr_text, page_no):
    """
    OCR 결과 → JSON 변환
    """
    items = []

    # Q: 기준으로 블록 분리
    blocks = re.split(r"\n(?=Q:\s*)", ocr_text.strip())

    for block in blocks:
        q_match = re.search(r"Q:\s*(.+)", block)
        e_match = re.search(r"E:\s*(.*)", block)
        a_match = re.search(r"A:\s*([OX○×])", block)

        if not (q_match and a_match):
            continue

        question_text = q_match.group(1).strip()
        question_text = re.sub(r"^[①-㊿]\s*", "", question_text)

        explanation = e_match.group(1).strip() if e_match else ""

        if explanation.startswith("A:") or explanation in ["O", "X", "○", "×"]:
            explanation = ""

        answer_raw = a_match.group(1)
        answer = "O" if answer_raw in ["O", "○"] else "X"

        items.append({
            "question_text": question_text,
            "explanation": explanation,
            "answer": answer,
            "page": page_no
        })

    return items

def main():
    all_items = []

    for page_no in TARGET_PAGES:
        print(f"\n▶ Page {page_no} 처리 중...")

        image_path = f"{OUTPUT_DIR}/page_{page_no}.png"
        pdf_page_to_image(PDF_PATH, page_no, image_path)

        base64_image = encode_image(image_path)

        # OpenAI 호출
        ocr_text = vision_ocr(base64_image)
        print(ocr_text)

        # json 파일로 저장
        page_items = parse_ocr_text_to_items(ocr_text, page_no)
        all_items.extend(page_items)

        print(f"Page {page_no}: {len(page_items)}문제 추출")

    # 최종 JSON 저장
    output_path = os.path.join(OUTPUT_DIR, "ox_questions.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] 전체 OX 문제 저장 완료 → {output_path}")


if __name__ == "__main__":
    main()
