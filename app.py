# app.py
# Sistema de Assistência Técnica - Arquivo Único
# Tecnologias: Python (Flask), HTML, CSS
# Persistência simples: JSON (arquivo gerenciado pelo código)
# Autor: Copilot

import json
import os
from datetime import datetime
from flask import Flask, request, redirect, url_for, render_template_string, flash

app = Flask(__name__)
app.secret_key = "changeme-secret-key"  # ajuste se desejar

DATA_FILE = "data.json"

# -------------------------
# Persistência e estrutura
# -------------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "next_client_id": 1,
            "next_order_id": 1,
            "clients": {},  # id -> {id, nome, telefone, email, endereco, documento, observacoes}
            "orders": {}    # id -> {id, client_id, criado_em, prazo, status, prioridade, descricao, tecnico,
                            #         estimativa, pecas, mao_obra, total, notas}
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {
                "next_client_id": 1,
                "next_order_id": 1,
                "clients": {},
                "orders": {}
            }

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(DATA, f, ensure_ascii=False, indent=2)

DATA = load_data()

# -------------------------
# Utilitários
# -------------------------
STATUSES = ["Aberta", "Em andamento", "Concluída", "Cancelada"]
PRIORIDADES = ["Baixa", "Média", "Alta", "Crítica"]

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def calc_total(estimativa, pecas, mao_obra):
    def to_float(v):
        if v is None or v == "":
            return 0.0
        try:
            return float(str(v).replace(",", "."))
        except ValueError:
            return 0.0
    e = to_float(estimativa)
    p = to_float(pecas)
    m = to_float(mao_obra)
    return round((p + m) if e == 0 else e, 2)

def get_client_name(cid):
    c = DATA["clients"].get(str(cid))
    return c["nome"] if c else "Cliente removido"

def filtered_orders(q=None, status=None, prioridade=None, cliente_id=None):
    itens = []
    for oid, o in DATA["orders"].items():
        match = True
        if q:
            ql = q.lower()
            c_nome = get_client_name(o["client_id"]).lower()
            campos = " ".join([
                o.get("descricao",""), o.get("tecnico",""), o.get("notas",""), c_nome
            ]).lower()
            match = ql in campos
        if status and match:
            match = o.get("status") == status
        if prioridade and match:
            match = o.get("prioridade") == prioridade
        if cliente_id and match:
            match = str(o.get("client_id")) == str(cliente_id)
        if match:
            itens.append(o)
    # ordena por criado_em desc
    itens.sort(key=lambda x: x.get("criado_em",""), reverse=True)
    return itens

