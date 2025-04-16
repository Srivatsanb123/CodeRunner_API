import os
import re
import subprocess
import uuid
import shutil
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

EXEC_EXT = ".exe" if os.name == "nt" else ""
PYTHON_CMD = "python" if os.name == "nt" else "python3"
BASE_DIR = "jobs"
os.makedirs(BASE_DIR, exist_ok=True)

def prepare_file(lang, code, job_id):
    job_dir = os.path.join(BASE_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    if lang == "Python":
        file = os.path.join(job_dir, "program.py")
    elif lang == "C":
        file = os.path.join(job_dir, "program.c")
        compile_cmd = ["gcc", file, "-o", os.path.join(job_dir, f"program{EXEC_EXT}")]
    elif lang == "C++":
        file = os.path.join(job_dir, "program.cpp")
        compile_cmd = ["g++", file, "-o", os.path.join(job_dir, f"program{EXEC_EXT}")]
    elif lang == "Java":
        class_match = re.search(r"(?<=public\sclass\s)\w+", code)
        if not class_match:
            return None, "Error: No public class found in Java code."
        class_name = class_match.group()
        file = os.path.join(job_dir, f"{class_name}.java")
        compile_cmd = ["javac", file]
    elif lang == "JavaScript":
        file = os.path.join(job_dir, "program.js")
    else:
        return None, "Error: Unsupported language."
    
    with open(file, 'w') as f:
        f.write(code)
    
    if lang in ["C", "C++", "Java"]:
        try:
            subprocess.run(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=10)
        except subprocess.CalledProcessError as e:
            return None, e.stderr.decode()
    
    return file, job_dir

def execute_code(lang, file, inp, job_id, job_dir):
    if lang == "Python":
        cmd = [PYTHON_CMD, file]
    elif lang in ["C", "C++"]:
        cmd = [os.path.join(job_dir, f"program{EXEC_EXT}")]
    elif lang == "Java":
        class_name = os.path.splitext(os.path.basename(file))[0]
        cmd = ["java", "-cp", job_dir, class_name]
    elif lang == "JavaScript":
        cmd = ["node", file]
    else:
        return "Error: Unsupported language."
    
    try:
        process = subprocess.run(cmd, input=inp, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        return process.stdout + process.stderr
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out."

def cleanup_files(job_dir):
    shutil.rmtree(job_dir, ignore_errors=True)

@app.route('/', methods=['POST'])
def execute_code_api():
    data = request.get_json()
    code = data.get('code')
    lang = data.get('language')
    inputs = data.get('inputs', [])
    
    job_id = str(uuid.uuid4())
    file, job_dir = prepare_file(lang, code, job_id)
    if file is None:
        return jsonify({'status': 'error', 'message': job_dir})
    
    try:
        outputs = [execute_code(lang, file, inp, job_id, job_dir) for inp in inputs]
    finally:
        cleanup_files(job_dir)
    
    return jsonify({'job_id': job_id, 'status': 'completed', 'outputs': outputs})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)