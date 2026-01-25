import os
from pdf2image import convert_from_path
from PIL import Image
import colorsys

# =================================================
# 설정
# =================================================
PDF_PATH = "data/ox_question/2026_세법말문제.pdf"
OUTPUT_DIR = "data/ox_question"
os.makedirs(OUTPUT_DIR, exist_ok=True)

DPI = 300
START_PAGE = 59
END_PAGE = 100

# 왼쪽 영역 (해설 박스가 존재할 수 있는 범위)
LEFT_CHECK_RATIO = (0.0, 0.0, 0.4, 0.95)

# 컬럼 영역 (문제 / 해설 스왑용)
LEFT_COL_RATIO  = (0.12, 0.405)
RIGHT_COL_RATIO = (0.41, 0.91)

# Theme 바 제거 기준 (페이지 높이 대비)
MIN_BOX_HEIGHT_RATIO = 0.06
MIN_BOX_WIDTH_RATIO  = 0.08

# =================================================
# 파란색 판별
# =================================================
def is_blue_pixel(r, g, b):
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return 0.52 <= h <= 0.70 and s >= 0.25 and v >= 0.30

# =================================================
# 해설 박스 여러 개 검출
# =================================================
def detect_answer_box_bboxes(img: Image.Image):
    w, h = img.size
    l = int(w * LEFT_CHECK_RATIO[0])
    t = int(h * LEFT_CHECK_RATIO[1])
    r = int(w * LEFT_CHECK_RATIO[2])
    b = int(h * LEFT_CHECK_RATIO[3])

    pixels = img.load()
    blue_rows = {}

    for y in range(t, b):
        for x in range(l, r):
            r_, g_, b_ = pixels[x, y]
            if is_blue_pixel(r_, g_, b_):
                blue_rows.setdefault(y, []).append(x)

    if not blue_rows:
        return []

    ys = sorted(blue_rows.keys())
    blocks = []
    current = [ys[0], ys[0]]

    for y in ys[1:]:
        if y == current[1] + 1:
            current[1] = y
        else:
            blocks.append(tuple(current))
            current = [y, y]
    blocks.append(tuple(current))

    bboxes = []
    for y_min, y_max in blocks:
        if (y_max - y_min) < h * MIN_BOX_HEIGHT_RATIO:
            continue

        xs = []
        for y in range(y_min, y_max + 1):
            xs.extend(blue_rows[y])

        if not xs:
            continue

        x_min, x_max = min(xs), max(xs)
        if (x_max - x_min) < w * MIN_BOX_WIDTH_RATIO:
            continue

        bboxes.append((x_min, y_min, x_max, y_max))

    return bboxes

# =================================================
# 해설 ↔ 문제 위치 스왑
# =================================================
def rearrange_page_by_answer_boxes(page: Image.Image, answer_bboxes):
    w, h = page.size
    new_page = page.copy()

    left_x1  = int(w * LEFT_COL_RATIO[0])
    left_x2  = int(w * LEFT_COL_RATIO[1])
    right_x1 = int(w * RIGHT_COL_RATIO[0])
    right_x2 = int(w * RIGHT_COL_RATIO[1])

    for (ax1, ay1, ax2, ay2) in answer_bboxes:
        # 해설 박스가 왼쪽에 있을 때만 처리
        center_x = (ax1 + ax2) / 2
        if center_x > w * 0.5:
            continue

        # 같은 y범위 문제 (오른쪽 컬럼 전체)
        print(right_x1, ay1, right_x2, ay2)
        problem_slice = page.crop((right_x1, ay1-10, right_x2, ay2+10))

        problem_slice.save('data/ox_question/2.png')

        # 해설은 "왼쪽 컬럼 전체"를 이동
        answer_slice = page.crop((left_x1, ay1-10, left_x2, ay2+10))

        answer_slice.save('data/ox_question/1.png')

        # # 원래 자리 비우기
        new_page.paste("white", (left_x1, ay1, left_x2, ay2))
        new_page.paste("white", (right_x1, ay1, right_x2, ay2))
        #
        # # 문제 → 왼쪽
        new_page.paste(problem_slice, (left_x1, ay1))
        #
        # # 해설 → 오른쪽
        new_page.paste(answer_slice, (right_x1+550, ay1))

    return new_page


# =================================================
# 메인 실행
# =================================================
def main():
    pages = convert_from_path(
        PDF_PATH,
        dpi=DPI,
        first_page=START_PAGE,
        last_page=END_PAGE
    )

    for idx, page in enumerate(pages):
        page_no = START_PAGE + idx
        page = page.convert("RGB")

        bboxes = detect_answer_box_bboxes(page)

        if not bboxes:
            print(f"Page {page_no}: 해설박스 없음")
            continue

        # 레이아웃 재배치
        fixed_page = rearrange_page_by_answer_boxes(page, bboxes)

        output_path = os.path.join(
            OUTPUT_DIR,
            f"fixed_page_{page_no}.png"
        )
        fixed_page.save(output_path)

        print(f"Page {page_no}: 해설 {len(bboxes)}개 스왑 완료 → 저장")

if __name__ == "__main__":
    main()