# -------------------------
# Layout base com CSS
# -------------------------
BASE = """
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Assistência Técnica</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {
  --bg: #0f172a;
  --panel: #111827;
  --muted: #94a3b8;
  --text: #e5e7eb;
  --accent: #22d3ee;
  --ok: #22c55e;
  --warn: #f59e0b;
  --bad: #ef4444;
  --border: #1f2937;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: radial-gradient(1200px circle at 10% 10%, #0b132e, var(--bg));
  color: var(--text); font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
}
a { color: var(--accent); text-decoration: none; }
header {
  position: sticky; top: 0; z-index: 50;
  background: rgba(17,24,39,0.7); backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
}
nav {
  max-width: 1100px; margin: 0 auto; display: flex; align-items: center; gap: 16px;
  padding: 12px 20px;
}
nav .brand { font-weight: 700; letter-spacing: 0.5px; }
nav .spacer { flex: 1; }
nav .menu a {
  padding: 8px 12px; border-radius: 8px; border: 1px solid transparent;
}
nav .menu a:hover { border-color: var(--border); background: #0b1220; }

main { max-width: 1100px; margin: 20px auto; padding: 0 20px; }

.panel {
  background: linear-gradient(180deg, rgba(31,41,55,0.7), rgba(17,24,39,0.7));
  border: 1px solid var(--border); border-radius: 14px; padding: 16px; margin-bottom: 18px;
}
.panel h2 { margin: 0 0 12px 0; font-size: 1.2rem; }

.grid {
  display: grid; grid-template-columns: repeat(12, 1fr); gap: 12px;
}
.card {
  background: rgba(2,6,23,0.5); border: 1px solid var(--border);
  border-radius: 12px; padding: 14px;
}
.card h3 { margin: 0 0 8px 0; font-size: 1rem; color: var(--muted); }

input, select, textarea {
  width: 100%; padding: 10px 12px; border-radius: 10px;
  border: 1px solid var(--border); background: #0b1220; color: var(--text);
}
label { font-size: 0.9rem; color: var(--muted); margin-bottom: 6px; display: block; }

button, .btn {
  display: inline-block; padding: 10px 14px; border-radius: 10px;
  border: 1px solid var(--border); background: #0b1220; color: var(--text);
  cursor: pointer;
}
button:hover, .btn:hover { border-color: var(--accent); color: var(--accent); }

.table { width: 100%; border-collapse: collapse; }
.table th, .table td { padding: 10px; border-bottom: 1px solid var(--border); text-align: left; }
.table th { color: var(--muted); font-weight: 600; }

.status { padding: 4px 8px; border-radius: 999px; font-size: 0.8rem; display: inline-block; }
.status.Aberta { background: #0b1220; border: 1px solid var(--accent); color: var(--accent); }
.status.Em\\ andamento { background: #0b1220; border: 1px solid var(--warn); color: var(--warn); }
.status.Concluída { background: #0b1220; border: 1px solid var(--ok); color: var(--ok); }
.status.Cancelada { background: #0b1220; border: 1px solid var(--bad); color: var(--bad); }

.alert { padding: 10px 12px; border: 1px solid var(--border); border-radius: 10px; background: #0b1220; margin-bottom: 12px; }

.footer { color: var(--muted); font-size: 0.85rem; text-align: center; padding: 20px 0; }

.printable { max-width: 800px; margin: 0 auto; background: white; color: #111; padding: 20px; border-radius: 8px; }
.printable h1 { margin-top: 0; }
@media print {
  header, nav, .footer { display: none; }
  body { background: white; }
  .printable { box-shadow: none; }
}
</style>
</head>
<body>
<header>
  <nav>
    <div class="brand">⚙️ Assistência Técnica</div>
    <div class="menu">
      <a href="{{ url_for('dashboard') }}">Dashboard</a>
      <a href="{{ url_for('list_clients') }}">Clientes</a>
      <a href="{{ url_for('list_orders') }}">Ordens</a>
      <a href="{{ url_for('new_order') }}">Nova OS</a>
      <a href="{{ url_for('new_client') }}">Novo Cliente</a>
    </div>
    <div class="spacer"></div>
  </nav>
</header>

<main>
  {% with messages = get_flashed_messages() %}
    {% if messages %}
      <div class="alert">
        {% for m in messages %}<div>{{ m }}</div>{% endfor %}
      </div>
    {% endif %}
  {% endwith %}
  {{ content|safe }}
</main>

<div class="footer">Feito com Python, Flask, HTML e CSS — Arquivo único</div>
</body>
</html>
"""

