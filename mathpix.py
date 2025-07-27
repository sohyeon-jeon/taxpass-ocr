import os
import requests
import json
from dotenv import load_dotenv

'''
Mathpix는 이미지나 PDF에서 수식, 텍스트, 표 등을 추출해주는 OCR API 입니다.
이 코드는 Mathpix API를 이용하여 
텍스트와 수식이 섞인 이미지로부터
일반 텍스트와 LaTeX 형식으로 변환해주는 기능을 수행합니다.
블로그에 관련 내용 정리해두었습니다.
링크 : https://choddu.tistory.com/29
'''
load_dotenv()

r = requests.post("https://api.mathpix.com/v3/text",
    files={"file": open("2025_재정학/26.png", "rb")},
                  data={
                      "options_json": json.dumps({
                          "math_inline_delimiters": ["$", "$"],
                          "rm_spaces": True,
                          "include_line_data": True,
                          "formats": ["latex_styled", "text"]
                      })
                  },
    headers={
        "app_id": os.getenv("MATHPIX_APP_ID"),
        "app_key": os.getenv("MATHPIX_APP_KEY"),
    }
)
# Mathpix 응답 JSON 저장
output_path = "result.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(r.json(), f, ensure_ascii=False, indent=4)

print(f" Mathpix 결과 저장 완료: {output_path}")
