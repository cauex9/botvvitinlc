import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[DB] Conectado ao Supabase com sucesso!")
    except Exception as e:
        print(f"[DB] Erro ao inicializar cliente Supabase: {e}")

# Arquivos locais de fallback caso o Supabase não esteja configurado
HISTORICO_FILE = 'historico.json'
SALDOS_FILE = 'saldos.json'
ESTOQUE_FILE = 'estoque.json'
TICKETS_FILE = 'tickets.json'



# ─────────────────────────────────────────────
# SALDOS
# ─────────────────────────────────────────────
def saldo_usuario(user_id: int) -> float:
    """Retorna o saldo interno do usuário."""
    if supabase:
        try:
            res = supabase.table("saldos").select("saldo").eq("user_id", user_id).execute()
            if res.data and len(res.data) > 0:
                return float(res.data[0]["saldo"])
            return 0.0
        except Exception as e:
            print(f"Erro ao consultar saldo no Supabase: {e}")
    
    # Fallback local
    if os.path.exists(SALDOS_FILE):
        try:
            with open(SALDOS_FILE, 'r', encoding='utf-8') as f:
                saldos = json.load(f)
                return float(saldos.get(str(user_id), 0))
        except Exception:
            pass
    return 0.0

def atualizar_saldo(user_id: int, novo_saldo: float):
    """Atualiza o saldo do usuário."""
    if supabase:
        try:
            now = datetime.now().isoformat()
            supabase.table("saldos").upsert({
                "user_id": user_id,
                "saldo": round(novo_saldo, 2),
                "updated_at": now
            }).execute()
            return
        except Exception as e:
            print(f"Erro ao atualizar saldo no Supabase: {e}")

    # Fallback local
    saldos = {}
    if os.path.exists(SALDOS_FILE):
        try:
            with open(SALDOS_FILE, 'r', encoding='utf-8') as f:
                saldos = json.load(f)
        except Exception:
            pass
    saldos[str(user_id)] = round(novo_saldo, 2)
    with open(SALDOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(saldos, f, indent=2)

def adicionar_saldo(user_id: int, valor: float) -> float:
    """Adiciona um valor ao saldo do usuário e retorna o novo saldo."""
    atual = saldo_usuario(user_id)
    novo = atual + valor
    atualizar_saldo(user_id, novo)
    return novo

def descontar_saldo(user_id: int, valor: float) -> bool:
    """Desconta um valor do saldo do usuário se houver saldo suficiente."""
    atual = saldo_usuario(user_id)
    if atual < valor:
        return False
    atualizar_saldo(user_id, atual - valor)
    return True


# ─────────────────────────────────────────────
# ESTOQUE
# ─────────────────────────────────────────────
def carregar_estoque() -> dict:
    """Retorna todo o estoque organizado por categoria: {'AMEX': ['cc1', 'cc2']}."""
    if supabase:
        try:
            res = supabase.table("estoque").select("categoria, conteudo").order("id").execute()
            estoque = {}
            if res.data:
                for row in res.data:
                    cat = row["categoria"].upper()
                    if cat not in estoque:
                        estoque[cat] = []
                    estoque[cat].append(row["conteudo"])
            return estoque
        except Exception as e:
            print(f"Erro ao carregar estoque do Supabase: {e}")

    # Fallback local
    if os.path.exists(ESTOQUE_FILE):
        try:
            with open(ESTOQUE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def obter_quantidade_estoque(categoria: str) -> int:
    """Retorna a quantidade de itens em estoque para a categoria."""
    categoria = categoria.upper()
    if supabase:
        try:
            res = supabase.table("estoque").select("id", count="exact").eq("categoria", categoria).execute()
            return res.count if res.count is not None else len(res.data or [])
        except Exception as e:
            print(f"Erro ao contar estoque no Supabase: {e}")

    estoque = carregar_estoque()
    item = estoque.get(categoria, [])
    return len(item) if isinstance(item, list) else int(item or 0)

def adicionar_cartoes_estoque(categoria: str, cartoes: list):
    """Adiciona cartões a uma categoria no estoque."""
    categoria = categoria.upper()
    if supabase:
        try:
            rows = [{"categoria": categoria, "conteudo": c} for c in cartoes if c.strip()]
            if rows:
                supabase.table("estoque").insert(rows).execute()
            return
        except Exception as e:
            print(f"Erro ao adicionar cartões no Supabase: {e}")

    # Fallback local
    estoque = carregar_estoque()
    if categoria not in estoque or not isinstance(estoque[categoria], list):
        estoque[categoria] = []
    estoque[categoria].extend(cartoes)
    with open(ESTOQUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(estoque, f, indent=2)

def retirar_cartao_estoque(categoria: str) -> str:
    """Retira 1 cartão da categoria no estoque e retorna o conteúdo do cartão."""
    categoria = categoria.upper()
    if supabase:
        try:
            res = supabase.table("estoque").select("id, conteudo").eq("categoria", categoria).order("id").limit(1).execute()
            if res.data and len(res.data) > 0:
                item_id = res.data[0]["id"]
                conteudo = res.data[0]["conteudo"]
                supabase.table("estoque").delete().eq("id", item_id).execute()
                return conteudo
            return None
        except Exception as e:
            print(f"Erro ao retirar cartão no Supabase: {e}")

    # Fallback local
    estoque = carregar_estoque()
    if categoria in estoque and isinstance(estoque[categoria], list) and len(estoque[categoria]) > 0:
        cartao = estoque[categoria].pop(0)
        with open(ESTOQUE_FILE, 'w', encoding='utf-8') as f:
            json.dump(estoque, f, indent=2)
        return cartao
    return None

def limpar_categoria_estoque(categoria: str) -> int:
    """Limpa uma categoria específica ou todo o estoque (categoria == 'TUDO')."""
    categoria = categoria.upper()
    if supabase:
        try:
            if categoria == "TUDO":
                supabase.table("estoque").delete().neq("id", 0).execute()
            else:
                supabase.table("estoque").delete().eq("categoria", categoria).execute()
            return True
        except Exception as e:
            print(f"Erro ao limpar categoria no Supabase: {e}")

    # Fallback local
    if categoria == "TUDO":
        estoque = {}
    else:
        estoque = carregar_estoque()
        if categoria in estoque:
            estoque[categoria] = []
    with open(ESTOQUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(estoque, f, indent=2)
    return True

def obter_cartoes_detalhados_categoria(categoria: str) -> list:
    """Retorna a lista de cartões da categoria especificada contendo o ID e conteúdo."""
    categoria = categoria.upper()
    if supabase:
        try:
            res = supabase.table("estoque").select("id, conteudo").eq("categoria", categoria).order("id").execute()
            if res.data:
                return res.data
            return []
        except Exception as e:
            print(f"Erro ao obter cartões detalhados no Supabase: {e}")

    # Fallback local
    estoque = carregar_estoque()
    itens = estoque.get(categoria, [])
    if isinstance(itens, list):
        return [{"id": idx + 1, "conteudo": c} for idx, c in enumerate(itens)]
    return []

def remover_cartao_por_indice(categoria: str, indice: int) -> tuple:
    """Remove um cartão pelo índice (1-indexed) da categoria. Retorna (sucesso, mensagem_ou_conteudo)."""
    categoria = categoria.upper()
    cartoes = obter_cartoes_detalhados_categoria(categoria)
    if not cartoes or indice < 1 or indice > len(cartoes):
        return False, "Índice inválido ou categoria sem cartões."

    item = cartoes[indice - 1]
    
    if supabase:
        try:
            item_id = item["id"]
            conteudo = item["conteudo"]
            supabase.table("estoque").delete().eq("id", item_id).execute()
            return True, conteudo
        except Exception as e:
            print(f"Erro ao remover cartão por índice no Supabase: {e}")
            return False, f"Erro no banco de dados: {e}"

    # Fallback local
    estoque = carregar_estoque()
    if categoria in estoque and isinstance(estoque[categoria], list):
        if 0 <= (indice - 1) < len(estoque[categoria]):
            removido = estoque[categoria].pop(indice - 1)
            with open(ESTOQUE_FILE, 'w', encoding='utf-8') as f:
                json.dump(estoque, f, indent=2)
            return True, removido

    return False, "Não foi possível remover o cartão."


# ─────────────────────────────────────────────
# TICKETS (CUPONS DE SALDO)
# ─────────────────────────────────────────────
def criar_ticket(codigo: str, valor: float) -> tuple:
    """Cria um novo ticket com o código e valor especificados."""
    codigo = codigo.strip().upper()
    if not codigo:
        return False, "Código de ticket inválido."
    if valor <= 0:
        return False, "O valor do ticket deve ser maior que zero."

    if supabase:
        try:
            res = supabase.table("tickets").select("id").eq("codigo", codigo).execute()
            if res.data and len(res.data) > 0:
                return False, f"Já existe um ticket com o código *{codigo}*!"
            
            supabase.table("tickets").insert({
                "codigo": codigo,
                "valor": round(valor, 2),
                "usado": False
            }).execute()
            return True, f"✅ Ticket *{codigo}* no valor de *R$ {valor:.2f}* foi criado com sucesso!"
        except Exception as e:
            print(f"Erro ao criar ticket no Supabase: {e}")
            return False, f"Erro ao salvar no banco de dados: {e}"

    # Fallback local
    tickets = {}
    if os.path.exists(TICKETS_FILE):
        try:
            with open(TICKETS_FILE, 'r', encoding='utf-8') as f:
                tickets = json.load(f)
        except Exception:
            pass

    if codigo in tickets:
        return False, f"Já existe um ticket com o código *{codigo}*!"

    tickets[codigo] = {
        "valor": round(valor, 2),
        "usado": False,
        "usado_por": None,
        "usado_em": None
    }

    with open(TICKETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tickets, f, indent=2)

    return True, f"✅ Ticket *{codigo}* no valor de *R$ {valor:.2f}* foi criado com sucesso!"

def resgatar_ticket(codigo: str, user_id: int) -> tuple:
    """Tenta resgatar um ticket para o usuário. Retorna (sucesso, mensagem, valor)."""
    codigo = codigo.strip().upper()
    now_iso = datetime.now().isoformat()
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    if supabase:
        try:
            res = supabase.table("tickets").select("*").eq("codigo", codigo).execute()
            if not res.data or len(res.data) == 0:
                return False, "❌ Ticket não encontrado ou código inválido!", 0.0
            
            t = res.data[0]
            if t.get("usado"):
                return False, "❌ Este ticket já foi resgatado por outra pessoa!", 0.0

            valor = float(t.get("valor", 0))

            # Atualiza ticket como usado no Supabase
            supabase.table("tickets").update({
                "usado": True,
                "usado_por": user_id,
                "usado_em": now_iso
            }).eq("id", t["id"]).execute()

            # Credita o saldo ao usuário
            adicionar_saldo(user_id, valor)
            return True, f"🎉 *Ticket resgatado com sucesso!*\n\n💰 *R$ {valor:.2f}* foram creditados na sua conta.", valor
        except Exception as e:
            print(f"Erro ao resgatar ticket no Supabase: {e}")
            return False, f"Erro ao processar resgate no banco de dados: {e}", 0.0

    # Fallback local
    if os.path.exists(TICKETS_FILE):
        try:
            with open(TICKETS_FILE, 'r', encoding='utf-8') as f:
                tickets = json.load(f)
        except Exception:
            tickets = {}
    else:
        tickets = {}

    if codigo not in tickets:
        return False, "❌ Ticket não encontrado ou código inválido!", 0.0

    t = tickets[codigo]
    if t.get("usado"):
        return False, "❌ Este ticket já foi resgatado por outra pessoa!", 0.0

    valor = float(t.get("valor", 0))
    t["usado"] = True
    t["usado_por"] = user_id
    t["usado_em"] = now_str

    with open(TICKETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tickets, f, indent=2)

    adicionar_saldo(user_id, valor)
    return True, f"🎉 *Ticket resgatado com sucesso!*\n\n💰 *R$ {valor:.2f}* foram creditados na sua conta.", valor



# ─────────────────────────────────────────────
# HISTÓRICO
# ─────────────────────────────────────────────
def obter_todos_usuarios() -> set:
    """Retorna um conjunto com todos os IDs de usuários únicos cadastrados no histórico e nos saldos."""
    usuarios = set()
    
    if supabase:
        try:
            res_h = supabase.table("historico").select("user_id").execute()
            if res_h.data:
                for row in res_h.data:
                    if row.get("user_id"):
                        usuarios.add(int(row["user_id"]))
        except Exception as e:
            print(f"Erro ao buscar usuarios do historico no Supabase: {e}")
            
        try:
            res_s = supabase.table("saldos").select("user_id").execute()
            if res_s.data:
                for row in res_s.data:
                    if row.get("user_id"):
                        usuarios.add(int(row["user_id"]))
        except Exception as e:
            print(f"Erro ao buscar usuarios dos saldos no Supabase: {e}")

    # Fallback local / complemento com arquivos JSON caso existam
    if os.path.exists(HISTORICO_FILE):
        try:
            with open(HISTORICO_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for ev in data:
                        if isinstance(ev, dict) and ev.get("user_id"):
                            usuarios.add(int(ev["user_id"]))
        except Exception:
            pass
            
    if os.path.exists(SALDOS_FILE):
        try:
            with open(SALDOS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for uid in data.keys():
                        try:
                            usuarios.add(int(uid))
                        except ValueError:
                            pass
        except Exception:
            pass

    return usuarios


def carregar_historico() -> list:
    """Carrega o histórico de eventos."""
    if supabase:
        try:
            res = supabase.table("historico").select("*").order("id").execute()
            if res.data:
                historico = []
                for row in res.data:
                    dt = row.get("created_at")
                    if dt:
                        try:
                            dt_obj = datetime.fromisoformat(dt.replace('Z', '+00:00'))
                            dt_str = dt_obj.strftime("%d/%m/%Y %H:%M:%S")
                        except Exception:
                            dt_str = str(dt)
                    else:
                        dt_str = ""
                    
                    historico.append({
                        "data": dt_str,
                        "user_id": row.get("user_id"),
                        "nome": row.get("nome") or "",
                        "username": row.get("username") or "",
                        "acao": row.get("acao") or "",
                        "detalhe": row.get("detalhe") or ""
                    })
                return historico
        except Exception as e:
            print(f"Erro ao carregar histórico no Supabase: {e}")

    # Fallback local
    if os.path.exists(HISTORICO_FILE):
        try:
            with open(HISTORICO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def registrar_evento(user_id: int, nome: str, username: str, acao: str, detalhe: str = ""):
    """Registra um novo evento no histórico."""
    uname = f"@{username}" if username and not username.startswith("@") else (username or "sem @")
    if supabase:
        try:
            supabase.table("historico").insert({
                "user_id": user_id,
                "nome": nome,
                "username": uname,
                "acao": acao,
                "detalhe": detalhe
            }).execute()
            return
        except Exception as e:
            print(f"Erro ao registrar evento no Supabase: {e}")

    # Fallback local
    historico = carregar_historico()
    evento = {
        "data": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "user_id": user_id,
        "nome": nome,
        "username": uname,
        "acao": acao,
        "detalhe": detalhe
    }
    historico.append(evento)
    with open(HISTORICO_FILE, 'w', encoding='utf-8') as f:
        json.dump(historico, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────────
# MIGRAÇÃO AUTOMÁTICA DE JSON LOCAL -> SUPABASE
# ─────────────────────────────────────────────
def migrar_dados_locais():
    """Migra dados de saldos.json, estoque.json e historico.json para o Supabase se existirem."""
    if not supabase:
        return

    # 1. Migrar Saldos
    if os.path.exists(SALDOS_FILE):
        try:
            with open(SALDOS_FILE, 'r', encoding='utf-8') as f:
                saldos = json.load(f)
                if isinstance(saldos, dict):
                    rows = []
                    for uid, sal in saldos.items():
                        rows.append({
                            "user_id": int(uid),
                            "saldo": float(sal)
                        })
                    if rows:
                        supabase.table("saldos").upsert(rows).execute()
                        print(f"[DB] Migrados {len(rows)} saldos para o Supabase.")
            os.rename(SALDOS_FILE, SALDOS_FILE + ".bak")
        except Exception as e:
            print(f"[DB] Erro ao migrar saldos.json: {e}")

    # 2. Migrar Estoque
    if os.path.exists(ESTOQUE_FILE):
        try:
            with open(ESTOQUE_FILE, 'r', encoding='utf-8') as f:
                estoque = json.load(f)
                if isinstance(estoque, dict):
                    rows = []
                    for cat, itens in estoque.items():
                        if isinstance(itens, list):
                            for item in itens:
                                rows.append({"categoria": cat.upper(), "conteudo": item})
                    if rows:
                        supabase.table("estoque").insert(rows).execute()
                        print(f"[DB] Migrados {len(rows)} itens de estoque para o Supabase.")
            os.rename(ESTOQUE_FILE, ESTOQUE_FILE + ".bak")
        except Exception as e:
            print(f"[DB] Erro ao migrar estoque.json: {e}")

    # 3. Migrar Histórico
    if os.path.exists(HISTORICO_FILE):
        try:
            with open(HISTORICO_FILE, 'r', encoding='utf-8') as f:
                historico = json.load(f)
                if isinstance(historico, list):
                    rows = []
                    for ev in historico:
                        rows.append({
                            "user_id": ev.get("user_id"),
                            "nome": ev.get("nome"),
                            "username": ev.get("username"),
                            "acao": ev.get("acao"),
                            "detalhe": ev.get("detalhe", "")
                        })
                    if rows:
                        supabase.table("historico").insert(rows).execute()
                        print(f"[DB] Migrados {len(rows)} eventos de histórico para o Supabase.")
            os.rename(HISTORICO_FILE, HISTORICO_FILE + ".bak")
        except Exception as e:
            print(f"[DB] Erro ao migrar historico.json: {e}")


# Executa a migração caso o Supabase esteja disponível
if supabase:
    try:
        migrar_dados_locais()
    except Exception as e:
        print(f"[DB] Não foi possível realizar a migração inicial: {e}")