# -------------------------
# Páginas
# -------------------------
@app.route("/")
def dashboard():
    total_clientes = len(DATA["clients"])
    total_os = len(DATA["orders"])
    abertas = sum(1 for o in DATA["orders"].values() if o.get("status") == "Aberta")
    andamento = sum(1 for o in DATA["orders"].values() if o.get("status") == "Em andamento")
    concluidas = sum(1 for o in DATA["orders"].values() if o.get("status") == "Concluída")

    ultimas = sorted(DATA["orders"].values(), key=lambda x: x.get("criado_em",""), reverse=True)[:8]

    content = f"""
    <div class="panel">
      <h2>Visão geral</h2>
      <div class="grid">
        <div class="card" style="grid-column: span 3;">
          <h3>Clientes</h3>
          <div style="font-size: 1.8rem; font-weight: 700;">{total_clientes}</div>
        </div>
        <div class="card" style="grid-column: span 3;">
          <h3>Ordens</h3>
          <div style="font-size: 1.8rem; font-weight: 700;">{total_os}</div>
        </div>
        <div class="card" style="grid-column: span 2;">
          <h3>Abertas</h3>
          <div style="font-size: 1.4rem; font-weight: 700;">{abertas}</div>
        </div>
        <div class="card" style="grid-column: span 2;">
          <h3>Em andamento</h3>
          <div style="font-size: 1.4rem; font-weight: 700;">{andamento}</div>
        </div>
        <div class="card" style="grid-column: span 2;">
          <h3>Concluídas</h3>
          <div style="font-size: 1.4rem; font-weight: 700;">{concluidas}</div>
        </div>
      </div>
    </div>

    <div class="panel">
      <h2>Últimas ordens</h2>
      <table class="table">
        <thead>
          <tr>
            <th>ID</th><th>Cliente</th><th>Status</th><th>Prioridade</th><th>Descrição</th><th>Criado</th><th>Ações</th>
          </tr>
        </thead>
        <tbody>
        {"".join([
          f"<tr><td>{o['id']}</td><td>{get_client_name(o['client_id'])}</td>" +
          f"<td><span class='status {o['status']}'>{o['status']}</span></td>" +
          f"<td>{o.get('prioridade','')}</td><td>{o.get('descricao','')[:50]}</td>" +
          f"<td>{o.get('criado_em','')}</td>" +
          f"<td><a class='btn' href='{url_for('edit_order', order_id=o['id'])}'>Editar</a> " +
          f"<a class='btn' href='{url_for('print_order', order_id=o['id'])}'>Imprimir</a></td></tr>"
        for o in ultimas])}
        </tbody>
      </table>
    </div>
    """
    return render_template_string(BASE, content=content)

# ---- Clientes ----
@app.route("/clientes")
def list_clients():
    q = request.args.get("q","").strip()
    clients = list(DATA["clients"].values())
    if q:
        ql = q.lower()
        clients = [c for c in clients if ql in " ".join([
            c.get("nome",""), c.get("telefone",""), c.get("email",""), c.get("endereco",""),
            c.get("documento",""), c.get("observacoes","")
        ]).lower()]
    clients.sort(key=lambda x: x.get("nome","").lower())
    rows = "".join([
        f"<tr><td>{c['id']}</td><td>{c['nome']}</td><td>{c.get('telefone','')}</td><td>{c.get('email','')}</td>" +
        f"<td>{c.get('documento','')}</td>" +
        f"<td><a class='btn' href='{url_for('edit_client', client_id=c['id'])}'>Editar</a> " +
        f"<form style='display:inline' method='post' action='{url_for('delete_client', client_id=c['id'])}' onsubmit='return confirm(\"Excluir cliente?\")'>" +
        f"<button class='btn' type='submit'>Excluir</button></form></td></tr>"
    for c in clients])
    content = f"""
    <div class="panel">
      <h2>Clientes</h2>
      <form method="get" class="grid">
        <div style="grid-column: span 8;">
          <label>Buscar</label>
          <input type="text" name="q" value="{q}" placeholder="Nome, telefone, email, documento...">
        </div>
        <div style="grid-column: span 4; align-self: end;">
          <button type="submit">Filtrar</button>
          <a class="btn" href="{url_for('new_client')}">Novo cliente</a>
        </div>
      </form>
      <table class="table">
        <thead><tr><th>ID</th><th>Nome</th><th>Telefone</th><th>Email</th><th>Documento</th><th>Ações</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """
    return render_template_string(BASE, content=content)

