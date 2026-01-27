import os
import shutil

from pdf2image import convert_from_path
from PIL import Image, ImageDraw
import colorsys

"""
세법 OX 문제 PDF를 OCR 처리하기 전에,
문제, 해설, 정답(O/X)의 시각적 구조를 통일하기 위한 전처리 파이프라인입니다.(목적: OCR 정확도 향상)

왼쪽의 파란색 해설 박스를 기준으로 문제 영역과 해설 영역을 검출한 뒤,
해설 박스 내부 구성([O/X | 번호 | 해설])을
형태([해설 | 번호 | O/X])로 재배치합니다.

또한 좌·우 컬럼에 분산된 문제와 해설을
동일한 방향과 순서로 정렬하여 OCR 인식의 일관성을 높이는 것이 목표입니다.
"""

# =================================================
# 설정
# =================================================
PDF_PATH = "data/ox_question/2026_세법말문제.pdf"
BASE_DIR = "data/ox_question"
# 임시 폴더 생성
TEMP_DIR = os.path.join(BASE_DIR, "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

DPI = 300
START_PAGE = 62
END_PAGE = 63

# 왼쪽 영역 (해설 박스가 존재할 수 있는 범위)
LEFT_CHECK_RATIO = (0.0, 0.0, 0.4, 0.95)

# 컬럼 영역 (문제 / 해설 스왑용)
LEFT_COL_RATIO = (0.12, 0.405)
RIGHT_COL_RATIO = (0.41, 0.91)

# Theme 바 제거 기준 (페이지 높이 대비)
MIN_BOX_HEIGHT_RATIO = 0.06
MIN_BOX_WIDTH_RATIO = 0.08

def is_blue_pixel(r, g, b):
    """
    추출할 파란색 색 범위 지정
    """
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return 0.52 <= h <= 0.70 and s >= 0.25 and v >= 0.30


def save_debug_answer_boxes(page: Image.Image, bboxes, page_no):
    """
    파란색 박스 디버그용 시각화(빨간색)
    """
    debug_img = page.copy()
    draw = ImageDraw.Draw(debug_img)

    for (x1, y1, x2, y2) in bboxes:
        draw.rectangle(
            [(x1, y1), (x2, y2)],
            outline="red",
            width=6
        )

    path = os.path.join(
        TEMP_DIR,
        f"debug_answer_boxes_page_{page_no}.png"
    )
    debug_img.save(path)
    print(f"[DEBUG] 해설 박스 검출 결과 저장 → {path}")


def detect_answer_box_bboxes(img: Image.Image):
    """
    파란색 해설 박스 검출 함수

    - 한 페이지에 여러개의 해설 박스가 존재할 수 있음
    - 좌측 영역(LEFT_CHECK_RATIO)을 탐색하여 파란색 계열 픽셀(is_blue_pixel)을 검출
    - 검출된 픽셀의 y좌표를 기반으로 연속 영역을 그룹화하여
      해설 박스 후보 영역(bounding box)을 생성한다
    - 일정 크기 이하의 영역은 노이즈로 판단하여 제외한다
    """
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


def draw_three_regions_in_box(draw: ImageDraw.ImageDraw, bbox):
    """
    해설 박스(bbox)를 가로 방향으로 3개 영역(O/X, 문제번호, 해설)으로 분할하여
    시각적으로 표시하는 디버그용 함수.

    - 빨간색 테두리: 해설 박스 전체 영역
    - 파란색 선: O/X 영역과 문제번호 영역의 경계
    - 초록색 선: 문제번호 영역과 해설 영역의 경계
    """

    x1, y1, x2, y2 = bbox
    bw = x2 - x1

    # 세로 분할 비율
    ox_ratio = 0.10  # O / X
    number_ratio = 0.14  # 번호

    x_ox_end = x1 + int(bw * ox_ratio)
    x_number_end = x_ox_end + int(bw * number_ratio)

    # 빨간색 박스 전체
    draw.rectangle(
        [(x1, y1), (x2, y2)],
        outline="red",
        width=5
    )

    # 파란색 OX | 번호
    draw.line(
        [(x_ox_end, y1), (x_ox_end, y2)],
        fill="blue",
        width=4
    )

    # 초록색 번호 | 해설
    draw.line(
        [(x_number_end, y1), (x_number_end, y2)],
        fill="green",
        width=4
    )


def reorder_answer_box_inside(page: Image.Image, bbox):
    """
    해설 박스 내부의 가로 구성 요소를 재배치하는 함수.

    기존 구조:
    [ O / X | 문제번호 | 해설 ]

    재배치 후 구조:
    [ 해설 | 문제번호 | O / X ]

    - draw_three_regions_in_box에서 시각화한 분할 비율을 기준으로 영역을 분리
    - OCR 정확도와 레이아웃 통일성을 높이기 위해 해설 박스 내부를 재배치
    """
    x1, y1, x2, y2 = bbox
    box = page.crop((x1, y1, x2, y2))
    bw, bh = box.size

    # 세로 분할 비율
    ox_ratio = 0.10
    number_ratio = 0.13

    ox_w = int(bw * ox_ratio)
    number_w = int(bw * number_ratio)

    # 기존 구조에서 영역 분리
    part_ox = box.crop((10, 0, ox_w + 20, bh))
    part_number = box.crop((ox_w, 0, ox_w + number_w, bh))
    part_explain = box.crop((ox_w + number_w, 0, bw, bh))

    # 새 박스 생성
    new_box = Image.new("RGB", (bw, bh), "white")

    x = 0
    # 해설
    new_box.paste(part_explain, (x, 0))
    x += part_explain.width

    # 숫자
    new_box.paste(part_number, (x, 0))
    x += part_number.width

    # O / X
    new_box.paste(part_ox, (x, 0))

    # 원래 페이지에 덮어쓰기
    page.paste(new_box, (x1, y1))


def save_debug_after_reorder(page: Image.Image, bboxes, page_no):
    """
    재배치 이후에도 기존 빨간 박스 영역이 유지되는지 확인용
    """
    debug_img = page.copy()
    draw = ImageDraw.Draw(debug_img)

    for (x1, y1, x2, y2) in bboxes:
        # 기존 박스
        draw.rectangle(
            [(x1, y1), (x2, y2)],
            outline="red",
            width=6
        )

    out_path = os.path.join(
        TEMP_DIR,
        f"debug_after_reorder_boxes_page_{page_no}.png"
    )
    debug_img.save(out_path)
    print(f"[DEBUG] 재배치 후 박스 영역 확인 → {out_path}")


def rearrange_page_by_answer_boxes(page: Image.Image, answer_bboxes):
    """
    OCR 정확도를 높이기 위해,
    문제와 해설이 페이지 상에서 항상 동일한 방향과 순서를 갖도록
    시각적 구조를 재배치하는 전처리 단계
    """

    w, h = page.size
    new_page = page.copy()

    left_x1 = int(w * LEFT_COL_RATIO[0])
    left_x2 = int(w * LEFT_COL_RATIO[1])
    right_x1 = int(w * RIGHT_COL_RATIO[0])
    right_x2 = int(w * RIGHT_COL_RATIO[1])

    for (ax1, ay1, ax2, ay2) in answer_bboxes:
        # 해설 박스가 왼쪽에 있을 때만 처리
        center_x = (ax1 + ax2) / 2
        if center_x > w * 0.5:
            continue

        # 같은 y범위 문제 (오른쪽 컬럼 전체)
        print(right_x1, ay1, right_x2, ay2)
        problem_slice = page.crop((right_x1, ay1 - 10, right_x2, ay2 + 10))

        # 해설은 "왼쪽 컬럼 전체"를 이동
        answer_slice = page.crop((left_x1, ay1 - 10, left_x2, ay2 + 10))

        # # 원래 자리 비우기
        new_page.paste("white", (left_x1, ay1, left_x2, ay2))
        new_page.paste("white", (right_x1, ay1, right_x2, ay2))
        #
        # # 문제 → 왼쪽
        new_page.paste(problem_slice, (left_x1, ay1))
        #
        # # 해설 → 오른쪽
        new_page.paste(answer_slice, (right_x1 + 550, ay1))

    return new_page


def build_final_pdf(
        pdf_path,
        TEMP_DIR,
        start_page,
        end_page,
        dpi=300,
        output_pdf_name="final_ox_questions.pdf"
):
    """
    OCR 전처리를 위해 재배치된 페이지 이미지를 우선 사용하여
    최종 OX 문제용 PDF를 생성하는 함수
    """
    print("[START] 최종 PDF 생성 중...")

    # 원본 PDF 전체를 이미지로 변환
    original_pages = convert_from_path(
        pdf_path,
        dpi=dpi,
        first_page=start_page,
        last_page=end_page
    )

    final_images = []

    for idx, original_img in enumerate(original_pages):
        page_no = start_page + idx
        fixed_img_path = os.path.join(
            TEMP_DIR,
            f"fixed_page_{page_no}.png"
        )

        if os.path.exists(fixed_img_path):
            print(f"✔ Page {page_no}: 수정본 사용")
            img = Image.open(fixed_img_path).convert("RGB")
        else:
            print(f"• Page {page_no}: 원본 사용")
            img = original_img.convert("RGB")

        final_images.append(img)

    # PDF로 저장
    output_pdf_path = os.path.join(BASE_DIR, output_pdf_name)

    final_images[0].save(
        output_pdf_path,
        save_all=True,
        append_images=final_images[1:]
    )

    print(f"[DONE] 최종 PDF 생성 완료 → {output_pdf_path}")


def cleanup_temp_dir(temp_dir):
    """
        OCR 전처리 과정에서 생성된 임시 폴더 삭제
        """
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        print(f"[CLEANUP] temp 폴더 삭제 완료 → {temp_dir}")


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

        # 디버그 이미지 저장
        save_debug_answer_boxes(page, bboxes, page_no)

        debug_img = page.copy()
        draw = ImageDraw.Draw(debug_img)

        for bbox in bboxes:
            draw_three_regions_in_box(draw, bbox)

        out_path = os.path.join(
            TEMP_DIR,
            f"debug_three_regions_page_{page_no}.png"
        )
        debug_img.save(out_path)

        print(f"[DEBUG] 개별 박스 내부 분할 시각화 저장 → {out_path}")

        for bbox in bboxes:
            reorder_answer_box_inside(page, bbox)

        out_path = os.path.join(
            TEMP_DIR,
            f"reordered_page_{page_no}.png"
        )
        page.save(out_path)
        print(out_path)

        print(f"[OK] Page {page_no}: 해설→숫자→정답 순서 재배치 완료")

        save_debug_after_reorder(page, bboxes, page_no)

        # 재배치
        fixed_page = rearrange_page_by_answer_boxes(page, bboxes)

        out_path = os.path.join(
            TEMP_DIR,
            f"fixed_page_{page_no}.png"
        )
        fixed_page.save(out_path)

        print(f"Page {page_no}: 처리 완료 → {out_path}")

    build_final_pdf(
        pdf_path=PDF_PATH,
        TEMP_DIR=TEMP_DIR,
        start_page=START_PAGE,
        end_page=END_PAGE,
        dpi=DPI,
        output_pdf_name="2026_세법_말문제_OX_정리본.pdf"
    )

    # temp 정리
    cleanup_temp_dir(TEMP_DIR)


if __name__ == "__main__":
    main()
