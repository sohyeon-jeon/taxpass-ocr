import re
import json

'''
이 스크립트는 LaTeX 형식으로 변환된 시험문제 `.tex` 파일을 불러와,
각 문제의 구성 요소(문제 번호, 설명, 선택지, 문제 정보)를 추출하고,
이를 JSON 형태로 저장하는 전처리 코드입니다.

주요 기능은 다음과 같습니다:
1. ```latex 블록 단위로 문제를 분리한 뒤,
2. 각 블록에서 <<problem_num>>, <<description>>, <<choice>>, <<problemInfo>> 등의 태그를 추출합니다.
3. 수식(`$...$`, `$$...$$`, `\begin{array}...\end{array}`) 외 일반 텍스트에서만 백슬래시(`\`)를 제거하여 React에서 수식 렌더링 시 오류를 방지합니다.
4. 모든 정보가 갖춰진 문제는 `output.json`에 저장하고, 필수 항목이 누락된 블록은 `exception.json`에 따로 기록하여 검토할 수 있도록 합니다.

이 스크립트는 MathJax 기반 수식 렌더링과 데이터베이스 저장을 위한 구조화된 문제 데이터를 생성하는 데 유용합니다.
'''

# 수식 영역($...$, $$...$$, \begin{array}...\end{array})을 보호하면서 그 외 텍스트의 백슬래시(\)만 제거하는 함수
def remove_backslash_outside_math(text):
    # 보호할 블록: $$...$$, $...$, \begin{array}...\end{array}
    pattern = re.compile(
        r'(\\begin\{array\}.*?\\end\{array\}|\${1,2}.*?\${1,2})',
        re.DOTALL
    )

    parts = pattern.split(text)

    result = []
    for part in parts:
        if re.match(r'(\\begin\{array\}.*?\\end\{array\}|\${1,2}.*?\${1,2})', part, re.DOTALL):
            result.append(part)  # 보호 구간은 그대로 유지
        else:
            result.append(part.replace("\\", ""))  # 나머지 구간의 \ 제거
    return ''.join(result)


input_file="2024_행정소송법.tex"
output_file=input_file.replace(".tex","")

with open(input_file, 'r', encoding='utf-8') as f:
    content = f.read()

# latex 블록 단위로 분리 + 공백 제거
blocks = [b.strip() for b in content.split('```latex') if b.strip()]

# 결과 저장용 리스트
result_list = []
exception_list = []

# 태그 추출 함수
def extract_tag(text, tag):
    pattern = fr'<<{tag}>>\s*(.*?)\s*<</{tag}>>'
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1).strip() if match else None

# 각 블록 처리
for i, block in enumerate(blocks):
    # problem_info는 있을 수도 없음
    raw_info = extract_tag(block, 'problemInfo')
    problem_info = raw_info.replace("• ", "") if raw_info else None
    # problem_info = "2024. 세무사"
    problem_num = extract_tag(block, 'problem_num')
    if problem_num:
        problem_num = problem_num.replace(".", "")

    raw_description = extract_tag(block, 'description')
    description = extract_tag(block, 'description')
    raw_choice = extract_tag(block, 'choice')
    choice = remove_backslash_outside_math(raw_choice) if raw_choice else None

    # 필수 요소 누락 시 예외 처리
    if not (problem_num and description and choice):
        exception_list.append({
            'index': i+1,
            'block': block
        })
        continue

    # 정상 데이터 저장
    result = {
        'problem_num': problem_num,
        'description': description,
        'choice': choice,

    }
    if problem_info:  # 있을 때만 포함
        result['problem_info'] = problem_info

    result_list.append(result)

# JSON 저장
with open(f'{output_file}.json', 'w', encoding='utf-8') as f:
    json.dump(result_list, f, ensure_ascii=False, indent=2)

with open(f'{output_file}_exception.json', 'a', encoding='utf-8') as f:
    json.dump(exception_list, f, ensure_ascii=False, indent=2)

print(f"저장 완료: {len(result_list)}개 문제")
print(f"예외 처리된 항목: {len(exception_list)}개 → exceptions.json에서 확인")
