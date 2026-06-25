from flask import Flask, request, send_file, render_template_string, jsonify
import subprocess
import os
import uuid
import json

app = Flask(__name__)

UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Limite de upload (50 MB)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Image Metadata Tool</title>

<style>
body{
    font-family:Arial,sans-serif;
    max-width:1000px;
    margin:40px auto;
    padding:20px;
}

.box{
    border:2px dashed #ccc;
    padding:20px;
    margin-top:20px;
}

.tabs{
    display:flex;
    gap:10px;
    margin-bottom:20px;
}

.tab{
    border:1px solid #ccc;
    padding:10px 20px;
    cursor:pointer;
    border-radius:5px;
}

.active{
    background:#eee;
}

button{
    padding:10px 20px;
    cursor:pointer;
}

input[type=file]{
    margin-bottom:10px;
}

table{
    width:100%;
    border-collapse:collapse;
    margin-top:20px;
}

th,td{
    border:1px solid #ddd;
    padding:8px;
    text-align:left;
    vertical-align:top;
}

th{
    background:#f0f0f0;
}

tr:nth-child(even){
    background:#fafafa;
}

#searchBox{
    width:100%;
    padding:10px;
    margin-top:15px;
    box-sizing:border-box;
}

.loading{
    margin-top:15px;
    color:#555;
}
</style>
</head>
<body>

<h1>🧼 Remover e Analisar Metadados</h1>

<div class="tabs">
    <div class="tab active" id="tabClean" onclick="showTab('clean')">
        Remover Metadados
    </div>

    <div class="tab" id="tabAnalyze" onclick="showTab('analyze')">
        Analisar Metadados
    </div>
</div>

<div id="clean" class="box">

    <h2>Remover Metadados</h2>

    <form method="POST" action="/clean" enctype="multipart/form-data">
        <input type="file" name="file" required>
        <br>
        <button type="submit">
            Limpar Arquivo
        </button>
    </form>

</div>

<div id="analyze" class="box" style="display:none;">

    <h2>Analisar Metadados</h2>

    <form id="analyzeForm">
        <input type="file" name="file" required>
        <br>
        <button type="submit">
            Analisar
        </button>
    </form>

    <div class="loading" id="loading"></div>

    <input
        type="text"
        id="searchBox"
        placeholder="Pesquisar metadados..."
        style="display:none;"
    >

    <div id="result"></div>

</div>

<script>

function showTab(tab){

    document.getElementById("clean").style.display =
        tab === "clean" ? "block" : "none";

    document.getElementById("analyze").style.display =
        tab === "analyze" ? "block" : "none";

    document.getElementById("tabClean").classList.remove("active");
    document.getElementById("tabAnalyze").classList.remove("active");

    if(tab === "clean"){
        document.getElementById("tabClean").classList.add("active");
    }else{
        document.getElementById("tabAnalyze").classList.add("active");
    }
}

document.getElementById("analyzeForm").addEventListener(
    "submit",
    async function(e){

        e.preventDefault();

        document.getElementById("loading").innerText =
            "Analisando arquivo...";

        document.getElementById("result").innerHTML = "";

        let formData = new FormData(this);

        try{

            let response = await fetch("/analyze",{
                method:"POST",
                body:formData
            });

            let data = await response.json();

            let metadata = Array.isArray(data)
                ? data[0]
                : data;

            let html = `
                <table id="metadataTable">
                <thead>
                    <tr>
                        <th>Campo</th>
                        <th>Valor</th>
                    </tr>
                </thead>
                <tbody>
            `;

            for(const [key,value] of Object.entries(metadata)){

                html += `
                <tr>
                    <td>${escapeHtml(key)}</td>
                    <td>${escapeHtml(String(value))}</td>
                </tr>
                `;
            }

            html += "</tbody></table>";

            document.getElementById("result").innerHTML = html;

            document.getElementById("searchBox").style.display =
                "block";

            document.getElementById("loading").innerText = "";

        }catch(err){

            document.getElementById("loading").innerText =
                "Erro ao analisar arquivo.";

        }

    }
);

document.getElementById("searchBox").addEventListener(
    "keyup",
    function(){

        let filter =
            this.value.toLowerCase();

        let rows =
            document.querySelectorAll(
                "#metadataTable tbody tr"
            );

        rows.forEach(row=>{

            let text =
                row.innerText.toLowerCase();

            row.style.display =
                text.includes(filter)
                ? ""
                : "none";

        });

    }
);

function escapeHtml(text){

    let div =
        document.createElement("div");

    div.innerText = text;

    return div.innerHTML;
}

</script>

</body>
</html>
"""

def run_exiftool(args, timeout=30):

    result = subprocess.run(
        ["exiftool"] + args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout
    )

    if result.returncode != 0:
        raise Exception(result.stderr)

    return result.stdout


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/analyze", methods=["POST"])
def analyze():

    if "file" not in request.files:
        return jsonify({"error": "Arquivo não enviado"}), 400

    file = request.files["file"]

    ext = os.path.splitext(file.filename)[1]
    uid = str(uuid.uuid4())

    path = os.path.join(
        UPLOAD_DIR,
        uid + ext
    )

    file.save(path)

    try:

        output = run_exiftool(
            ["-j", path]
        )

        data = json.loads(output)

        return jsonify(data)

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500

    finally:

        if os.path.exists(path):
            os.remove(path)


@app.route("/clean", methods=["POST"])
def clean():

    if "file" not in request.files:
        return "Arquivo não enviado", 400

    file = request.files["file"]

    ext = os.path.splitext(file.filename)[1]

    uid = str(uuid.uuid4())

    input_path = os.path.join(
        UPLOAD_DIR,
        uid + ext
    )

    output_path = os.path.join(
        UPLOAD_DIR,
        uid + "_clean" + ext
    )

    file.save(input_path)

    try:

        subprocess.run(
            [
                "exiftool",
                "-all=",
                "-o",
                output_path,
                input_path
            ],
            check=True,
            timeout=30
        )

        return send_file(
            output_path,
            as_attachment=True,
            download_name=file.filename
        )

    except subprocess.TimeoutExpired:

        return "Processamento demorou demais.", 500

    except Exception as e:

        return f"Erro: {e}", 500

    finally:

        if os.path.exists(input_path):
            os.remove(input_path)

        # output removido após envio
        # o sistema operacional limpará ao reiniciar
        # ou você pode criar um cron de limpeza

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080
    )
