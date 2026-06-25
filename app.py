from flask import Flask, request, send_file, render_template_string, jsonify
import subprocess
import os
import uuid
import json

app = Flask(__name__)

UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================
# HTML (UI simples com abas)
# =========================
HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Image Metadata Tool</title>
  <style>
    body { font-family: Arial; max-width: 700px; margin: 40px auto; text-align: center; }
    .box { border: 2px dashed #ccc; padding: 20px; margin-bottom: 20px; }
    button { padding: 10px; margin-top: 10px; cursor: pointer; }
    input { padding: 8px; }
    .tabs { display: flex; justify-content: center; margin-bottom: 20px; }
    .tab { margin: 0 10px; cursor: pointer; padding: 10px; border: 1px solid #ccc; }
    .active { background: #eee; }
    pre { text-align: left; background: #111; color: #0f0; padding: 15px; overflow-x: auto; }
  </style>
</head>
<body>

<h2>🧼📊 Image Metadata Tool</h2>

<div class="tabs">
  <div class="tab active" onclick="showTab('clean')">Remover Metadados</div>
  <div class="tab" onclick="showTab('analyze')">Analisar Metadados</div>
</div>

<!-- CLEAN -->
<div id="clean" class="box">
  <h3>Remover Metadados</h3>
  <form method="post" action="/clean" enctype="multipart/form-data">
    <input type="file" name="file" required><br>
    <button type="submit">Upload e limpar</button>
  </form>
</div>

<!-- ANALYZE -->
<div id="analyze" class="box" style="display:none;">
  <h3>Analisar Metadados</h3>
  <form id="analyzeForm">
    <input type="file" name="file" required><br>
    <button type="submit">Analisar</button>
  </form>

  <pre id="result"></pre>
</div>

<script>
function showTab(tab) {
  document.getElementById("clean").style.display = tab === 'clean' ? 'block' : 'none';
  document.getElementById("analyze").style.display = tab === 'analyze' ? 'block' : 'none';
}

document.getElementById("analyzeForm").onsubmit = async function(e) {
  e.preventDefault();

  let formData = new FormData(this);

  let res = await fetch("/analyze", {
    method: "POST",
    body: formData
  });

  let data = await res.json();
  document.getElementById("result").innerText = JSON.stringify(data, null, 2);
};
</script>

</body>
</html>
"""

# =========================
# Função segura exiftool
# =========================
def run_exiftool(args, timeout=30):
    try:
        result = subprocess.run(
            ["exiftool"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout
        )
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Erro: timeout no processamento do exiftool."


# =========================
# HOME
# =========================
@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML)


# =========================
# REMOVER METADADOS
# =========================
@app.route("/clean", methods=["POST"])
def clean():
    file = request.files["file"]

    uid = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]

    input_path = f"{UPLOAD_DIR}/{uid}{ext}"
    output_path = f"{UPLOAD_DIR}/{uid}_clean{ext}"

    file.save(input_path)

    try:
        subprocess.run(
            ["exiftool", "-all=", "-o", output_path, input_path],
            check=True,
            timeout=30
        )
    except subprocess.TimeoutExpired:
        return "Erro: processamento demorou demais.", 500

    # Download direto (browser permite escolher local)
    return send_file(
        output_path,
        as_attachment=True,
        download_name=file.filename
    )


# =========================
# ANALISAR METADADOS
# =========================
@app.route("/analyze", methods=["POST"])
def analyze():
    file = request.files["file"]

    uid = str(uuid.uuid4())
    path = f"{UPLOAD_DIR}/{uid}"

    file.save(path)

    output = run_exiftool([path])

    try:
        data = json.loads(output)
    except:
        data = {"raw_output": output}

    return jsonify(data)


# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
