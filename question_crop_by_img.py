import os
import numpy as np
import re
import fitz
import cv2
import pytesseract

'''
이미지 기반 PDF에서 문제 번호를 OCR로 인식하고, OpenCV를 이용해 문제 단위로 자동 분할하는 스크립트입니다.
자세한 구현 방식은 블로그에 정리해두었습니다.
링크 : https://choddu.tistory.com/28
'''

# PDF 경로
pdf_path = "법인세법_기본문제.pdf"
output_folder=pdf_path.replace(".pdf","")

# 출력 폴더 생성
os.makedirs(output_folder, exist_ok=True)

# PDF 열기
doc = fitz.open(pdf_path)

# PDF 페이지 로드
for p in range(6, 24):
    page = doc.load_page(p)

    # 페이지를 300dpi 해상도의 이미지(Pixmap)로 변환
    full_pix = page.get_pixmap(dpi=300)

    # Pixmap의 이미지 데이터를 NumPy 배열로 변환
    full_img = np.frombuffer(full_pix.samples, dtype=np.uint8).reshape((full_pix.height, full_pix.width, full_pix.n))

    # RGBA 이미지인 경우 → RGB로 변환
    if full_pix.n == 4:
        full_img = cv2.cvtColor(full_img, cv2.COLOR_RGBA2RGB)

    # 문제번호 인식용 클립 영역
    clip_rect = fitz.Rect(0, 120, 300, 700) if p == 6 else fitz.Rect(0, 50, 300, 700)

    # clip_rect = fitz.Rect(0, 50, 150, 680)
    clip_pix = page.get_pixmap(dpi=300, clip=clip_rect)
    clip_img = np.frombuffer(clip_pix.samples, dtype=np.uint8).reshape((clip_pix.height, clip_pix.width, clip_pix.n))
    if clip_pix.n == 4:
        clip_img = cv2.cvtColor(clip_img, cv2.COLOR_RGBA2RGB)


    # 마젠타 색상 마스킹
    lower_pink = np.array([200, 0, 200])
    upper_pink = np.array([255, 80, 255])
    mask = cv2.inRange(clip_img, lower_pink[::-1], upper_pink[::-1])
    masked_img = cv2.bitwise_and(clip_img, clip_img, mask=mask)

    # 이미지 디버깅
    # cv2.imshow("이미지3", masked_img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    # Threshold 후 OCR
    gray = cv2.cvtColor(masked_img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
    config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
    ocr_data = pytesseract.image_to_data(thresh, config=config, output_type=pytesseract.Output.DICT)
    # print('ocr_data',ocr_data['text'])
    # ocr_data['', '', '', '', '26', '', '27']

    # 인식된 숫자와 상대 y위치
    positions = []
    for i in range(len(ocr_data['text'])):
        word = ocr_data['text'][i]
        if re.fullmatch(r'\d+', word):
            y_clip_px = ocr_data['top'][i]
            number = int(word)
            positions.append({'number': number, 'y_clip_px': y_clip_px})

    # print('positions',positions)
    # positions[{'number': 26, 'y_clip_px': 85}, {'number': 27, 'y_clip_px': 1455}]

    if not positions:
        continue

    # 정렬
    positions.sort(key=lambda x: x['y_clip_px'])

    # 보정 좌표 계산용 정보
    clip_top_pt = clip_rect.y0
    clip_height_pt = clip_rect.y1 - clip_rect.y0
    clip_height_px = clip_img.shape[0]
    full_height_px = full_img.shape[0]
    page_height_pt = page.rect.height

    # 문제별 자르기
    for i, q in enumerate(positions):
        # OCR 상대 y → 절대 y (pt) → full_img px 변환
        y_pt = clip_top_pt + q['y_clip_px'] * clip_height_pt / clip_height_px
        y1 = int(y_pt * full_height_px / page_height_pt)

        if i + 1 < len(positions):
            y_pt_next = clip_top_pt + positions[i + 1]['y_clip_px'] * clip_height_pt / clip_height_px
            y2 = int(y_pt_next * full_height_px / page_height_pt)
        else:
            y2 = full_img.shape[0]

        # 크롭 및 저장
        cropped = full_img[y1-20:y2, :]
        filename = f"{output_folder}/{q['number']:02d}.png"
        cv2.imwrite(filename, cropped)
        print(f"Saved: {filename} ({y1}px ~ {y2}px)")
