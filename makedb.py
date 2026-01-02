import os
import subprocess

# 실행할 db.py 경로 목록
r_path = "static/data/"
db_files = [
    f"{r_path}chatbot1/db.py",
    f"{r_path}chatbot2/db.py",
    f"{r_path}chatbot3/db.py",
    f"{r_path}chatbot4/db.py",
]

# 프로젝트 루트 기준 실행
project_root = os.path.dirname(os.path.abspath(__file__))
print(f"프로젝트 루트: {project_root}")
for db_file in db_files:
    full_path = os.path.join(project_root, db_file)
    if os.path.exists(full_path):
        print(f"🚀 실행 중: {db_file}")
        subprocess.run(["python", full_path])
    else:
        print(f"⚠️ 파일 없음: {db_file}")