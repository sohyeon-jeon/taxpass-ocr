import os
import openai
import base64
from dotenv import load_dotenv

'''
세법 OX 문제 이미지에서 문제, 정답(O/X), 해설을 구조적으로 추출하는 OpenAI 코드입니다.

①, ②, ③ 등의 동그라미 숫자를 기준으로 문제를 분리하고,
각 문항에 대해 "theme", "number", "question", "answer", "explanation" 구조의 JSON으로 반환합니다.
'''

# 1. Load API Key
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")



# 2. 이미지 base64 인코딩 함수
def encode_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


# 3. 입력 이미지 폴더
input_folder = "data/ox_question/"

# 4. OCR + 구조화 실행
for f in sorted(os.listdir(input_folder)):
    if f not in ['세법2.png']:  # 필요시 파일명 변경
        continue

    image_path = f"{input_folder}/{f}"
    base64_image = encode_image(image_path)

    # 5. GPT Vision 호출
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise OCR parser specialized in Korean tax-law OX-type exam questions.\n\n"
                    "Your goal is to extract each question, its correct answer (O/X), and explanation "
                    "from a scanned OX exam page.\n\n"
                    "Each question begins with a **circled number (①, ②, ③, ④, ...)** "
                    "and includes Korean text describing a tax law statement. "
                    "The correct mark (O or X) appears near or beside each statement, often in a pink box. "
                    "Sometimes a short pink note or comment provides an explanation for why the answer is correct or wrong.\n\n"

                    "### Extraction Rules:\n"
                    "1. Use the circled numbers (①–⑩) as delimiters to separate questions.\n"
                    "2. Extract exactly:\n"
                    "   - 'theme': the header or topic (e.g., '부가가치세 기초이론', '부가가치세 납세의무')\n"
                    "   - 'number': the circled number as an integer\n"
                    "   - 'question': the full Korean question text following the number\n"
                    "   - 'answer': either 'O' or 'X'\n"
                    "   - 'explanation': the nearby reasoning or comment (usually in pink or underlined)\n"
                    "3. Ignore page numbers, headers like '세법 말문제 OX', and decorative layout elements.\n"
                    "4. Preserve all Korean text as-is — do not translate.\n"
                    "5. Do not invent missing explanations; leave empty if not present.\n"
                    "6. Return data in strict JSON array format, with no commentary.\n\n"

                    "### Example Output:\n"
                    "[\n"
                    "  {\n"
                    "    \"theme\": \"부가가치세 기초이론\",\n"
                    "    \"number\": 1,\n"
                    "    \"question\": \"부가가치세는 특정한 재화와 용역의 소비행위에 대해서 과세하는 소비세에 해당한다.\",\n"
                    "    \"answer\": \"X\",\n"
                    "    \"explanation\": \"부가가치세 → 일반소비세 (모든 재화나 용역의 공급에 과세)\"\n"
                    "  },\n"
                    "  {\n"
                    "    \"theme\": \"부가가치세 납세의무\",\n"
                    "    \"number\": 2,\n"
                    "    \"question\": \"사업자가 부가가치세가 과세되는 재화의 공급시 부가가치세를 거래징수하지 못한 경우에는 부가가치세를 납부할 의무가 없다.\",\n"
                    "    \"answer\": \"X\",\n"
                    "    \"explanation\": \"사업자등록 여부, 거래징수 여부 불문 → 납세의무 있음\"\n"
                    "  }\n"
                    "]"
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all OX-style tax law questions with their answers and explanations as structured JSON data."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                    }
                ],
            },
        ],
        max_tokens=4096,
        temperature=0
    )

    # 6. 결과 저장
    json_output = response.choices[0].message.content
    print(f"\n==== {f} ====\n")
    print(json_output)

    output_path = f"{input_folder}{f.replace('.png', '.json')}"
    with open(output_path, "w", encoding="utf-8") as out:
        out.write(json_output)

    print(f"\n Extracted JSON saved to: {output_path}\n")

