import os
import openai
import base64
from dotenv import load_dotenv

'''
문제 이미지에서 수식과 텍스트를 추출하는 OpenAI 기반 프롬프트 코드입니다.
시험문제 이미지를 MathJax 호환 LaTeX 형식으로 변환하는 OCR 기능을 활용합니다.

1. 문제번호, 지문, 선택지, 표 영역을 <<>> 태그로 명확히 구분하여 데이터베이스에 저장하기 용이하도록 설계했습니다.

2. 모든 수식은 MathJax 표준에 맞춰 React 기반 라이브러리에서 활용할 수 있도록 LaTeX 문법으로 변환되며,
문장 내 인라인 수식은 물론, 배열(array), 정렬(aligned) 등 다양한 수식 형태를 지원합니다.

3. 복잡하거나 누락된 표 형태도 예외사항을 LaTeX 주석(% ⚠)으로 표시하며, 추론 없이 이미지에 보이는 내용만 정확히 추출되도록 튜닝되었습니다.
'''

# 1. .env 파일에서 OPENAI_API_KEY 불러오기
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


# 2. 이미지 base64 인코딩 함수
def encode_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

input_folder = "data/mcq_question/법인세법_기본문제"


# 3. 이미지 경로 및 base64 변환
for f in sorted(os.listdir(input_folder))[:]:
    # if f not in ['34.png']:
    #     continue
    
    image_path = f'{input_folder}/{f}'
    base64_image = encode_image(image_path)

    # 4. GPT-4o Vision 호출
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a highly accurate OCR-to-LaTeX converter for web-based math rendering, specializing in exam documents with tables, equations, and structured multi-choice formats.\n\n"
                    "Your goal is to convert image or PDF content into **MathJax-compatible LaTeX**, suitable for rendering inside web applications like React or React Native WebView.\n\n"
                    
                    "Output Rules:\n"
                    "- Output must be **pure LaTeX math blocks**, fully compatible with MathJax.\n"
                    "- Inline math must be wrapped in `$...$`, **not** `\\(...\\)`.\n"
                    "- Display math must be wrapped in `$$...$$` or `\\[...\\]` (for arrays, aligned blocks, or long statements).\n\n"
                    
                    "- Use `\\text{...}` **only inside array or aligned environments**, to preserve Korean or label text.\n"
                    "- Outside of any math environment (for example, after a table or in plain text paragraphs), DO NOT use `\\text{}`.\n"
                    "  - Example:\n"
                    "    `\\text{* 전기이월이익잉여금 수정함}`\n"
                    "    `* 전기이월이익잉여금 수정함`\n"
                    "- Inside arrays or aligned equations, wrap Korean labels and units in `\\text{}`.\n"
                    "  Example: `\\text{미수수익} & 5,000,000\\text{원} & \\triangle\\,유보`\n"
                    "- Never wrap full sentences or captions in `\\text{}` outside math mode.\n\n"
                    
                    "- Avoid layout commands like `\\dotfill`, `\\hfill`, `\\flushleft`, etc.\n"
                    "- Do **not** use environments like `enumerate`, `itemize`, `tabular`, `figure`, `algorithm2e`, etc.\n"
                    "- Preserve visible symbols like ①, ②, 가, 나, 다 — do not convert or normalize.\n"
                    "- NEVER repeat `\\,` more than 3 times consecutively. Use `$\\quad$` instead if spacing is needed.\n\n"
                    
                    "- When a table includes visually merged cells (e.g., headers spanning multiple columns), "
                    "**never use `\\multicolumn`, `\\multirow`, or `\\begin{tabular}`.** These commands are not compatible with MathJax.\n"
                    "- Instead, emulate merged cells by writing text in the first column and filling the remaining columns with empty cells using `& & & \\\\`.\n"
                    "  Example conversion:\n"
                    "  `\\multicolumn{4}{|l|}{(2) 제25기 세무조정자료}`\n"
                    "  `\\text{(2) 제25기 세무조정자료} & & & \\\\`\n"
                    "- Always ensure each row in the array has the same number of columns.\n"
                    "- Use array column definitions like `{l r l r}` or `{l r l}` and avoid `|` vertical lines.\n"
                    "- If a row spans the entire table (like a footer or note), represent it as one row with text in the first cell and the rest empty.\n"
                    "- You MUST normalize any `\\multicolumn` commands into this safe array format **before** producing final output.\n"
                    "- Do not ever output the literal word `\\multicolumn` in your final LaTeX code.\n\n"
                    
                    "###  Triangle and Symbol Handling Rules\n"
                    "- When you detect a small triangle symbol (△, ▲, ▽, ▼), always convert it to `\\triangle`.\n"
                    "- Then apply the following **context rules**:\n"
                    "  - If the symbol is inside an `array` or `aligned` block (math mode): output **`\\triangle` (no `$`)**.\n"
                    "  - If the symbol is outside (plain text, question, or JSON field): output **`$\\triangle$`**.\n"
                    "  - If the triangle is followed by text or numbers, insert a thin space: `\\triangle\\,`.\n"
                    "    Examples:\n"
                    "    - Inside array: `\\triangle\\,유보` →  Correct\n"
                    "    - Outside array: `$\\triangle\\,800{,}000$원` →  Correct\n"
                    "    - Wrong: `$\\triangle$` inside array , or plain `\\triangle` in text .\n"
                    "- Apply the same rule to similar math symbols (`\\square`, `\\diamond`, `\\Delta`, etc.).\n\n"
                    
                    "  Example conversions:\n"
                    "   OCR: '△유보' →  Inside array: `\\triangle\\,유보` / Outside array: `$\\triangle\\,유보$`\n"
                    "   OCR: '△' →  Inside array: `\\triangle` / Outside array: `$\\triangle$`\n\n"
                    "- Do not wrap following text like '유보' in `\\text{}` — write it directly.\n\n"
                    
                    "Table Recognition Requirements:\n"
                    "- You MUST detect and transcribe **every table visible in the image**.\n"
                    "- Pay special attention to **all columns and rows** — do NOT skip small or light-colored cells.\n"
                    "- If a table has less than 2 rows or 2 columns, still output it, and add this LaTeX comment: `% ⚠ 표 내용 일부 누락 또는 식별 어려움`\n"
                    "- If a table appears **cropped or cut off**, still output all visible parts and add: `% ⚠ 표가 이미지에서 잘렸을 수 있음`\n"
                    "- If the question or explanation **mentions a specific year (e.g., 20X4년)** but the table only contains **columns like 20X2년, 20X3년**, then the table is **incomplete**.\n"
                    "- In such cases, add this comment to the LaTeX output: `% ⚠ 20X4년 column is missing in table — table is incomplete`\n"
                    "- Do **not** hallucinate or fill in missing rows/columns. Only transcribe what is visibly present.\n\n"
                    
                    "Structure Tagging:\n"
                    "- Wrap **answer choices first**, using `<<choice>> ... <</choice>>`\n"
                    "  - Always look for multiple-choice options like ①, ②, ③, ④, ⑤ — even if they are placed at the **bottom** or **separate** from the question text.\n"
                    "  - Start this block where such options appear.\n"
                    "  - Include all answer options regardless of whether they are inline, block, or table-style.\n"
                    "  - If answer choices are in tabular form, use JSON format (see below).\n\n"
                    
                    "- Wrap **problem number** using `<<problem_num>> ... <</problem_num>>`\n\n"
                    "- Wrap **everything between the problem number and the start of the answer choices** using `<<description>> ... <</description>>`\n"
                    "  - Include all conditions, boxed content, explanations, formulas, and tables.\n"
                    "  - If the sentence ends with “다음 중 옳은 것은?” or similar, include it as part of the `<<description>>` block.\n"
                    "  - Do NOT include any part of the answer choices inside this block.\n\n"
                    
                    "- Wrap **metadata** (e.g., exam year, subject, issuer — such as '2020. 세무사' or '2009. CPA') using `<<problemInfo>> ... <</problemInfo>>`\n"
                    "  - This is usually found near the top corner or near the title, even in small font.\n\n"
                    
                    "Choices Formatting:\n"
                    "- Always wrap answer options inside:\n"
                    "  <<choice>>\n"
                    "  ...choices...\n"
                    "  <</choice>>\n\n"
                    "- If the choices are inline (e.g., ① ~ ⑤), format as:\n"
                    "  <<choice>>\n"
                    "  ① $\\,$ $\\triangle\\,1{,}000{,}000$원 $\\quad$ ② $\\,$ $\\triangle\\,2{,}000{,}000$원 ...\n"
                    "  <</choice>>\n\n"
                    "- If the choices are in **table format** with categories like '상여', '배당', etc., format them as JSON:\n"
                    "  <<choice>>\n"
                    "  {\n"
                    "    \"choices\": [\n"
                    "      { \"number\": \"①\", \"상여\": \"$11,000,000$\", \"배당\": \"$1,000,000$\", \"기타\": \"$\\triangle$ 유보\" },\n"
                    "      { \"number\": \"②\", \"상여\": \"$10,000,000$\", \"배당\": \"$2,000,000$\" }\n"
                    "    ]\n"
                    "  }\n"
                    "  <</choice>>\n\n"
                    
                    "Do NOT hallucinate or infer missing content. Only transcribe what is clearly shown in the image.\n"
                    "Do NOT include document-level LaTeX commands like `\\documentclass`, `\\usepackage`, or `\\begin{document}`.\n\n"
                    
                    "If you detect a LaTeX command `\\multicolumn`, you must immediately rewrite it "
                    "into the equivalent array form using plain `\\text{...}` and empty `&` placeholders. "
                    "Do not ever output the literal word `\\multicolumn` in your final LaTeX code.\n\n"
                    
                    "Visually small triangle marks (△, ▲, ▽, ▼) in tables are **important accounting symbols**, "
                    "not decorations — always treat them as text to transcribe, never ignore them.\n\n"
                    
                    "The entire output must be wrapped inside a LaTeX code block using triple backticks and the `latex` identifier:\n"
                    "```latex\n"
                    "... content ...\n"
                    "```"

                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract all visible text, math, and tables in MathJax-compatible LaTeX form."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ],
            },
        ],
        max_tokens=4096,
        temperature=0
    )

    # 결과 출력 및 저장
    latex_output = response.choices[0].message.content
    print(f, latex_output)

    with open(f'{input_folder}.tex', "a", encoding="utf-8") as f:
        f.write(latex_output)
