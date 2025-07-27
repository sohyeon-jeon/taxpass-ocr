import re
import json
from pykospacing import Spacing

'''
이 코드는 OCR 결과(mathpix API 이용)에서 줄바꿈으로 인해 잘못 붙은 단어들을 PyKoSpacing으로 교정하는 로직입니다.
각 줄의 마지막 단어와 다음 줄의 첫 단어를 붙여 띄어쓰기 보정을 수행하고, 교정 결과를 원문에 반영합니다.
줄 단위 후처리를 통해 한국어 문장을 더 자연스럽게 정제할 수 있습니다.
링크 : https://choddu.tistory.com/26
위 링크에 자세한 내용 정리해두었습니다. 

'''

spacing = Spacing()

def apply_spacing_exclude_math(text):
    # 수식 부분 임시 치환
    math_patterns = re.findall(r'\$.*?\$', text)
    for i, formula in enumerate(math_patterns):
        text = text.replace(formula, f"<<MATH_{i}>>")

    # 한글 문장에만 spacing 적용
    def spacing_korean(match):
        return spacing(match.group())

    spaced = re.sub(r'[가-힣\s\,\.]+', spacing_korean, text)

    # 수식 복원
    for i, formula in enumerate(math_patterns):
        spaced = spaced.replace(f"<<MATH_{i}>>", formula)

    return spaced

def extract_text_list(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [line['text'] for line in data.get('line_data', []) if 'text' in line]

def get_spacing_corrections(lines):
    corrections = []

    for i in range(len(lines) - 1):
        curr_line = lines[i].strip()
        next_line = lines[i + 1].strip()

        if not next_line:
            continue

        curr_tokens = curr_line.split()
        next_tokens = next_line.split()

        last_token = curr_tokens[-1] if curr_tokens else None
        first_token = next_tokens[0] if next_tokens else None

        if last_token and first_token:
            joined = last_token + first_token
            spaced_result = apply_spacing_exclude_math(joined)

            if spaced_result != joined:
                corrections.append({
                    "joined": joined,
                    "spaced": spaced_result
                })

    return corrections  #  빠진 부분

def smart_lstrip_preserve_newlines(texts):
    cleaned = []
    for text in texts:
        lines = text.split('\n')
        stripped_lines = [line.lstrip() for line in lines]
        cleaned_text = '\n'.join(stripped_lines)
        cleaned.append(cleaned_text)
    return ''.join(cleaned)

# 실행 
texts = extract_text_list('mathpix_result.json')
print('texts',texts)
full_text = smart_lstrip_preserve_newlines(texts)
print(full_text)

corrections = get_spacing_corrections(texts)
print('corrections', corrections)

# 교정된 텍스트 생성
for c in corrections:
    if c["joined"] in full_text:
        print(f" 교체: {c['joined']} → {c['spaced']}")
        full_text = full_text.replace(c["joined"], c["spaced"])

# 최종 결과 출력
print("\n 최종 교정된 텍스트:")
print(full_text)

# 파일로 저장
output_path = "fullText.txt"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(full_text)

print(f"\n 파일 저장 완료: {output_path}")