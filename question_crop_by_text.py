import os
import numpy as np
import re
import fitz
import statistics
import cv2

'''
텍스트 기반 PDF 시험지에서 문제 번호(예: 1., 2., 3.)를 기준으로
각 문제 영역을 자동으로 인식하고 이미지로 분할합니다.
PyMuPDF를 사용해 텍스트 위치를 추출하고,
OpenCV를 이용해 해당 영역을 잘라 이미지로 저장합니다.
자세한 구현 방식은 블로그에 정리해두었습니다.
링크 : https://choddu.tistory.com/27
'''

# PDF 열기
pdf_path = "2025_재정학.pdf"
doc = fitz.open(pdf_path)
output_folder=pdf_path.replace(".pdf","")
os.makedirs(output_folder, exist_ok=True)

total_pages = len(doc)
# 문제번호를 찾기 위한 숫자 패턴
# 1~2자리 숫자((ex_1,22)로이고 마침표
# ex_ 1. 22.
pattern = re.compile(r'^(\d{1,2})\.')

# 1. 전체 문제번호 후보 모으기
all_question_candidates = []

for p in range(total_pages):
    page = doc.load_page(p)
    # get_text : 페이지에서 텍스트를 볼록 단위로 추출
    blocks = page.get_text("blocks")
    # (x0, y0, x1, y1, text, block_no, block_type, block_flags)
    for block in blocks:
        x0, y0, x1, y1, text, *_ = block
        for line in text.strip().splitlines():
            line = line.strip()
            match = pattern.match(line)
            if match:
                # "01","02","12"... 두자리 문자열로 반환
                number = match.group(1).zfill(2)
                all_question_candidates.append({
                    'page': p + 1,
                    'number': number,
                    'x': x0,
                    'y': y0
                })
                break

for item in all_question_candidates:
    print(item)

# 2. 평균 좌표 기반 필터링으로 문제번호 후보 중 이상치 제거
# 대부분의 실제 문제번호("숫자.")는 페이지 왼쪽 상단에 위치하므로 x좌표가 비슷함
# 반면, 본문 중간에 등장하는 "숫자."는 x좌표가 비슷하지 않음
# 따라서 모든 후보의 x좌표 평균을 구한 뒤, 평균 ±10 정도를 허용하여 문제번호만 필터링함
# 이를 해결하기 위해, 잘못 인식된 숫자를 제거하고 실제 문제번호만 필터링함
x_list = [q['x'] for q in all_question_candidates]
if x_list:
    mean_x = statistics.mean(x_list)
    lower, upper = mean_x - 15, mean_x + 15
else:
    mean_x = 0
    lower, upper = -1, -1

print(f"\n 전체 문제번호 평균 x = {mean_x:.2f}, 허용 범위 = [{lower:.2f}, {upper:.2f}]")

# 3. 페이지별로 필터링 후 crop
for p in range(1, total_pages + 1):
    question_numbers = [q for q in all_question_candidates if q['page'] == p and lower <= q['x'] <= upper]
    question_numbers.sort(key=lambda q: q['y'])  # y좌표 순으로 정렬

    if not question_numbers:
        continue

    # 3-1. 페이지 이미지 렌더링
    page = doc.load_page(p - 1)
    page_height = page.rect.height
    pix = page.get_pixmap(dpi=300)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)

    # 이미지 높이는 픽셀 단위이고, pdf 좌표는 점 단위
    # scale_y : 변환 비율 계산
    img_height = img.shape[0]
    scale_y = img_height / page_height

    # 3-2. 문제 단위로 crop
    for i, q in enumerate(question_numbers):
        # 각 문제의 y1부터 다음 문제 y2까지의 이미지를 잘라냄
        y1 = int(q['y'] * scale_y)
        y2 = int(question_numbers[i + 1]['y'] * scale_y) if i + 1 < len(question_numbers) else img_height
        cropped = img[y1:y2, :]

        filename = f"{q['number']}.png"
        cv2.imwrite(os.path.join(output_folder, filename), cropped, [cv2.IMWRITE_PNG_COMPRESSION, 0])
        print(f"Saved: {output_folder}/{filename} / p{str(p).zfill(2)} ({y1}px ~ {y2}px)")
