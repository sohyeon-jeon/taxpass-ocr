import os
import json
import psycopg2
from dotenv import load_dotenv

"""
OX 문제(JSON) → ox_questions 테이블 적재 스크립트

- 입력: parse_data/output/*.json
- 대상 테이블: ox_questions
- PK: (subject_id, main_theme, theme, question_no)
"""

# --------------------
# db 연결
# --------------------
load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

conn.autocommit = False
cur = conn.cursor()

# --------------------
# 과목 정보
# --------------------
SUBJECT_ID = 2                 # 세법학개론 ID
MAIN_THEME = "부가가치세법 총론"   # 상위 분류
CREATED_BY_USER = "system"

# --------------------
# JSON 로드
# --------------------
with open("parse_data/output/부가가치세법 총론.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# --------------------
# INSERT SQL
# --------------------
insert_sql = """
INSERT INTO ox_questions (
    subject_id,
    main_theme,
    theme,
    question_no,
    question_title,
    question_text,
    answer,
    explanation,
    created_by_user_id
)
VALUES (
    %(subject_id)s,
    %(main_theme)s,
    %(theme)s,
    %(question_no)s,
    %(question_title)s,
    %(question_text)s,
    %(answer)s,
    %(explanation)s,
    %(created_by_user_id)s
)
ON CONFLICT (subject_id, main_theme, theme, question_no)
DO NOTHING;
"""

# --------------------
# 데이터 적재
# --------------------
try:
    for block in data:
        theme = block["theme"].strip()
        question_title = block["question_title"].strip()

        for item in block["items"]:
            params = {
                "subject_id": SUBJECT_ID,
                "main_theme": MAIN_THEME,
                "theme": theme,
                "question_no": str(item["index"]),
                "question_title": question_title,
                "question_text": item["raw_text"].strip(),
                "answer": True if item["answer"] == "O" else False,
                "explanation": item.get("explanation", "").strip(),
                "created_by_user_id": CREATED_BY_USER
            }

            cur.execute(insert_sql, params)

    conn.commit()
    print("OX 문제 데이터 INSERT 완료")

except Exception as e:
    conn.rollback()
    print("INSERT 실패:", e)

finally:
    cur.close()
    conn.close()
