from flask import Flask, jsonify, request
import subprocess
import os
import re

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(BASE_DIR, "runner.py")

# Ensure RUNNER is absolute path
RUNNER = os.path.abspath(RUNNER)

# Debug: print paths
print(f"BASE_DIR: {BASE_DIR}")
print(f"RUNNER: {RUNNER}")
print(f"RUNNER exists: {os.path.exists(RUNNER)}")
print(f"Files in BASE_DIR: {os.listdir(BASE_DIR) if os.path.exists(BASE_DIR) else 'N/A'}")


@app.route("/")
def home():
    return "API is running"


@app.route("/generate")
def generate():

    package = request.args.get("package", "standare")

    try:
        # Run runner.py
        result = subprocess.check_output(
            ["python", RUNNER, package],
            cwd=BASE_DIR,
            text=True,
            stderr=subprocess.STDOUT
        ).strip()

        # Extract ONLY URLs from output
        urls = re.findall(r'https?://\S+', result)

        final_url = urls[-1] if urls else result if result.startswith("http") else None

        if final_url:
            # Return only the URL as plain text
            return final_url, 200, {'Content-Type': 'text/plain'}
        else:
            return "No URL found", 404, {'Content-Type': 'text/plain'}

    except subprocess.CalledProcessError:
        return "Error generating URL", 500, {'Content-Type': 'text/plain'}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)