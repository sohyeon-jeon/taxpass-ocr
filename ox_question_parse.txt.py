import os
import json
import re
from pathlib import Path

'''
텍스트 파일을 JSON으로 변환하여 DB 저장를 쉽게 해주는 스크립트입니다.

.txt 파일 > 
1. 회계등식은 자산 = 부채 + 자본이다.
정답: O
세부 카테고리: 회계 기본원리 / 회계등식
해설: 회계의 기본 구조는 자산은 부채와 자본의 합이라는 등식으로 표현되며, 이는 재무상태표 작성의 기초가 되는 가장 기본적인 원리이다.

.json 파일 > 
  {
    "number": "1",
    "question": "회계등식은 자산 = 부채 + 자본이다.",
    "answer": "O",
    "category": "회계 기본원리 / 회계등식",
    "explanation": "회계의 기본 구조는 자산은 부채와 자본의 합이라는 등식으로 표현되며, 이는 재무상태표 작성의 기초가 되는 가장 기본적인 원리이다."
  },

'''
def parse_ox_txt_file(file_path):
    with open(file_path, encoding='utf-8') as f:
        text = f.read()

    blocks = re.split(r'\n(?=\d+\.\s)', text.strip())
    results = []

    for block in blocks:
        m1 = re.match(r'(\d+)\.\s*(.+?)\n정답:\s*(O|X)', block)
        if not m1:
            continue

        number = str(m1.group(1))
        question = m1.group(2).strip()
        answer = m1.group(3).strip()

        cat_match = re.search(r'세부 카테고리:\s*(.+)', block)
        category = cat_match.group(1).strip() if cat_match else ""

        expl_match = re.search(r'해설:\s*(.+)', block, re.DOTALL)
        explanation = expl_match.group(1).strip() if expl_match else ""

        results.append({
            "number": number,
            "question": question,
            "answer": answer,
            "category": category,
            "explanation": explanation
        })

    return results


# 실행
file_path = "data/ox_question/회계학개론.txt"
parsed = parse_ox_txt_file(file_path)
subject = Path(file_path).stem

# 저장 디렉토리 생성
os.makedirs("data/output", exist_ok=True)

with open(f"data/output/{subject}_ox_questions.json", "w", encoding='utf-8') as f:
    json.dump(parsed, f, ensure_ascii=False, indent=2)

print("JSON 저장 완료:", f"{subject}_ox_questions.json")
