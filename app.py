import os
import re
import subprocess
import uuid
import shutil
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()
key=os.getenv("KEY")
app = Flask(__name__)
CORS(app)

EXEC_EXT = ".exe" if os.name == "nt" else ""
PYTHON_CMD = "python" if os.name == "nt" else "python3"
BASE_DIR = "jobs"
os.makedirs(BASE_DIR, exist_ok=True)


def validate_code(lang: str, code: str) -> str:
    SYSTEM_CALLS = [ r'\b(system|exec(?:v|vp|ve|le)?|fork|popen)\s*\(' ]
    C_IO_FUNCS = [
        r'\b(fopen|fclose|fread|fwrite|fprintf|fscanf|fgetc|fputc|fgets|fputs|'
        r'remove|unlink|rename|tmpfile|tmpnam|mkdir|rmdir|opendir|readdir|'
        r'chmod|stat)\s*\('
    ]
    C_NET_FUNCS = [
        r'\b(socket|bind|connect|listen|accept|send|recv|recvfrom|sendto|'
        r'getaddrinfo|gethostbyname|gethostname|getpeername)\s*\(',
        r'#\s*include\s*<(sys/socket\.h|netinet/in\.h|arpa/inet\.h)>'
    ]
    CPP_STREAMS = [
        r'\b(std::)?(ifstream|ofstream|fstream)\b',
        r'#\s*include\s*<filesystem>',
        r'std::filesystem::\w+\s*\('
    ]
    JAVA_SYS = [
        r'\bRuntime\.getRuntime\(\)\.',
        r'\bProcessBuilder\b',
        r'System\.load(?:Library)?\s*\('
    ]
    JAVA_IO = [
        r'import\s+java\.(?:io|nio\.file)\b',
        r'new\s+(?:FileInputStream|FileOutputStream|FileReader|FileWriter|'
        r'BufferedReader|BufferedWriter|PrintWriter|RandomAccessFile)\b',
        r'\bFile\.(?:createNewFile|delete|renameTo|mkdirs|listFiles|exists)\s*\(',
        r'\bFiles\.(?:readAllBytes|readAllLines|write|createFile|delete)\s*\(',
        r'\bPaths\.get\s*\('
    ]
    JAVA_NET = [
        r'import\s+java\.net\.(?:Socket|ServerSocket|URL|HttpURLConnection)\b',
        r'new\s+(?:Socket|ServerSocket|URL|HttpURLConnection)\b',
        r'\bInetAddress\b'
    ]
    JS_SYS = [
        r'\beval\s*\(',
        r'\bFunction\s*\(',
        r'\bprocess\.(?:exit|kill)\b',
        r'require\s*\(\s*[\'"](?:child_process|fs)[\'"]\s*\)',
        r'\bexecSync\s*\('
    ]
    JS_FS = [
        r'\bfs\.(?:readFile|readFileSync|writeFile|writeFileSync|'
        r'appendFile|appendFileSync|unlink|unlinkSync|rename|renameSync|'
        r'mkdir|mkdirSync|rmdir|rmdirSync|readdir|readdirSync|open|'
        r'openSync|createReadStream|createWriteStream)\s*\(',
        r'\bfs\.promises\.\w+\s*\('
    ]
    JS_NET = [
        r'require\s*\(\s*[\'"](http|https|net|tls|dgram|dns)[\'"]\s*\)',
        r'\b(?:http|https)\.(?:createServer|get|request)\s*\(',
        r'\bnet\.(?:createServer|connect)\s*\(',
        r'\bdns\.(?:lookup|resolve)\s*\(',
        r'\bdgram\.createSocket\s*\('
    ]
    PY_FILE_MODULES = r'os|sys|shutil|pathlib|io|tempfile|zipfile|tarfile'
    PY_WALK_MODULES = r'glob|fnmatch|fileinput|mmap'
    PY_DYN_MODULES  = r'importlib|runpy|compileall|__import__'
    PY_PKG_MODULES  = r'pip|setuptools|distutils|pkg_resources'
    PY_NET_MODULES  = r'socket|requests|urllib|ftplib|http|xmlrpc|paramiko'
    PY_ALL_MODULES  = '|'.join([
        PY_FILE_MODULES, PY_WALK_MODULES,
        PY_DYN_MODULES, PY_PKG_MODULES, PY_NET_MODULES, 'subprocess'
    ])

    PY_BUILTINS = [
        r'\b(open|compile|exec|eval)\s*\(',
        r'\bos\.environ\b',
        r'\bsubprocess\.(?:run|Popen|call|check_output|check_call|getoutput)\s*\('
    ]
    PY_MODULE_CALLS = [
        r'os\.(?:open|remove|unlink|rename|replace|mkdir|makedirs|rmdir|removedirs|listdir|scandir|chmod|chown)\s*\(',
        r'shutil\.(?:copy2?|move|rmtree|make_archive)\s*\(',
        r'pathlib\.Path\(\s*[\'"]',
        r'io\.(?:FileIO|open)\s*\(',
        r'tempfile\.(?:NamedTemporaryFile|TemporaryFile|mkstemp|mkdtemp)\s*\(',
        r'(?:zipfile|tarfile)\.(?:ZipFile|TarFile|open)\s*\(',
        r'glob\.(?:glob|iglob)\s*\(',
        r'fnmatch\.fnmatch(?:case|filter)?\s*\(',
        r'fileinput\.(?:input|filename|fileno|lineno)\s*\(',
        r'mmap\.mmap\s*\('
    ]

    forbidden_patterns = {
        'Python': [
            rf'import\s+({PY_ALL_MODULES})\b',
            rf'from\s+({PY_ALL_MODULES})\s+import'
        ] + PY_BUILTINS + PY_MODULE_CALLS,

        'C':  SYSTEM_CALLS + C_IO_FUNCS + C_NET_FUNCS,

        'C++': SYSTEM_CALLS + C_IO_FUNCS + C_NET_FUNCS + CPP_STREAMS,

        'Java': SYSTEM_CALLS + JAVA_SYS + JAVA_IO + JAVA_NET,

        'JavaScript': JS_SYS + JS_FS + JS_NET
    }

    patterns = forbidden_patterns.get(lang, [])
    for pattern in patterns:
        if re.search(pattern, code, re.MULTILINE):
            return f"Error: Forbidden function or module usage detected in {lang} code."

    return None

def prepare_file(lang, code, job_id):
    job_dir = os.path.join(BASE_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    supported_langs = ["Python", "C", "C++", "Java", "JavaScript"]
    if lang not in supported_langs:
        return None, "Error: Unsupported language."

    validation_error = validate_code(lang, code)
    if validation_error:
        return None, validation_error

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
    secret_key = data.get('key')
    if secret_key != key:
        return jsonify({'status': 'error', 'message': "Invalid secret key."})
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
    app.run(host="0.0.0.0", port=5000)