@app.route("/clientes/novo", methods=["GET","POST"])
def new_client():
    if request.method == "POST":
        cid = DATA["next_client_id"]
        DATA["next_client_id"] += 1
        c = {
            "id": cid,
            "nome": request.form.get("nome","").strip(),
            "telefone": request.form.get("telefone","").strip(),
            "email": request.form.get("email","").strip(),
            "endereco": request.form.get("endereco","").strip(),
            "documento": request.form.get("documento","").strip(),
            "observacoes": request.form.get("observacoes","").strip()
        }
        DATA["clients"][str(cid)] = c
        save_data()
        flash("Cliente criado com sucesso.")
        return redirect(url_for("list_clients"))

    content = f"""
    <div class="panel">
      <h2>Novo cliente</h2>
      <form method="post" class="grid">
        <div style="grid-column: span 6;">
          <label>Nome</label>
          <input name="nome" required>
        </div>
        <div style="grid-column: span 3;">
          <label>Telefone</label>
          <input name="telefone">
        </div>
        <div style="grid-column: span 3;">
          <label>Email</label>
          <input name="email" type="email">
        </div>
        <div style="grid-column: span 6;">
          <label>Endereço</label>
          <input name="endereco">
        </div>
        <div style="grid-column: span 3;">
          <label>Documento (CPF/CNPJ)</label>
          <input name="documento">
        </div>
        <div style="grid-column: span 12;">
          <label>Observações</label>
          <textarea name="observacoes" rows="3"></textarea>
        </div>
        <div style="grid-column: span 12;">
          <button type="submit">Salvar</button>
          <a class="btn" href="{url_for('list_clients')}">Cancelar</a>
        </div>
      </form>
    </div>
    """
    return render_template_string(BASE, content=content)

@app.route("/clientes/<int:client_id>/editar", methods=["GET","POST"])
def edit_client(client_id):
    c = DATA["clients"].get(str(client_id))
    if not c:
        flash("Cliente não encontrado.")
        return redirect(url_for("list_clients"))
    if request.method == "POST":
        c["nome"] = request.form.get("nome","").strip()
        c["telefone"] = request.form.get("telefone","").strip()
        c["email"] = request.form.get("email","").strip()
        c["endereco"] = request.form.get("endereco","").strip()
        c["documento"] = request.form.get("documento","").strip()
        c["observacoes"] = request.form.get("observacoes","").strip()
        save_data()
        flash("Cliente atualizado.")
        return redirect(url_for("list_clients"))

    content = f"""
    <div class="panel">
      <h2>Editar cliente</h2>
      <form method="post" class="grid">
        <div style="grid-column: span 6;">
          <label>Nome</label>
          <input name="nome" value="{c.get('nome','')}" required>
        </div>
        <div style="grid-column: span 3;">
          <label>Telefone</label>
          <input name="telefone" value="{c.get('telefone','')}">
        </div>
        <div style="grid-column: span 3;">
          <label>Email</label>
          <input name="email" type="email" value="{c.get('email','')}">
        </div>
        <div style="grid-column: span 6;">
          <label>Endereço</label>
          <input name="endereco" value="{c.get('endereco','')}">
        </div>
        <div style="grid-column: span 3;">
          <label>Documento (CPF/CNPJ)</label>
          <input name="documento" value="{c.get('documento','')}">
        </div>
        <div style="grid-column: span 12;">
          <label>Observações</label>
          <textarea name="observacoes" rows="3">{c.get('observacoes','')}</textarea>
        </div>
        <div style="grid-column: span 12;">
          <button type="submit">Salvar</button>
          <a class="btn" href="{url_for('list_clients')}">Cancelar</a>
        </div>
      </form>
    </div>
    """
    return render_template_string(BASE, content=content)

@app.route("/clientes/<int:client_id>/excluir", methods=["POST"])
def delete_client(client_id):
    cid = str(client_id)
    if cid in DATA["clients"]:
        # impedir exclusão se houver OS
        has_os = any(str(o.get("client_id")) == cid for o in DATA["orders"].values())
        if has_os:
            flash("Não é possível excluir: existem ordens de serviço vinculadas.")
        else:
            del DATA["clients"][cid]
            save_data()
            flash("Cliente excluído.")
    else:
        flash("Cliente não encontrado.")
    return redirect(url_for("list_clients"))

