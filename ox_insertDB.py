import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

'''
OX 문제가 저장된 json 파일을 불러와 데이터베이스에 저장하는 스크립트입니다.
.json 파일 형식 > 
  {
    "number": "1",
    "question": "조세법률주의는 헌법상 명시된 원칙이다.",
    "answer": "O",
    "category": "조세법의 기본원칙 / 헌법상 조세원칙",
    "explanation": "조세법률주의는 헌법 제59조에 따라 조세의 종목과 세율은 반드시 국회의 법률에 의해 정해져야 하며, 이는 자의적 과세를 방지하고 납세자의 재산권을 보호하기 위한 법치주의적 원칙이다."
  },
'''

# ox 문제가 저장된 json 파일 불러오기
JSON_PATH = 'data/output/행정소송법_ox_questions.json'
SUBJECT_NAME = JSON_PATH.split("/")[-1].replace("_ox_questions.json","")
CREATED_BY_USER_ID = 'admin'
CREATED_BY_IP = '127.0.0.1'

# DB 연결
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)
cur = conn.cursor()

# subject_id 조회 (과목이름으로 과목 id 추출)
cur.execute("SELECT id FROM subjects WHERE name = %s", (SUBJECT_NAME,))
subject_row = cur.fetchone()
if not subject_row:
    raise Exception(f"Subject '{SUBJECT_NAME}' not found in subjects table.")
subject_id = subject_row[0]

with open(JSON_PATH, encoding='utf-8') as f:
    questions = json.load(f)

# INSERT 실행
for q in questions:
    number = q["number"]
    question_text = q["question"]
    answer = True if q["answer"].strip().upper() == "O" else False
    explanation = q.get("explanation", "")
    tag = q.get("category", "").strip().split("/") if q.get("category") else []

    cur.execute("""
        INSERT INTO ox_questions (
            subject_id, number, question_text, answer,
            explanation, tag,
            created_by_ip, created_by_user_id,
            updated_by_ip, updated_by_user_id
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        subject_id, number, question_text, answer,
        explanation, tag,
        CREATED_BY_IP, CREATED_BY_USER_ID,
        CREATED_BY_IP, CREATED_BY_USER_ID
    ))

# 커밋
conn.commit()
cur.close()
conn.close()
print("OX 문제 삽입 완료.")

