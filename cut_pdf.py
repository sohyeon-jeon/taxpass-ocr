from pypdf import PdfReader, PdfWriter

# 원본 PDF 경로
input_path = "data/ox_question/2026_세법말문제.pdf"
# 새로 만들 PDF 경로
output_path = "output_17_20.pdf"

# 1) PDF 읽기
reader = PdfReader(input_path)
writer = PdfWriter()

start_page = 16
end_page = 20

# 2) 원하는 페이지만 복사
for page_num in range(start_page, end_page):
    if page_num < len(reader.pages):  # 혹시 페이지 수보다 크면 방지
        writer.add_page(reader.pages[page_num])

# 3) 새 PDF로 저장
with open(output_path, "wb") as f:
    writer.write(f)