# ---- Ordens de Serviço ----
@app.route("/ordens")
def list_orders():
    q = request.args.get("q","").strip()
    status = request.args.get("status","").strip() or None
    prioridade = request.args.get("prioridade","").strip() or None
    cliente_id = request.args.get("cliente_id","").strip() or None
    itens = filtered_orders(q, status, prioridade, cliente_id)

    client_options = "".join([f"<option value='{c['id']}' {'selected' if str(c['id'])==str(cliente_id) else ''}>{c['nome']}</option>"
                              for c in sorted(DATA['clients'].values(), key=lambda x: x['nome'].lower())])

    rows = "".join([
        f"<tr><td>{o['id']}</td><td>{get_client_name(o['client_id'])}</td>" +
        f"<td><span class='status {o['status']}'>{o['status']}</span></td>" +
        f"<td>{o.get('prioridade','')}</td><td>{o.get('descricao','')[:60]}</td>" +
        f"<td>{o.get('criado_em','')}</td><td>{o.get('prazo','')}</td>" +
        f"<td>R$ {str(o.get('total',0)).replace('.',',')}</td>" +
        f"<td><a class='btn' href='{url_for('edit_order', order_id=o['id'])}'>Editar</a> " +
        f"<a class='btn' href='{url_for('print_order', order_id=o['id'])}'>Imprimir</a> " +
        f"<form style='display:inline' method='post' action='{url_for('delete_order', order_id=o['id'])}' onsubmit='return confirm(\"Excluir OS?\")'>" +
        f"<button class='btn' type='submit'>Excluir</button></form></td></tr>"
    for o in itens])

    content = f"""
    <div class="panel">
      <h2>Ordens de serviço</h2>
      <form method="get" class="grid">
        <div style="grid-column: span 4;">
          <label>Buscar</label>
          <input type="text" name="q" value="{q}" placeholder="Cliente, descrição, técnico, notas...">
        </div>
        <div style="grid-column: span 3;">
          <label>Status</label>
          <select name="status">
            <option value="">Todos</option>
            {''.join([f"<option {'selected' if status==s else ''}>{s}</option>" for s in STATUSES])}
          </select>
        </div>
        <div style="grid-column: span 3;">
          <label>Prioridade</label>
          <select name="prioridade">
            <option value="">Todas</option>
            {''.join([f"<option {'selected' if prioridade==p else ''}>{p}</option>" for p in PRIORIDADES])}
          </select>
        </div>
        <div style="grid-column: span 2;">
          <label>Cliente</label>
          <select name="cliente_id">
            <option value="">Todos</option>
            {client_options}
          </select>
        </div>
        <div style="grid-column: span 12; align-self: end;">
          <button type="submit">Filtrar</button>
          <a class="btn" href="{url_for('new_order')}">Nova OS</a>
        </div>
      </form>
      <table class="table">
        <thead>
          <tr>
            <th>ID</th><th>Cliente</th><th>Status</th><th>Prioridade</th><th>Descrição</th><th>Criado</th>
            <th>Prazo</th><th>Total</th><th>Ações</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    """
    return render_template_string(BASE, content=content)

