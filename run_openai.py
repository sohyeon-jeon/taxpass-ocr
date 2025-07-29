import os
import openai
import base64
from dotenv import load_dotenv

# 1. .env 파일에서 OPENAI_API_KEY 불러오기
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")


# 2. 이미지 base64 인코딩 함수
def encode_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

input_folder = "2024_행정소송법"
# 3. 이미지 경로 및 base64 변환
for f in sorted(os.listdir(input_folder))[40:]:
    # if f not in ['32.png']:
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
                    "- Display math must be wrapped in `$$...$$` or `\\[...\\]` (for arrays, aligned blocks, or long statements).\n"
                    "- Use `\\text{...}` to wrap Korean or label text **only inside array/aligned environments**.\n"
                    "- Do **not** use `\\text{}` in inline choice lists (e.g., ① $\\,$ 70,000,000원) — leave as raw text.\n"
                    "- For label-value formatting, use `\\begin{array}` or `\\begin{aligned}` with appropriate alignment columns (`l`, `r`, etc.).\n"
                    "- For sentences with embedded math symbols (e.g., `\\sim`, `\\triangle`), wrap the full sentence in `$$...$$`, and math segments in `$...$`.\n"
                    "  Example: `$$다음은 제25기(2025.1.1. $\\sim$ 12.31.) 자료이다.$$`\n"
                    "- Do **not** use `array` environments for regular text blocks. Only use them for clearly tabular or numerically aligned content.\n"
                    "- Avoid layout commands like `\\dotfill`, `\\hfill`, `\\flushleft`, etc.\n"
                    "- Do **not** use environments like `enumerate`, `itemize`, `tabular`, `figure`, `algorithm2e`, etc.\n"
                    "- Preserve visible symbols like ①, ②, 가, 나, 다 — do not convert or normalize.\n"
                    "- NEVER repeat `\\,` more than 3 times consecutively. Use `$\\quad$` instead if spacing is needed.\n\n"
                    "- Carefully cross-check all tables against the question text to ensure no referenced years, rows, or columns are missing.\\n"
                    "If any expected data (e.g., a year like '20X4년') is mentioned in the question but not present in the table, you must flag the table as incomplete."


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
                    "  - If answer choices are in tabular form, use JSON format (see below).\n"
                    "\n"
                    "- Wrap **problem number** using `<<problem_num>> ... <</problem_num>>`\n"
                    "\n"
                    "- Wrap **everything between the problem number and the start of the answer choices** using `<<description>> ... <</description>>`\n"
                    "  - Include all conditions, boxed content, explanations, formulas, and tables.\n"
                    "  - If the sentence ends with “다음 중 옳은 것은?” or similar, include it as part of the `<<description>>` block.\n"
                    "  - Do NOT include any part of the answer choices inside this block.\n"
                    "\n"
                    "- Wrap **metadata** (e.g., exam year, subject, issuer — such as '2020. 세무사' or '2009. CPA') using `<<problemInfo>> ... <</problemInfo>>`\n"
                    "  - This is usually found near the top corner or near the title, even in small font.\n"
                    "\n"
                    "Choices Formatting:\n"
                    "- Always wrap answer options inside:\n"
                    "  <<choice>>\n"
                    "  ...choices...\n"
                    "  <</choice>>\n"
                    "\n"
                    "- If the choices are inline (e.g., ① ~ ⑤), format as:\n"
                    "  <<choice>>\n"
                    "  ① $\\,$ 1,000,000원 $\\quad$ ② $\\,$ 2,000,000원 $\\quad$ ③ ...\n"
                    "  <</choice>>\n"
                    "\n"
                    "- If the choices are in **table format** with categories like '상여', '배당', etc., format them as JSON:\n"
                    "  <<choice>>\n"
                    "  {\n"
                    "    \"choices\": [\n"
                    "      { \"number\": \"①\", \"상여\": \"$11,000,000$\", \"배당\": \"$1,000,000$\" },\n"
                    "      { \"number\": \"②\", \"상여\": \"$10,000,000$\", \"배당\": \"$2,000,000$\" }\n"
                    "    ]\n"
                    "  }\n"
                    "  <</choice>>\n"


                    "Do NOT hallucinate or infer missing content. Only transcribe what is clearly shown in the image.\n"
                    "Do NOT include document-level LaTeX commands like `\\documentclass`, `\\usepackage`, or `\\begin{document}`.\n\n"

                    "The entire output must be wrapped inside a LaTeX code block using triple backticks and the `latex` identifier:\n"
                    "```latex\n"
                    "... content ...\n"
                    "```"
                )
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "This image contains tables that may include merged cells.\n"
                            # "Please express those using \\multirow or \\multicolumn where appropriate."
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}",
                        },
                    }
                ],
            },
        ],
        max_tokens=4096,
        temperature=0
    )

    # 결과 출력
    latex_output = response.choices[0].message.content
    print(f, latex_output)

    # 결과 .tex 파일로 저장
    with open(f'{input_folder}.tex', "a", encoding="utf-8") as f:
        f.write(latex_output)
