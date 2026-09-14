import os
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, 
    flash, session, send_from_directory, abort
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "aec_secret_key_prod_2026_super_safe")

# Configurações de Pastas de Upload
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER_IMG = os.path.join(BASE_DIR, "static", "uploads")
UPLOAD_FOLDER_CURRICULOS = os.path.join(BASE_DIR, "static", "uploads", "curriculos")

os.makedirs(UPLOAD_FOLDER_IMG, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_CURRICULOS, exist_ok=True)

app.config["UPLOAD_FOLDER_IMG"] = UPLOAD_FOLDER_IMG
app.config["UPLOAD_FOLDER_CURRICULOS"] = UPLOAD_FOLDER_CURRICULOS

ALLOWED_IMG_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "svg"}
ALLOWED_DOC_EXTENSIONS = {"pdf", "doc", "docx"}

DB_PATH = os.path.join(BASE_DIR, "leads.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def allowed_img_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMG_EXTENSIONS

def allowed_doc_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_DOC_EXTENSIONS

# ================= BANCO DE DADOS =================

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabela de Leads Comerciais
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            empresa TEXT NOT NULL,
            telefone TEXT NOT NULL,
            vidas TEXT NOT NULL,
            servico TEXT NOT NULL,
            data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tabela de Imagens Dinâmicas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_images (
            chave TEXT PRIMARY KEY,
            url TEXT NOT NULL
        )
    """)

    # Se existir uma tabela site_texts com esquema legado/antigo, recria com o formato correto
    cursor.execute("DROP TABLE IF EXISTS site_texts")

    # Tabela de Textos e Métricas Dinâmicas (Esquema Oficial)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_texts (
            chave TEXT PRIMARY KEY,
            conteudo TEXT NOT NULL
        )
    """)

    # Tabela de Candidaturas / Trabalhe Conosco
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS curriculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            telefone TEXT NOT NULL,
            area TEXT NOT NULL,
            arquivo_curriculo TEXT NOT NULL,
            data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabela de Imagens Dinâmicas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_images (
            chave TEXT PRIMARY KEY,
            url TEXT NOT NULL
        )
    """)

    # Tabela de Textos e Métricas Dinâmicas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_texts (
            chave TEXT PRIMARY KEY,
            conteudo TEXT NOT NULL
        )
    """)

    # Tabela de Candidaturas / Trabalhe Conosco
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS curriculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL,
            telefone TEXT NOT NULL,
            area TEXT NOT NULL,
            arquivo_curriculo TEXT NOT NULL,
            data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Imagens Padrão
    imagens_padrao = {
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

    for chave, url in imagens_padrao.items():
        cursor.execute("INSERT OR IGNORE INTO site_images (chave, url) VALUES (?, ?)", (chave, url))

    # Textos e Métricas Padrão
    textos_padrao = {
        "stats_clientes_num": "450+",
        "stats_clientes_titulo": "Empresas Assessoradas",
        "stats_clientes_desc": "Conformidade e gestão contínua de SST em diversos segmentos.",
        "stats_consultorias_num": "100%",
        "stats_consultorias_titulo": "Conformidade eSocial",
        "stats_consultorias_desc": "Disparos dentro dos prazos legais dos eventos S-2210, S-2220 e S-2240.",
        "stats_horas_num": "15k+",
        "stats_horas_titulo": "ASOs e Laudos Emitidos",
        "stats_horas_desc": "Prontidão clínica e respaldo pericial completo com ART e CRM."
    }

    for chave, conteudo in textos_padrao.items():
        cursor.execute("INSERT OR IGNORE INTO site_texts (chave, conteudo) VALUES (?, ?)", (chave, conteudo))

    conn.commit()
    conn.close()

init_db()

def get_site_images():
    conn = get_db_connection()
    rows = conn.execute("SELECT chave, url FROM site_images").fetchall()
    conn.close()
    return {row["chave"]: row["url"] for row in rows}

def get_site_texts():
    conn = get_db_connection()
    rows = conn.execute("SELECT chave, conteudo FROM site_texts").fetchall()
    conn.close()
    return {row["chave"]: row["conteudo"] for row in rows}

# ================= NOTIFICAÇÃO SMTP =================

def enviar_alerta_email(lead_data):
    smtp_server = os.getenv("MAIL_SERVER")
    smtp_port = int(os.getenv("MAIL_PORT", 587))
    smtp_user = os.getenv("MAIL_USERNAME")
    smtp_pass = os.getenv("MAIL_PASSWORD")
    destinatario = os.getenv("MAIL_DESTINATARIO", "contato@aecsst.com.br")

    if not all([smtp_server, smtp_user, smtp_pass]):
        return False

    msg = MIMEMultipart()
    msg["From"] = f"A&C SST Site <{smtp_user}>"
    msg["To"] = destinatario
    msg["Subject"] = f"Novo Lead Comercial: {lead_data['empresa']} ({lead_data['nome']})"

    corpo = f"""
    NOVO CONTATO RECEBIDO PELO SITE - A&C GOVERNANÇA EM SST
    -------------------------------------------------------
    Nome / Responsável: {lead_data['nome']}
    Empresa / Razão Social: {lead_data['empresa']}
    WhatsApp / Telefone: {lead_data['telefone']}
    Nº de Colaboradores: {lead_data['vidas']}
    Serviço de Interesse: {lead_data['servico']}
    Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
    -------------------------------------------------------
    Mensagem enviada automaticamente pelo sistema do site.
    """
    msg.attach(MIMEText(corpo, "plain", "utf-8"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Aviso: Erro no envio do e-mail: {e}")
        return False

# ================= DECORATOR DE AUTENTICAÇÃO =================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logado"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function

# ================= ROTAS PÚBLICAS =================

@app.route("/", methods=["GET"])
def home():
    imagens = get_site_images()
    textos = get_site_texts()
    dados_site = {
        "page_title": "A&C Governança em Saúde e Segurança do Trabalho",
        "contact_email": os.getenv("MAIL_DESTINATARIO", "contato@aecsst.com.br"),
        "whatsapp_num": os.getenv("WHATSAPP_NUM", "5534920017086"),
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

    if not all([nome, empresa, telefone]):
        flash("Por favor, preencha todos os campos obrigatórios.", "erro")
        return redirect(url_for("home") + "#proposta")

    conn = get_db_connection()
    conn.execute("""
        INSERT INTO leads (nome, empresa, telefone, vidas, servico)
        VALUES (?, ?, ?, ?, ?)
    """, (nome, empresa, telefone, vidas, servico))
    conn.commit()
    conn.close()

    enviar_alerta_email({
        "nome": nome,
        "empresa": empresa,
        "telefone": telefone,
        "vidas": vidas,
        "servico": servico
    })

    flash("Sua solicitação foi enviada com sucesso! Nossos especialistas entrarão em contato em breve.", "sucesso")
    return redirect(url_for("home") + "#proposta")

@app.route("/trabalhe-conosco", methods=["POST"])
def trabalhe_conosco():
    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip()
    telefone = request.form.get("telefone", "").strip()
    area = request.form.get("area", "").strip()
    arquivo = request.files.get("curriculo")

    if not all([nome, email, telefone, area]):
        flash("Preencha todos os campos cadastrais.", "erro_curriculo")
        return redirect(url_for("home") + "#trabalhe-conosco")

    if not arquivo or arquivo.filename == "":
        flash("Por favor, selecione e anexe seu currículo (PDF ou DOCX).", "erro_curriculo")
        return redirect(url_for("home") + "#trabalhe-conosco")

    if arquivo and allowed_doc_file(arquivo.filename):
        ext = arquivo.filename.rsplit(".", 1)[1].lower()
        nome_limpo = "".join(c for c in nome if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = secure_filename(f"CV_{nome_limpo}_{timestamp}.{ext}")

        caminho_final = os.path.join(app.config["UPLOAD_FOLDER_CURRICULOS"], nome_arquivo)
        arquivo.save(caminho_final)

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO curriculos (nome, email, telefone, area, arquivo_curriculo)
            VALUES (?, ?, ?, ?, ?)
        """, (nome, email, telefone, area, nome_arquivo))
        conn.commit()
        conn.close()

        flash("Candidatura cadastrada com sucesso! Nosso RH analisará seu perfil.", "sucesso_curriculo")
        return redirect(url_for("home") + "#trabalhe-conosco")
    else:
        flash("Formato de currículo inválido. Use apenas arquivos .PDF, .DOC ou .DOCX.", "erro_curriculo")
        return redirect(url_for("home") + "#trabalhe-conosco")

# ================= PAINEL ADMINISTRATIVO =================

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_logado"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")
        
        user_padrao = os.getenv("ADMIN_USER", "admin")
        pass_padrao = os.getenv("ADMIN_PASS", "aec2026admin")

        if usuario == user_padrao and senha == pass_padrao:
            session["admin_logado"] = True
            flash("Login efetuado com sucesso.", "sucesso")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Credenciais de acesso incorretas.", "erro")

    return render_template("login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logado", None)
    flash("Sessão encerrada com sucesso.", "sucesso")
    return redirect(url_for("admin_login"))

@app.route("/admin", methods=["GET"])
@login_required
def admin_dashboard():
    conn = get_db_connection()
    leads = conn.execute("SELECT * FROM leads ORDER BY data_envio DESC").fetchall()
    curriculos = conn.execute("SELECT * FROM curriculos ORDER BY data_envio DESC").fetchall()
    imagens = conn.execute("SELECT chave, url FROM site_images").fetchall()
    textos = conn.execute("SELECT chave, conteudo FROM site_texts").fetchall()
    conn.close()

    img_dict = {img["chave"]: img["url"] for img in imagens}
    txt_dict = {txt["chave"]: txt["conteudo"] for txt in textos}

    return render_template(
        "admin.html", 
        leads=leads, 
        curriculos=curriculos, 
        img=img_dict, 
        txt=txt_dict
    )

@app.route("/admin/atualizar-imagem", methods=["POST"])
@login_required
def admin_atualizar_imagem():
    chave = request.form.get("chave")
    url_remota = request.form.get("url_remota", "").strip()
    arquivo = request.files.get("arquivo_imagem")

    url_final = None

    if arquivo and arquivo.filename != "":
        if allowed_img_file(arquivo.filename):
            ext = arquivo.filename.rsplit(".", 1)[1].lower()
            nome_arquivo = secure_filename(f"{chave}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}")
            caminho_salvar = os.path.join(app.config["UPLOAD_FOLDER_IMG"], nome_arquivo)
            arquivo.save(caminho_salvar)
            url_final = f"/static/uploads/{nome_arquivo}"
        else:
            flash("Formato de imagem inválido. Formatos aceitos: PNG, JPG, JPEG, WEBP, SVG.", "erro")
            return redirect(url_for("admin_dashboard"))
    elif url_remota:
        url_final = url_remota

    if url_final:
        conn = get_db_connection()
        conn.execute("INSERT OR REPLACE INTO site_images (chave, url) VALUES (?, ?)", (chave, url_final))
        conn.commit()
        conn.close()
        flash(f"Imagem de '{chave}' atualizada com sucesso.", "sucesso")
    else:
        flash("Nenhuma imagem enviada ou URL especificada.", "erro")

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/atualizar-metricas", methods=["POST"])
@login_required
def admin_atualizar_metricas():
    campos = [
        "stats_clientes_num", "stats_clientes_titulo", "stats_clientes_desc",
        "stats_consultorias_num", "stats_consultorias_titulo", "stats_consultorias_desc",
        "stats_horas_num", "stats_horas_titulo", "stats_horas_desc"
    ]

    conn = get_db_connection()
    for campo in campos:
        valor = request.form.get(campo, "").strip()
        if valor:
            conn.execute("INSERT OR REPLACE INTO site_texts (chave, conteudo) VALUES (?, ?)", (campo, valor))
    conn.commit()
    conn.close()

    flash("Métricas e indicadores operacionais atualizados com sucesso.", "sucesso")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/curriculo/<path:filename>")
@login_required
def baixar_curriculo(filename):
    safe_filename = secure_filename(filename)
    return send_from_directory(app.config["UPLOAD_FOLDER_CURRICULOS"], safe_filename, as_attachment=True)

@app.route("/admin/excluir-lead/<int:id>", methods=["POST"])
@login_required
def excluir_lead(id):
    conn = get_db_connection()
    conn.execute("DELETE FROM leads WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    flash("Lead removido com sucesso.", "sucesso")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/excluir-curriculo/<int:id>", methods=["POST"])
@login_required
def excluir_curriculo(id):
    conn = get_db_connection()
    cv = conn.execute("SELECT arquivo_curriculo FROM curriculos WHERE id = ?", (id,)).fetchone()
    if cv:
        caminho_arq = os.path.join(app.config["UPLOAD_FOLDER_CURRICULOS"], cv["arquivo_curriculo"])
        if os.path.exists(caminho_arq):
            try:
                os.remove(caminho_arq)
            except OSError:
                pass
        conn.execute("DELETE FROM curriculos WHERE id = ?", (id,))
        conn.commit()
    conn.close()
    flash("Candidatura removida.", "sucesso")
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)