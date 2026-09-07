import os
import sqlite3
from datetime import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, Response
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "aec-sst-secret-key-2026")

DB_NAME = "leads.db"
UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DEFAULT_IMAGES = {
    "logo": "/static/img/logo.png",
    "servico_pgr": "https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=600&q=80",
    "servico_pcmso": "https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=600&q=80",
    "servico_treinamentos": "https://images.unsplash.com/photo-1504917599217-d4dc5ebe6122?auto=format&fit=crop&w=600&q=80",
    "estrutura_recepcao": "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=600&q=80",
    "estrutura_consultorio": "https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=600&q=80",
    "estrutura_exames": "https://images.unsplash.com/photo-1579684385127-1ef15d508118?auto=format&fit=crop&w=600&q=80",
    "estrutura_treinamento": "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?auto=format&fit=crop&w=600&q=80",
    "sobre_1": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?auto=format&fit=crop&w=500&q=80",
    "sobre_2": "https://images.unsplash.com/photo-1541888946425-d0fbb18086f6?auto=format&fit=crop&w=500&q=80",
    "sobre_3": "https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=500&q=80",
    "sobre_4": "https://images.unsplash.com/photo-1578575437130-527eed3abbec?auto=format&fit=crop&w=500&q=80"
}

DEFAULT_TEXTS = {
    "stats_clientes_num": "+300",
    "stats_clientes_titulo": "Clientes Atendidos",
    "stats_clientes_desc": "Empresas fortalecidas com soluções integradas de SST.",
    "stats_consultorias_num": "+125",
    "stats_consultorias_titulo": "Consultorias Concluídas",
    "stats_consultorias_desc": "Projetos entregues com rigor técnico e conformidade.",
    "stats_horas_num": "+400h",
    "stats_horas_titulo": "Horas de Treinamento",
    "stats_horas_desc": "Capacitação prática em conformidade com as Normas Regulamentadoras."
}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ==========================================
# BANCO DE DADOS (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_envio TEXT NOT NULL,
            nome TEXT NOT NULL,
            empresa TEXT NOT NULL,
            telefone TEXT NOT NULL,
            vidas TEXT NOT NULL,
            servico TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_images (
            chave TEXT PRIMARY KEY,
            url TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_texts (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)

    for chave, url in DEFAULT_IMAGES.items():
        cursor.execute("INSERT OR IGNORE INTO site_images (chave, url) VALUES (?, ?)", (chave, url))

    for chave, valor in DEFAULT_TEXTS.items():
        cursor.execute("INSERT OR IGNORE INTO site_texts (chave, valor) VALUES (?, ?)", (chave, valor))

    conn.commit()
    conn.close()

def get_site_images():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT chave, url FROM site_images")
    rows = cursor.fetchall()
    conn.close()
    
    imagens = DEFAULT_IMAGES.copy()
    for chave, url in rows:
        imagens[chave] = url
    return imagens

def update_image_url(chave, url):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO site_images (chave, url) VALUES (?, ?)", (chave, url))
    conn.commit()
    conn.close()

def get_site_texts():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT chave, valor FROM site_texts")
    rows = cursor.fetchall()
    conn.close()
    
    textos = DEFAULT_TEXTS.copy()
    for chave, valor in rows:
        textos[chave] = valor
    return textos

def update_site_texts(novos_textos):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for chave, valor in novos_textos.items():
        cursor.execute("INSERT OR REPLACE INTO site_texts (chave, valor) VALUES (?, ?)", (chave, valor.strip()))
    conn.commit()
    conn.close()

def salvar_lead(nome, empresa, telefone, vidas, servico):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cursor.execute("""
            INSERT INTO leads (data_envio, nome, empresa, telefone, vidas, servico)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (agora, nome, empresa, telefone, vidas, servico))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ [ERRO DB] Falha ao salvar no banco: {e}")
        return False

# ==========================================
# AUTENTICAÇÃO BÁSICA
# ==========================================
def check_auth(username, password):
    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_pass = os.getenv("ADMIN_PASS", "aec2026")
    return username == admin_user and password == admin_pass

def authenticate():
    return Response(
        "Acesso restrito. Faça login com credenciais de administrador.",
        401,
        {"WWW-Authenticate": 'Basic realm="Login Obrigatorio"'}
    )

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# ==========================================
# ENVIO DE E-MAIL
# ==========================================
def enviar_email_proposta(nome, empresa, telefone, vidas, servico):
    servidor_smtp = os.getenv("MAIL_SERVER")
    porta_smtp = int(os.getenv("MAIL_PORT", 587))
    usuario_smtp = os.getenv("MAIL_USERNAME")
    senha_smtp = os.getenv("MAIL_PASSWORD")
    destinatario = os.getenv("MAIL_DESTINATARIO", "contato@aecsst.com.br")

    if not servidor_smtp or not usuario_smtp or not senha_smtp:
        return False

    mensagem = MIMEMultipart()
    mensagem["From"] = usuario_smtp
    mensagem["To"] = destinatario
    mensagem["Subject"] = f"🔔 Novo Orçamento no Site: {empresa} - {nome}"

    corpo = f"""
    Nova proposta comercial solicitada no site:
    Nome: {nome}
    Empresa: {empresa}
    Telefone/WhatsApp: {telefone}
    Vidas: {vidas}
    Serviço: {servico}
    Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
    """
    mensagem.attach(MIMEText(corpo, "plain", "utf-8"))

    try:
        servidor = smtplib.SMTP(servidor_smtp, porta_smtp)
        servidor.starttls()
        servidor.login(usuario_smtp, senha_smtp)
        servidor.sendmail(usuario_smtp, destinatario, mensagem.as_string())
        servidor.quit()
        return True
    except Exception as e:
        print(f"❌ [ERRO SMTP] Falha ao enviar e-mail: {e}")
        return False

# ==========================================
# ROTAS PÚBLICAS
# ==========================================
@app.route("/", methods=["GET"])
def home():
    imagens = get_site_images()
    textos = get_site_texts()
    dados_site = {
        "page_title": "A&C Governança em Saúde e Segurança do Trabalho",
        "contact_email": os.getenv("MAIL_DESTINATARIO", "contato@aecsst.com.br"),
        "whatsapp_num": os.getenv("WHATSAPP_NUM", "5534920017086"),  # <-- NÚMERO ATUALIZADO
        "portal_treinamento_url": "https://aecsst.com.br/#/treinamentos",
        "portal_cliente_url": "https://aecsst.com.br/#/cliente",
        "img": imagens,
        "txt": textos
    }
    return render_template("index.html", **dados_site)

@app.route("/contato", methods=["POST"])
def contato():
    nome = request.form.get("nome", "").strip()
    empresa = request.form.get("empresa", "").strip()
    telefone = request.form.get("telefone", "").strip()
    vidas = request.form.get("vidas", "").strip()
    servico = request.form.get("servico", "").strip()

    salvar_lead(nome, empresa, telefone, vidas, servico)
    enviar_email_proposta(nome, empresa, telefone, vidas, servico)

    flash("Proposta enviada com sucesso! Entraremos em contato em breve.", "sucesso")
    return redirect(url_for("home", _anchor="proposta"))

# ==========================================
# ROTAS ADMINISTRATIVAS
# ==========================================
@app.route("/admin")
@requires_auth
def admin_dashboard():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM leads")
    total_leads = cursor.fetchone()[0]
    conn.close()
    return render_template("admin_dashboard.html", total_leads=total_leads)

@app.route("/admin/leads")
@requires_auth
def admin_leads():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, data_envio, nome, empresa, telefone, vidas, servico FROM leads ORDER BY id DESC")
    leads = cursor.fetchall()
    conn.close()
    return render_template("admin_leads.html", leads=leads)

@app.route("/admin/imagens", methods=["GET", "POST"])
@requires_auth
def admin_imagens():
    if request.method == "POST":
        chave = request.form.get("chave")
        arquivo = request.files.get("arquivo")

        if chave and arquivo and arquivo.filename != "" and allowed_file(arquivo.filename):
            extensao = arquivo.filename.rsplit(".", 1)[1].lower()
            nome_seguro = f"{chave}_{int(datetime.now().timestamp())}.{extensao}"
            caminho_completo = os.path.join(app.config["UPLOAD_FOLDER"], nome_seguro)
            arquivo.save(caminho_completo)

            url_publica = f"/static/uploads/{nome_seguro}"
            update_image_url(chave, url_publica)
            flash("Imagem atualizada com sucesso!", "sucesso")
        else:
            flash("Formato de arquivo inválido ou não selecionado.", "erro")

        return redirect(url_for("admin_imagens"))

    imagens = get_site_images()
    return render_template("admin_imagens.html", imagens=imagens)

@app.route("/admin/metricas", methods=["GET", "POST"])
@requires_auth
def admin_metricas():
    if request.method == "POST":
        novos_textos = {
            "stats_clientes_num": request.form.get("stats_clientes_num", "+300"),
            "stats_clientes_titulo": request.form.get("stats_clientes_titulo", "Clientes Atendidos"),
            "stats_clientes_desc": request.form.get("stats_clientes_desc", ""),
            "stats_consultorias_num": request.form.get("stats_consultorias_num", "+125"),
            "stats_consultorias_titulo": request.form.get("stats_consultorias_titulo", "Consultorias Concluídas"),
            "stats_consultorias_desc": request.form.get("stats_consultorias_desc", ""),
            "stats_horas_num": request.form.get("stats_horas_num", "+400h"),
            "stats_horas_titulo": request.form.get("stats_horas_titulo", "Horas de Treinamento"),
            "stats_horas_desc": request.form.get("stats_horas_desc", "")
        }
        update_site_texts(novos_textos)
        flash("Indicadores atualizados com sucesso!", "sucesso")
        return redirect(url_for("admin_metricas"))

    textos = get_site_texts()
    return render_template("admin_metricas.html", txt=textos)

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)