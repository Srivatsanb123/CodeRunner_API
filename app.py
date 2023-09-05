import os
import re
import subprocess
import uuid
import shutil
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
cors = CORS(app)

job_data = {}

def execute_code(lang, code, inp, job_id):
    output = ""
    file = ""
    job_dir = ""
    if lang == "Python":
        file = f"program_{job_id}.py"
        cmd = ["python", file]
    elif lang == "C":
        file = f"program_{job_id}.c"
        compile_cmd = ["gcc", file, "-o", f"program_{job_id}.o"]
    elif lang == "C++":
        file = f"program_{job_id}.cpp"
        compile_cmd = ["g++", file, "-o", f"program_{job_id}.o"]
    elif lang == "Java":
        job_dir = f"job_{job_id}"
        os.makedirs(job_dir, exist_ok=True)
        
        class_name = re.search(r"(?<=public\sclass\s)\w+(?=\s*\{)", code).group()
        file = os.path.join(job_dir, f"{class_name}.java")

        with open(file, 'w') as f:
            f.write(code)

        compile_cmd = ["javac", file]
    elif lang == "JavaScript":
        file = f"program_{job_id}.js"
        cmd = ["node", file]

    if file:
        with open(file, 'w') as f:
            for line in code.splitlines():
                f.write(line + '\n')
        cleanup_files = [file]
        try:
            if lang in ["C", "C++"]:
                subprocess.run(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=5)
                cleanup_files.extend([f"program_{job_id}.o"])
                process = subprocess.run([f'./program_{job_id}.o'], input=inp, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
                output = process.stdout + process.stderr
            elif lang == "Java":
                subprocess.run(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=5)
                classes = re.findall(r"(?<=class\s)\w+", code)
                cleanup_files.extend([os.path.join(job_dir, f"{cls}.class") for cls in classes])
                process = subprocess.run(["java", "-cp", job_dir, class_name], input=inp, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
                output = process.stdout + process.stderr
            else:
                process = subprocess.run(cmd, input=inp, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         timeout=10)
                output = process.stdout + process.stderr
        except subprocess.CalledProcessError as error:
            output = error.stderr
        except subprocess.TimeoutExpired:
            output = "Error: Code execution timed out (possible infinite loop)."
        finally:
            for file in cleanup_files:
                if os.path.exists(file):
                    os.remove(file)
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir)
    return output

@app.route('/', methods=['POST'])
def execute_code_api():
    if request.method == 'POST':
        data = request.get_json()
        code = data.get('code')
        lang = data.get('language')
        inp = data.get('input')
        job_id = str(uuid.uuid4())
        job_data[job_id] = {'status': 'running', 'output': ''}
        try:
            output = execute_code(lang, code, inp, job_id)
            if isinstance(output, bytes):
                output = output.decode('utf-8')
            job_data[job_id]['status'] = 'completed'
            job_data[job_id]['output'] = output
            response_data = {'job_id': job_id, 'status': 'completed', 'output': output}
            job_data.pop(job_id)
            return jsonify(response_data)
        except Exception as e:
            print(e)
            return jsonify({'status': 'error', 'message': str(e)})

@app.route('/status/<job_id>', methods=['GET'])
def get_job_status(job_id):
    if job_id in job_data:
        return jsonify(job_data[job_id])
    else:
        return jsonify({'status': 'error', 'message': 'Job not found'})

if __name__ == '__main__':
    app.run(debug=True)
