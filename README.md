# CodeRunner API

The **CodeRunner API** is a Flask-based web service that allows users to execute code in various programming languages. This API is designed to compile and run code snippets provided by users and return the output or error messages. It supports languages like Python, C, C++, JavaScript, and Java.

## Table of Contents

- [Usage](#usage)
  - [Endpoints](#endpoints)
  - [Request Format](#request-format)
  - [Response Format](#response-format)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage Example](#usage-example)

## Usage

### Endpoints

- **Execute Code:** Submit code for execution.
  - **Endpoint:** `/`
  - **HTTP Method:** POST
  - **Input Data:** JSON payload with the following fields:
    - `code`: The code snippet to execute.
    - `language`: The programming language (e.g., "Python", "C", "JavaScript").
    - `input`: The input data for the code (if required).

- **Get Job Status:** Check the status of a code execution job.
  - **Endpoint:** `/status/<job_id>`
  - **HTTP Method:** GET
  - **Path Parameter:** `job_id` (The unique ID of the job to check).

### Request Format

To execute code, send a POST request to the `/` endpoint with a JSON payload:

```json
{
  "code": "Your code snippet here",
  "language": "Python",
  "input": "Input data (if required)"
}
```

### Response Format

The API will respond with JSON data containing the job status and output:

```json
{
  "job_id": "Unique Job ID",
  "status": "Job Status",
  "output": "Execution Output or Error Messages"
}
```

## Getting Started

### Prerequisites

- Python 3.x
- Flask
- Flask-CORS

### Installation

Clone the repository:

```shell
git clone https://github.com/Srivatsanb123/CodeRunner_API.git
```

Run the Flask application:

```shell
python app.py
```
The API should now be running locally on http://localhost:5000.

## Usage Example
Here's an example of how to use the CodeRunner API in Python:

```python
import requests

api_url = "http://localhost:5000"

# Example code snippet
code = """
print("Hello, World!")
"""

data = {
    "code": code,
    "language": "Python",
    "input": ""
}

response = requests.post(f"{api_url}/", json=data)
if response.status_code == 200:
    result = response.json()
    print("Job ID:", result["job_id"])
    print("Status:", result["status"])
    print("Output:", result["output"])
else:
    print("Error:", response.text)
```
Thank you for paying a visit to this repo.Kindly visit my other repos too ...
