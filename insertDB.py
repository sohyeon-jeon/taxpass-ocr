import os
import re
import json
import psycopg2
from dotenv import load_dotenv

'''
이 스크립트는 LaTeX에서 추출된 문제 및 보기 데이터를 JSON 파일로부터 불러와,
PostgreSQL 데이터베이스에 과목, 문제 묶음, 문제, 보기, 정답, 해설 정보를 저장하는 코드입니다.

주요 기능은 다음과 같습니다:
1. `.env` 환경변수로부터 DB 접속 정보를 로드하여 PostgreSQL에 연결합니다.
2. 과목(subjects)과 문제 그룹(problem_groups)을 생성하고 해당 ID를 가져옵니다.
3. 문제 JSON 파일을 순회하며 각 문제의 번호, 설명, 연도, 시험명을 추출하고 `questions` 테이블에 저장합니다.
    - 보기 항목은 text형(①~⑤) 또는 JSON table형으로 판단하여 `choices` 테이블에 각각 다르게 저장합니다.
4. 정답 JSON 파일을 로딩한 뒤, 문제번호 기준으로 `questions` 테이블의 ID를 매핑하여 정답 및 해설을 `answers` 테이블에 저장합니다.
5. 처리 중 오류 발생 시 트랜잭션을 롤백하고, 정상 처리 시 커밋 후 연결을 종료합니다.
'''

# .env 파일 로드
load_dotenv()

# PostgreSQL 연결
conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD")
)

# 기본정보 설정
subject_name = '세법'
problem_group_name = '김문철_법인세법_법인세법총론_기본문제'
question_file = '법인세법_기본문제_수정.json'
answer_file = '법인세법총론_기본문제_답안_parsed.json'
tag = ['법인세법', '법인세법총론']  # PostgreSQL 배열로 들어감

try:
    cur = conn.cursor()

    # 과목 생성
    cur.execute("INSERT INTO subjects(name) VALUES (%s) RETURNING id", (subject_name,))
    subject_id = cur.fetchone()[0]

    # 문제 묶음 생성
    cur.execute("INSERT INTO problem_groups(subjects_id, name) VALUES (%s, %s) RETURNING id",
                (subject_id, problem_group_name))
    problem_group_id = cur.fetchone()[0]

    # 문제 JSON 로딩
    with open(question_file, 'r', encoding='utf-8') as f:
        question_data = json.load(f)

    for item in question_data:
        # description
        description = item.get('description')
        if isinstance(description, list):
            formatted_description = '\n'.join(description)
        else:
            formatted_description = description

        # 시험 연도/종류는 problem_info에서 추출
        raw_info = item.get('problem_info', '')
        exam_year, exam_name = None, None
        match = re.match(r'(\d{4})\.\s*(.*)', raw_info)
        if match:
            exam_year = int(match.group(1))
            exam_name = match.group(2).strip()

        # INSERT questions
        cur.execute("""
            INSERT INTO questions (
                problem_group_id,
                number,
                exam_year,
                exam_name,
                description,
                tag
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            problem_group_id,
            item.get('problem_num'),
            exam_year,
            exam_name,
            formatted_description,
            tag  # PostgreSQL array
        ))
        question_id = cur.fetchone()[0]

        # INSERT 보기 (text형 or table형 판단)
        choices_raw = item.get('choice')

        # table형인지 먼저 검사
        table_data = None
        try:
            # JSON 파싱 시도
            parsed = json.loads(choices_raw)
            if isinstance(parsed, dict) and 'choices' in parsed:
                table_data = parsed['choices']
        except Exception:
            pass

        if table_data:  # table형 보기
            for table_option in table_data:
                cur.execute("""
                           INSERT INTO choices (
                               question_id,
                               choice_index,
                               choice_type,
                               content
                           ) VALUES (%s, %s, %s, %s)
                       """, (
                    question_id,
                    None,  # table형은 인덱스 없음
                    'table',
                    json.dumps(table_option, ensure_ascii=False)
                ))
        else:  # text형 보기
            if isinstance(choices_raw, str):
                options = re.split(r'(?=\s*[①-⑤])', choices_raw.strip())
                for idx, option in enumerate([o.strip() for o in options if o.strip()], start=1):
                    cleaned_option = re.sub(r"^\s*[①-⑤]\s*", "", option).strip()
                    cur.execute("""
                               INSERT INTO choices (
                                   question_id,
                                   choice_index,
                                   choice_type,
                                   content
                               ) VALUES (%s, %s, %s, %s)
                           """, (
                        question_id,
                        idx,
                        'text',
                        cleaned_option
                    ))

    # 문제번호 → question_id 매핑
    cur.execute("SELECT id, number FROM questions WHERE problem_group_id = %s", (problem_group_id,))
    question_map = {row[1]: row[0] for row in cur.fetchall()}

    # 정답 로딩
    with open(answer_file, 'r', encoding='utf-8') as f:
        answer_data = json.load(f)

    for item in answer_data:
        q_num = str(item.get('번호')).strip()
        correct_answer = item.get('정답')
        explanation = item.get('해설')

        if isinstance(explanation, list):
            explanation = '\n'.join(explanation)

        question_id = question_map.get(q_num)
        if question_id and correct_answer:
            cur.execute("""
                INSERT INTO answers (
                    question_id,
                    correct_answer,
                    explanation
                ) VALUES (%s, %s, %s)
            """, (
                question_id,
                correct_answer.strip(),
                explanation
            ))

    conn.commit()
    print("데이터베이스 저장 성공!")

except Exception as e:
    conn.rollback()
    print(f"!!! 에러 발생: {e}")

finally:
    cur.close()
    conn.close()