@app.route("/ordens/nova", methods=["GET","POST"])
def new_order():
    clients = sorted(DATA["clients"].values(), key=lambda x: x["nome"].lower())
    if request.method == "POST":
        if not clients:
            flash("Crie um cliente antes de abrir uma OS.")
            return redirect(url_for("new_client"))
        oid = DATA["next_order_id"]; DATA["next_order_id"] += 1
        client_id = int(request.form.get("client_id"))
        estimativa = request.form.get("estimativa","")
        pecas = request.form.get("pecas","")
        mao_obra = request.form.get("mao_obra","")
        total = calc_total(estimativa, pecas, mao_obra)
        o = {
            "id": oid,
            "client_id": client_id,
            "criado_em": now_str(),
            "prazo": request.form.get("prazo","").strip(),
            "status": request.form.get("status","Aberta"),
            "prioridade": request.form.get("prioridade","Média"),
            "descricao": request.form.get("descricao","").strip(),
            "tecnico": request.form.get("tecnico","").strip(),
            "estimativa": estimativa,
            "pecas": pecas,
            "mao_obra": mao_obra,
            "total": total,
            "notas": request.form.get("notas","").strip()
        }
        DATA["orders"][str(oid)] = o
        save_data()
        flash(f"OS #{oid} criada.")
        return redirect(url_for("list_orders"))

    client_options = "".join([f"<option value='{c['id']}'>{c['nome']}</option>" for c in clients])
    content = f"""
    <div class="panel">
      <h2>Nova OS</h2>
      <form method="post" class="grid">
        <div style="grid-column: span 6;">
          <label>Cliente</label>
          <select name="client_id" required>{client_options}</select>
        </div>
        <div style="grid-column: span 3;">
          <label>Status</label>
          <select name="status">{''.join([f"<option>{s}</option>" for s in STATUSES])}</select>
        </div>
        <div style="grid-column: span 3;">
          <label>Prioridade</label>
          <select name="prioridade">{''.join([f"<option>{p}</option>" for p in PRIORIDADES])}</select>
        </div>
        <div style="grid-column: span 8;">
          <label>Descrição do problema/serviço</label>
          <textarea name="descricao" rows="3" required></textarea>
        </div>
        <div style="grid-column: span 4;">
          <label>Técnico responsável</label>
          <input name="tecnico">
        </div>
        <div style="grid-column: span 4;">
          <label>Prazo (YYYY-MM-DD HH:MM)</label>
          <input name="prazo" placeholder="2025-09-30 18:00">
        </div>
        <div style="grid-column: span 4;">
          <label>Estimativa total (R$)</label>
          <input name="estimativa" placeholder="0 para usar peças + mão de obra">
        </div>
        <div style="grid-column: span 2;">
          <label>Peças (R$)</label>
          <input name="pecas" placeholder="0,00">
        </div>
        <div style="grid-column: span 2;">
          <label>Mão de obra (R$)</label>
          <input name="mao_obra" placeholder="0,00">
        </div>
        <div style="grid-column: span 12;">
          <label>Notas</label>
          <textarea name="notas" rows="3"></textarea>
        </div>
        <div style="grid-column: span 12;">
          <button type="submit">Criar OS</button>
          <a class="btn" href="{url_for('list_orders')}">Cancelar</a>
        </div>
      </form>
    </div>
    """
    return render_template_string(BASE, content=content)

@app.route("/ordens/<int:order_id>/editar", methods=["GET","POST"])
def edit_order(order_id):
    o = DATA["orders"].get(str(order_id))
    if not o:
        flash("OS não encontrada.")
        return redirect(url_for("list_orders"))

    clients = sorted(DATA["clients"].values(), key=lambda x: x["nome"].lower())

    if request.method == "POST":
        o["client_id"] = int(request.form.get("client_id"))
        o["status"] = request.form.get("status","Aberta")
        o["prioridade"] = request.form.get("prioridade","Média")
        o["descricao"] = request.form.get("descricao","").strip()
        o["tecnico"] = request.form.get("tecnico","").strip()
        o["prazo"] = request.form.get("prazo","").strip()
        o["estimativa"] = request.form.get("estimativa","")
        o["pecas"] = request.form.get("pecas","")
        o["mao_obra"] = request.form.get("mao_obra","")
        o["total"] = calc_total(o["estimativa"], o["pecas"], o["mao_obra"])
        o["notas"] = request.form.get("notas","").strip()
        save_data()
        flash("OS atualizada.")
        return redirect(url_for("list_orders"))

    client_options = "".join([f"<option value='{c['id']}' {'selected' if c['id']==o['client_id'] else ''}>{c['nome']}</option>" for c in clients])
    content = f"""
    <div class="panel">
      <h2>Editar OS #{o['id']}</h2>
      <form method="post" class="grid">
        <div style="grid-column: span 6;">
          <label>Cliente</label>
          <select name="client_id">{client_options}</select>
        </div>
        <div style="grid-column: span 3;">
          <label>Status</label>
          <select name="status">{''.join([f"<option {'selected' if o['status']==s else ''}>{s}</option>" for s in STATUSES])}</select>
        </div>
        <div style="grid-column: span 3;">
          <label>Prioridade</label>
          <select name="prioridade">{''.join([f"<option {'selected' if o['prioridade']==p else ''}>{p}</option>" for p in PRIORIDADES])}</select>
        </div>
        <div style="grid-column: span 8;">
          <label>Descrição</label>
          <textarea name="descricao" rows="3">{o.get('descricao','')}</textarea>
        </div>
        <div style="grid-column: span 4;">
          <label>Técnico</label>
          <input name="tecnico" value="{o.get('tecnico','')}">
        </div>
        <div style="grid-column: span 4;">
          <label>Prazo</label>
          <input name="prazo" value="{o.get('prazo','')}">
        </div>
        <div style="grid-column: span 4;">
          <label>Estimativa total (R$)</label>
          <input name="estimativa" value="{o.get('estimativa','')}">
        </div>
        <div style="grid-column: span 2;">
          <label>Peças (R$)</label>
          <input name="pecas" value="{o.get('pecas','')}">
        </div>
        <div style="grid-column: span 2;">
          <label>Mão de obra (R$)</label>
          <input name="mao_obra" value="{o.get('mao_obra','')}">
        </div>
        <div style="grid-column: span 12;">
          <label>Notas</label>
          <textarea name="notas" rows="3">{o.get('notas','')}</textarea>
        </div>
        <div style="grid-column: span 12;">
          <button type="submit">Salvar</button>
          <a class="btn" href="{url_for('list_orders')}">Cancelar</a>
        </div>
      </form>
    </div>
    """
    return render_template_string(BASE, content=content)

