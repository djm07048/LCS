import os
import PyPDF2
import re
from pathlib import Path


def split_pdf_by_exams(subject_name):
    # 시험 리스트
    exam_data = {
        "2014-2020": {
            "exams": ["2014학년도 예비시행", "2014학년도 6월", "2014학년도 9월", "2014학년도 대수능",
                      "2015학년도 6월", "2015학년도 9월", "2015학년도 대수능",
                      "2016학년도 6월", "2016학년도 9월", "2016학년도 대수능",
                      "2017학년도 6월", "2017학년도 9월", "2017학년도 대수능",
                      "2018학년도 6월", "2018학년도 9월", "2018학년도 대수능",
                      "2019학년도 6월", "2019학년도 9월", "2019학년도 대수능",
                      "2020학년도 6월", "2020학년도 9월", "2020학년도 대수능"],
            "source_pdf": fr"2014~2020학년도 6, 9, 수능 문제지_{subject_name}.pdf"
        },
        "2021-2025": {
            "exams": ["2021학년도 6월", "2021학년도 9월", "2021학년도 대수능",
                      "2022학년도 6월", "2022학년도 9월", "2022학년도 대수능",
                      "2023학년도 6월", "2023학년도 9월", "2023학년도 대수능",
                      "2024학년도 6월", "2024학년도 9월", "2024학년도 대수능",
                      "2025학년도 6월", "2025학년도 9월", "2025학년도 대수능"],
            "source_pdf": fr"2021~2025학년도 6, 9, 수능 문제지_{subject_name}.pdf"
        }
    }

    # 경로 설정
    base_dir = fr"T:\Software\LCS\input\{subject_name}"

    # 디렉토리가 없으면 생성
    os.makedirs(base_dir, exist_ok=True)

    # 각 연도 범위에 대해 처리
    for year_range, data in exam_data.items():
        exams = data["exams"]
        source_pdf = data["source_pdf"]
        source_path = os.path.join(base_dir, source_pdf)

        print(f"\n{year_range} 처리 중: {source_pdf}")

        try:
            with open(source_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)

                # 한 시험당 페이지 수
                pages_per_exam = 4

                # 각 시험별로 처리
                for i, exam in enumerate(exams):
                    # 시작 및 종료 페이지 계산
                    start_page = i * pages_per_exam
                    end_page = start_page + pages_per_exam

                    # 페이지 범위 검증
                    if start_page >= total_pages:
                        print(f"경고: {exam}의 시작 페이지({start_page})가 총 페이지 수({total_pages})를 초과합니다.")
                        continue

                    if end_page > total_pages:
                        end_page = total_pages
                        print(f"경고: {exam}의 페이지 범위 조정: {start_page}-{end_page - 1}")

                    # PDF 작성
                    pdf_writer = PyPDF2.PdfWriter()

                    # 페이지 추출
                    for page_num in range(start_page, end_page):
                        pdf_writer.add_page(pdf_reader.pages[page_num])

                    # 파일명 생성
                    year_match = re.search(r'(\d{4})학년도', exam)
                    year = year_match.group(1) if year_match else "Unknown"
                    exam_type = exam.replace(f"{year}학년도", "").strip()

                    output_filename = f"{year}학년도 {exam_type} {subject_name}.pdf"
                    output_path = os.path.join(base_dir, output_filename)

                    # 파일 저장
                    with open(output_path, 'wb') as output_file:
                        pdf_writer.write(output_file)

                    print(f"저장 완료: {output_filename}")

        except FileNotFoundError:
            print(f"오류: 파일을 찾을 수 없습니다 - {source_path}")
        except Exception as e:
            print(f"오류 발생: {str(e)}")


def main():
    subject_name = input("과목명을 입력하세요: ")
    split_pdf_by_exams(subject_name)
    print("\n모든 작업이 완료되었습니다.")


if __name__ == "__main__":
    main()