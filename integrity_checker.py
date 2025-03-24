import os
from pathlib import Path

# Define the list of subjects and exams
subjects = ["물1", "물2", "화1", "화2", "생1", "생2"]
exams = [
    "2014학년도 예비시행", "2014학년도 6월", "2014학년도 9월", "2014학년도 대수능",
    "2015학년도 6월", "2015학년도 9월", "2015학년도 대수능",
    "2016학년도 6월", "2016학년도 9월", "2016학년도 대수능",
    "2017학년도 6월", "2017학년도 9월", "2017학년도 대수능",
    "2018학년도 6월", "2018학년도 9월", "2018학년도 대수능",
    "2019학년도 6월", "2019학년도 9월", "2019학년도 대수능",
    "2020학년도 6월", "2020학년도 9월", "2020학년도 대수능",
    "2021학년도 6월", "2021학년도 9월", "2021학년도 대수능",
    "2022학년도 6월", "2022학년도 9월", "2022학년도 대수능",
    "2023학년도 6월", "2023학년도 9월", "2023학년도 대수능",
    "2024학년도 6월", "2024학년도 9월", "2024학년도 대수능",
    "2025학년도 6월", "2025학년도 9월", "2025학년도 대수능"
]

# Define the base directory
base_dir = Path(r"T:\THedu\KiceDB")

# Function to check the integrity of PDF files
def check_integrity():
    for subject in subjects:
        subject_dir = base_dir / subject
        if not subject_dir.exists():
            print(f"Directory not found: {subject_dir}")
            continue

        expected_files = {f"{exam} {i}번 {subject}_caption.pdf" for exam in exams for i in range(1, 21)}
        actual_files = {file.name for file in subject_dir.glob("*_caption.pdf")}

        missing_files = expected_files - actual_files
        extra_files = actual_files - expected_files

        if missing_files:
            print(f"Missing files in {subject}:")
            for file in sorted(missing_files):
                print(f"  {file}")

        if extra_files:
            print(f"Extra files in {subject}:")
            for file in sorted(extra_files):
                print(f"  {file}")

# Run the integrity check
check_integrity()