@app.route("/ordens/<int:order_id>/excluir", methods=["POST"])
def delete_order(order_id):
    oid = str(order_id)
    if oid in DATA["orders"]:
        del DATA["orders"][oid]
        save_data()
        flash("OS excluída.")
    else:
        flash("OS não encontrada.")
    return redirect(url_for("list_orders"))

@app.route("/ordens/<int:order_id>/imprimir")
def print_order(order_id):
    o = DATA["orders"].get(str(order_id))
    if not o:
        flash("OS não encontrada.")
        return redirect(url_for("list_orders"))
    c_nome = get_client_name(o["client_id"])
    cliente = DATA["clients"].get(str(o["client_id"]))
    doc = cliente.get("documento","") if cliente else ""
    tel = cliente.get("telefone","") if cliente else ""
    email = cliente.get("email","") if cliente else ""
    endereco = cliente.get("endereco","") if cliente else ""

    content = f"""
    <div class="printable">
      <h1>Ordem de Serviço #{o['id']}</h1>
      <p><strong>Data:</strong> {o.get('criado_em','')} &nbsp; <strong>Prazo:</strong> {o.get('prazo','')}</p>
      <hr>
      <h2>Cliente</h2>
      <p><strong>Nome:</strong> {c_nome}</p>
      <p><strong>Documento:</strong> {doc}</p>
      <p><strong>Telefone:</strong> {tel} &nbsp; <strong>Email:</strong> {email}</p>
      <p><strong>Endereço:</strong> {endereco}</p>
      <hr>
      <h2>Detalhes</h2>
      <p><strong>Status:</strong> {o.get('status','')} &nbsp; <strong>Prioridade:</strong> {o.get('prioridade','')}</p>
      <p><strong>Técnico:</strong> {o.get('tecnico','')}</p>
      <p><strong>Descrição:</strong><br>{o.get('descricao','').replace('\n','<br>')}</p>
      <p><strong>Notas:</strong><br>{o.get('notas','').replace('\n','<br>')}</p>
      <hr>
      <h2>Valores</h2>
      <p><strong>Estimativa:</strong> R$ {str(o.get('estimativa','0')).replace('.',',')}</p>
      <p><strong>Peças:</strong> R$ {str(o.get('pecas','0')).replace('.',',')} &nbsp; <strong>Mão de obra:</strong> R$ {str(o.get('mao_obra','0')).replace('.',',')}</p>
      <p><strong>Total:</strong> R$ {str(o.get('total','0')).replace('.',',')}</p>
      <hr>
      <p><em>Assinatura do cliente:</em> ________________________________</p>
      <p><em>Assinatura do responsável:</em> ____________________________</p>
      <p><a href="#" onclick="window.print(); return false;" class="btn">Imprimir</a> &nbsp;
         <a href="{url_for('list_orders')}" class="btn">Voltar</a></p>
    </div>
    """
    return render_template_string(BASE, content=content)

# -------------------------
# Execução
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)