from flask import Flask, request, send_file, render_template_string
import subprocess
import os
import uuid
import threading

app = Flask(__name__)

UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Exif Cleaner</title>
  <style>
    body { font-family: Arial; max-width: 600px; margin: 50px auto; text-align: center; }
    input, button { padding: 10px; margin-top: 10px; }
    .box { border: 2px dashed #ccc; padding: 30px; }
  </style>
</head>
<body>
  <h2>🧼 Remover Metadados</h2>
  <div class="box">
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="file" required><br>
      <button type="submit">Enviar e limpar</button>
    </form>
  </div>
</body>
</html>
"""

def cleanup(path, delay=60):
    def _delete():
        try:
            os.remove(path)
        except:
            pass
    threading.Timer(delay, _delete).start()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template_string(HTML)

    file = request.files["file"]

    ext = os.path.splitext(file.filename)[1]
    uid = str(uuid.uuid4())

    input_path = f"{UPLOAD_DIR}/{uid}{ext}"
    output_path = f"{UPLOAD_DIR}/{uid}_clean{ext}"

    file.save(input_path)

    # remove TODOS os metadados e gera cópia limpa
    subprocess.run(
        ["exiftool", "-all=", "-o", output_path, input_path],
        check=True
    )

    # limpa arquivos originais depois
    cleanup(input_path, 10)
    cleanup(output_path, 300)

    return send_file(output_path, as_attachment=True, download_name=file.filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)