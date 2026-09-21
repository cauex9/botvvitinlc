import telebot
import requests
import uuid
import re
import json
import os
import db
from dotenv import load_dotenv
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ─────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────
load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
PUBLIC_KEY = os.getenv('POSEIDON_PUBLIC_KEY')
SECRET_KEY = os.getenv('POSEIDON_SECRET_KEY')

credenciais_faltantes = [
    nome for nome, valor in {
        'TELEGRAM_BOT_TOKEN': TOKEN,
        'POSEIDON_PUBLIC_KEY': PUBLIC_KEY,
        'POSEIDON_SECRET_KEY': SECRET_KEY,
    }.items() if not valor
]
if credenciais_faltantes:
    raise RuntimeError(
        'Configure no arquivo .env: ' + ', '.join(credenciais_faltantes)
    )

DONO_ID = 8241738977      # <-- ID do dono no Telegram
DONO_CHAT_ID  = None                    # <-- preenchido automaticamente quando o dono usar /start

POSEIDON_URL = 'https://app.poseidonpay.site/api/v1/gateway/pix/receive'

bot = telebot.TeleBot(TOKEN)

# ─────────────────────────────────────────────
# ESTADO DE CONVERSA (em memória)
# ─────────────────────────────────────────────
user_state = {}

# ─────────────────────────────────────────────
# SISTEMA DE BANCO DE DADOS (SUPABASE / FALLBACK)
# ─────────────────────────────────────────────
def saldo_usuario(user_id: int) -> float:
    return db.saldo_usuario(user_id)

def carregar_historico() -> list:
    return db.carregar_historico()

def obter_todos_usuarios() -> set:
    return db.obter_todos_usuarios()

def registrar_evento(user_id: int, nome: str, username: str, acao: str, detalhe: str = ""):
    db.registrar_evento(user_id, nome, username, acao, detalhe)

def notificar_dono(texto: str):
    """Envia notificação para o dono do bot."""
    global DONO_CHAT_ID
    if DONO_CHAT_ID:
        try:
            bot.send_message(DONO_CHAT_ID, texto, parse_mode="Markdown")
        except Exception:
            pass



# ─────────────────────────────────────────────
# MENUS
# ─────────────────────────────────────────────
def menu_principal(username=""):
    markup = InlineKeyboardMarkup()
    btn_comprar = InlineKeyboardButton("💳 Comprar CC", callback_data="comprar")
    btn_conta   = InlineKeyboardButton("👤 Minha conta", callback_data="conta")
    btn_saldo   = InlineKeyboardButton("💰 Adicionar saldo", callback_data="saldo")
    btn_ticket  = InlineKeyboardButton("🎟️ Resgatar Ticket", callback_data="resgatar_ticket")
    btn_dono    = InlineKeyboardButton("👑 Dono", url=f"tg://user?id={DONO_ID}")
    markup.add(btn_comprar)
    markup.row(btn_conta, btn_saldo)
    markup.add(btn_ticket)
    markup.add(btn_dono)

    return markup

def menu_produtos():
    markup = InlineKeyboardMarkup()
    produtos = [
        ("AMEX | R$ 30",          "prod_AMEX|30"),
        ("B2B | R$ 20",           "prod_B2B|20"),
        ("BLACK | R$ 30",         "prod_BLACK|30"),
        ("BUSINESS | R$ 20",      "prod_BUSINESS|20"),
        ("CLASSIC | R$ 15",       "prod_CLASSIC|15"),
        ("CORPORATE | R$ 30",     "prod_CORPORATE|30"),
        ("ELECTRON | R$ 20",      "prod_ELECTRON|20"),
        ("ELO | R$ 40",           "prod_ELO|40"),
        ("GOLD | R$ 15",          "prod_GOLD|15"),
        ("INDEFINIDO | R$ 20",    "prod_INDEFINIDO|20"),
        ("INFINITE | R$ 30",      "prod_INFINITE|30"),
        ("NUBA GOLD | R$ 15",     "prod_NUBAGOLD|15"),
        ("NUBA PLATINUM | R$ 20", "prod_NUBAPLATINUM|20"),
        ("PLATINUM | R$ 25",      "prod_PLATINUM|25"),
        ("PREPAID | R$ 29",       "prod_PREPAID|29"),
        ("SIGNATURE | R$ 20",     "prod_SIGNATURE|20"),
        ("STANDARD | R$ 15",      "prod_STANDARD|15"),
        ("TRAD REWARDS | R$ 20",  "prod_TRADREWARDS|20"),
        ("WORLD | R$ 20",         "prod_WORLD|20"),
    ]
    botoes = [InlineKeyboardButton(t, callback_data=d) for t, d in produtos]
    for i in range(0, len(botoes), 2):
        if i + 1 < len(botoes):
            markup.row(botoes[i], botoes[i+1])
        else:
            markup.add(botoes[i])
    markup.add(InlineKeyboardButton("💰 Adicionar saldo", callback_data="saldo"))
    markup.add(InlineKeyboardButton("⬅️ Voltar", callback_data="voltar"))
    return markup

def menu_adm():
    markup = InlineKeyboardMarkup()
    btn_saldo = InlineKeyboardButton("💼 Saldo API", callback_data="adm_saldo")
    btn_hist  = InlineKeyboardButton("📋 Histórico", callback_data="adm_hist")
    btn_add_cc = InlineKeyboardButton("➕ Add Cartão", callback_data="adm_add_cc")
    btn_rem_cc = InlineKeyboardButton("📦 Estoque / Remover CC", callback_data="adm_rem_cc")
    btn_ticket = InlineKeyboardButton("🎟️ Criar Ticket", callback_data="adm_criar_ticket")
    btn_voltar = InlineKeyboardButton("⬅️ Voltar", callback_data="voltar")
    markup.row(btn_saldo, btn_hist)
    markup.row(btn_add_cc, btn_rem_cc)
    markup.add(btn_ticket)
    markup.add(btn_voltar)
    return markup

def menu_categorias_estoque():
    markup = InlineKeyboardMarkup()
    categorias = [
        "AMEX", "B2B", "BLACK", "BUSINESS", "CLASSIC", "CORPORATE",
        "ELECTRON", "ELO", "GOLD", "INDEFINIDO", "INFINITE", "NUBA GOLD",
        "NUBA PLATINUM", "PLATINUM", "PREPAID", "SIGNATURE", "STANDARD",
        "TRAD REWARDS", "WORLD"
    ]
    botoes = []
    for cat in categorias:
        qtd = db.obter_quantidade_estoque(cat)
        cat_clean = cat.replace(" ", "")
        botoes.append(InlineKeyboardButton(f"{cat} ({qtd})", callback_data=f"adm_cat_rem_{cat_clean}"))
        
    for i in range(0, len(botoes), 2):
        if i + 1 < len(botoes):
            markup.row(botoes[i], botoes[i+1])
        else:
            markup.add(botoes[i])
            
    markup.add(InlineKeyboardButton("⬅️ Voltar ao ADM", callback_data="adm_voltar_menu"))
    return markup


# ─────────────────────────────────────────────
# INTEGRAÇÃO API - SALDO DO PRODUTOR
# ─────────────────────────────────────────────
POSEIDON_BALANCE_URL = 'https://app.poseidonpay.site/api/v1/gateway/producer/balance'

def consultar_saldo() -> dict:
    """Consulta o saldo atual da conta do produtor na PoseidonPay."""
    headers = {
        'x-public-key': PUBLIC_KEY,
        'x-secret-key': SECRET_KEY,
        'Content-Type': 'application/json'
    }
    try:
        resp = requests.get(POSEIDON_BALANCE_URL, headers=headers, timeout=10)
        return resp.json()
    except requests.exceptions.Timeout:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}

import random

def gerar_cpf_valido():
    cpf = [random.randint(0, 9) for _ in range(9)]
    for _ in range(2):
        val = sum([(len(cpf) + 1 - i) * v for i, v in enumerate(cpf)]) % 11
        cpf.append(11 - val if val > 1 else 0)
    return ''.join(map(str, cpf))

# ─────────────────────────────────────────────
# INTEGRAÇÃO PIX - POSEIDONPAY
# ─────────────────────────────────────────────
def gerar_pix(valor: float, user_id: int, user_name: str) -> dict:
    """Chama a API da PoseidonPay e retorna o resultado."""
    headers = {
        'x-public-key': PUBLIC_KEY,
        'x-secret-key': SECRET_KEY,
        'Content-Type': 'application/json'
    }
    body = {
        "identifier": str(uuid.uuid4()),
        "amount": valor,
        "client": {
            "name":  user_name or f"Usuario_{user_id}",
            "email": f"user{user_id}@telegram.com",
            "phone": "(11) 99999-9999",
            "document": gerar_cpf_valido()
        },
        "metadata": {
            "provider": "TelegramBot",
            "orderId":  str(user_id)
        }
    }
    try:
        resp = requests.post(POSEIDON_URL, json=body, headers=headers, timeout=15)
        return resp.json()
    except requests.exceptions.Timeout:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)}

def enviar_pix_ao_usuario(chat_id: int, valor: float, resultado: dict):
    """Envia o QR Code e código Pix ao usuário após geração."""
    if resultado.get("status") in ("OK", "PENDING"):
        pix   = resultado.get("pix", {})
        code  = pix.get("code", "")
        image = pix.get("image", "")

        texto = (
            f"✅ *Cobrança Pix gerada com sucesso!*\n\n"
            f"💰 *Valor:* R$ {valor:.2f}\n\n"
            f"📋 *Copia e Cola:*\n`{code}`\n\n"
            f"_Após o pagamento seu saldo será creditado automaticamente._"
        )

        if image:
            try:
                bot.send_photo(chat_id, image, caption=texto, parse_mode="Markdown")
            except Exception:
                bot.send_message(chat_id, texto, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, texto, parse_mode="Markdown")

    elif resultado.get("error"):
        bot.send_message(
            chat_id,
            f"❌ Erro ao conectar com a API: `{resultado['error']}`\nTente novamente mais tarde.",
            parse_mode="Markdown"
        )
    else:
        # Pega toda a resposta para debug
        raw_resp = str(resultado)
        bot.send_message(chat_id, f"❌ Falha ao gerar Pix. Resposta da API:\n`{raw_resp}`", parse_mode="Markdown")

# ─────────────────────────────────────────────
# HANDLERS DE MENSAGEM
# ─────────────────────────────────────────────
@bot.message_handler(commands=['start'])
def send_welcome(message):
    global DONO_CHAT_ID
    user  = message.from_user
    nome  = user.first_name or "Usuário"
    uname = user.username or ""

    # Captura automaticamente o chat_id do dono
    if user.id == DONO_ID:
        DONO_CHAT_ID = message.chat.id

    user_state.pop(message.chat.id, None)

    # Registra no histórico
    registrar_evento(user.id, nome, uname, "entrou no bot")

    # Notifica o dono
    notificar_dono(
        f"🔔 *Novo usuário no bot!*\n\n"
        f"👤 Nome: {nome}\n"
        f"🆔 ID: `{user.id}`\n"
        f"📱 Username: @{uname if uname else 'sem @'}\n"
        f"🕐 Horário: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    )

    bot.send_message(
        message.chat.id,
        f"👋 Olá, *{nome}*! Bem-vindo. Escolha uma opção abaixo:",
        reply_markup=menu_principal(uname),
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['adm'])
def cmd_adm(message):
    """Comando exclusivo do dono para abrir o Painel ADM."""
    if message.from_user.id != DONO_ID:
        bot.send_message(message.chat.id, "❌ Você não tem permissão para usar este comando.")
        return
    bot.send_message(
        message.chat.id,
        "🛠️ *Painel do Administrador*\n\nEscolha uma opção:",
        parse_mode="Markdown",
        reply_markup=menu_adm()
    )

@bot.message_handler(commands=['aviso'])
def cmd_aviso(message):
    """Comando exclusivo do dono para enviar mensagem para todos os usuários."""
    import time
    if message.from_user.id != DONO_ID:
        bot.send_message(message.chat.id, "❌ Você não tem permissão para usar este comando.")
        return
        
    partes = message.text.split(maxsplit=1)
    if len(partes) < 2 or not partes[1].strip():
        bot.send_message(message.chat.id, "⚠️ Uso correto: `/aviso sua mensagem aqui`", parse_mode="Markdown")
        return
        
    texto = partes[1].strip()
    usuarios = obter_todos_usuarios()
    
    if not usuarios:
        bot.send_message(message.chat.id, "⚠️ Nenhum usuário encontrado no histórico ou banco de dados.")
        return
        
    enviados = 0
    falhas = 0
    msg_wait = bot.send_message(message.chat.id, f"⏳ Enviando aviso para {len(usuarios)} usuários...")
    
    for uid in usuarios:
        try:
            bot.send_message(uid, f"📢 *Aviso do Administrador:*\n\n{texto}", parse_mode="Markdown")
            enviados += 1
        except Exception:
            try:
                # Tenta enviar como texto puro se o Markdown falhar por causa de caracteres especiais (ex: _, *, `, [)
                bot.send_message(uid, f"📢 Aviso do Administrador:\n\n{texto}")
                enviados += 1
            except Exception:
                falhas += 1
        time.sleep(0.04)  # Evita bloqueio por limite de taxa do Telegram (rate limit)
            
    bot.edit_message_text(
        f"✅ *Aviso enviado!*\n\n"
        f"Sucesso: `{enviados}`\n"
        f"Falhas: `{falhas}` (bloquearam o bot)",
        chat_id=message.chat.id,
        message_id=msg_wait.message_id,
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['historico'])
def cmd_historico(message):
    """Comando exclusivo do dono para ver o histórico de usuários."""
    if message.from_user.id != DONO_ID:
        bot.send_message(message.chat.id, "❌ Você não tem permissão para usar este comando.")
        return

    historico = carregar_historico()
    if not historico:
        bot.send_message(message.chat.id, "📋 Histórico vazio.")
        return

    # Mostra os últimos 20 eventos
    ultimos = historico[-20:]
    linhas = ["📋 *Histórico (últimos eventos):*\n"]
    for ev in reversed(ultimos):
        linhas.append(
            f"🕐 `{ev['data']}`\n"
            f"👤 {ev['nome']} ({ev['username']}) — ID: `{ev['user_id']}`\n"
            f"📌 *{ev['acao']}*" + (f": {ev['detalhe']}" if ev['detalhe'] else "") + "\n"
        )

    texto = "\n".join(linhas)

    # Telegram tem limite de 4096 chars por mensagem
    if len(texto) > 4000:
        texto = texto[:4000] + "\n\n_...lista truncada_"

    bot.send_message(message.chat.id, texto, parse_mode="Markdown")


@bot.message_handler(commands=['meusaldo'])
def cmd_meu_saldo(message):
    """Comando exclusivo do dono para checar o saldo na PoseidonPay."""
    if message.from_user.id != DONO_ID:
        bot.send_message(message.chat.id, "❌ Você não tem permissão para usar este comando.")
        return

    msg_wait = bot.send_message(message.chat.id, "⏳ Consultando saldo, aguarde...")
    dados = consultar_saldo()
    try:
        bot.delete_message(message.chat.id, msg_wait.message_id)
    except Exception:
        pass

    if dados.get("error"):
        bot.send_message(
            message.chat.id,
            f"❌ Erro ao consultar saldo: `{dados['error']}`",
            parse_mode="Markdown"
        )
    else:
        disponivel = dados.get("available", 0)
        pendente   = dados.get("pending", 0)
        retido     = dados.get("fundLock", 0)
        bot.send_message(
            message.chat.id,
            f"💼 *Saldo PoseidonPay*\n\n"
            f"💰 *Disponível:* R$ {disponivel:.2f}\n"
            f"⏳ *Pendente:* R$ {pendente:.2f}\n"
            f"🔒 *Retido:* R$ {retido:.2f}",
            parse_mode="Markdown"
        )

@bot.message_handler(commands=['criarticket'])
def cmd_criar_ticket(message):
    """Comando exclusivo do dono para criar um ticket de saldo."""
    if message.from_user.id != DONO_ID:
        bot.send_message(message.chat.id, "❌ Você não tem permissão para usar este comando.")
        return
        
    partes = message.text.split()
    if len(partes) < 3:
        bot.send_message(message.chat.id, "⚠️ Uso correto: `/criarticket CODIGO VALOR` (ex: `/criarticket PROMO10 15`)", parse_mode="Markdown")
        return
        
    codigo = partes[1].strip()
    try:
        valor = float(partes[2].replace(',', '.'))
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ Valor inválido. Digite apenas números para o valor. Ex: `15` ou `29.90`", parse_mode="Markdown")
        return
        
    ok, msg = db.criar_ticket(codigo, valor)
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")

@bot.message_handler(commands=['resgatar'])
def cmd_resgatar(message):
    """Comando para o usuário resgatar um ticket de saldo."""
    partes = message.text.split()
    if len(partes) < 2:
        bot.send_message(message.chat.id, "⚠️ Uso correto: `/resgatar CODIGO` (ex: `/resgatar PROMO10`)", parse_mode="Markdown")
        return
        
    codigo = partes[1].strip()
    user = message.from_user
    ok, msg, valor = db.resgatar_ticket(codigo, user.id)
    
    if ok:
        registrar_evento(user.id, user.first_name or "Usuário", user.username or "", "resgatou ticket", f"{codigo.upper()} (R$ {valor:.2f})")
        notificar_dono(
            f"🎟️ *Ticket Resgatado!*\n\n"
            f"👤 Nome: {user.first_name}\n"
            f"📱 Username: @{user.username if user.username else 'sem @'}\n"
            f"🆔 ID: `{user.id}`\n"
            f"🎟️ Ticket: `{codigo.upper()}`\n"
            f"💵 Valor: R$ {valor:.2f}"
        )
        
    bot.send_message(message.chat.id, msg, parse_mode="Markdown")


@bot.message_handler(func=lambda m: True)
def handle_text(message):
    chat_id = message.chat.id
    estado  = user_state.get(chat_id)

    if estado == "aguardando_dados_ticket":
        partes = message.text.split()
        if len(partes) < 2:
            bot.send_message(chat_id, "⚠️ Formato inválido! Envie o código e o valor. Exemplo: `PROMO10 15`", parse_mode="Markdown")
            return
        codigo = partes[0].strip()
        try:
            valor = float(partes[1].replace(',', '.'))
        except ValueError:
            bot.send_message(chat_id, "⚠️ Valor inválido. Digite apenas números. Ex: `15` ou `29.90`", parse_mode="Markdown")
            return
            
        ok, msg = db.criar_ticket(codigo, valor)
        user_state.pop(chat_id, None)
        bot.send_message(chat_id, msg, parse_mode="Markdown")
        return

    if estado == "aguardando_codigo_ticket":
        codigo = message.text.strip()
        user = message.from_user
        ok, msg, valor = db.resgatar_ticket(codigo, user.id)
        user_state.pop(chat_id, None)
        
        if ok:
            registrar_evento(user.id, user.first_name or "Usuário", user.username or "", "resgatou ticket", f"{codigo.upper()} (R$ {valor:.2f})")
            notificar_dono(
                f"🎟️ *Ticket Resgatado!*\n\n"
                f"👤 Nome: {user.first_name}\n"
                f"📱 Username: @{user.username if user.username else 'sem @'}\n"
                f"🆔 ID: `{user.id}`\n"
                f"🎟️ Ticket: `{codigo.upper()}`\n"
                f"💵 Valor: R$ {valor:.2f}"
            )
            
        bot.send_message(chat_id, msg, parse_mode="Markdown")
        return

    if type(estado) is dict and estado.get("estado") == "aguardando_rem_cartao_indice":
        cat = estado["categoria"]
        texto = message.text.strip().upper()
        
        if texto == "TUDO":
            db.limpar_categoria_estoque(cat)
            user_state.pop(chat_id, None)
            bot.send_message(chat_id, f"✅ Todo o estoque da categoria *{cat}* foi zerado!", parse_mode="Markdown")
            return
            
        try:
            idx = int(texto)
        except ValueError:
            bot.send_message(chat_id, "⚠️ Digite o NÚMERO do cartão que deseja remover (ex: `1`) ou `TUDO`.", parse_mode="Markdown")
            return
            
        ok, removido = db.remover_cartao_por_indice(cat, idx)
        user_state.pop(chat_id, None)
        if ok:
            bot.send_message(chat_id, f"✅ Cartão #{idx} removido da categoria *{cat}*:\n`{removido}`", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"❌ Erro: {removido}", parse_mode="Markdown")
        return

    if estado == "aguardando_cat_add":

        cat = message.text.strip().upper()
        user_state[chat_id] = {"estado": "aguardando_ccs_add", "categoria": cat}
        bot.send_message(
            chat_id,
            f"Categoria selecionada: *{cat}*\n"
            "Agora envie vários cartões na mesma mensagem, separados por nova linha, vírgula ou ponto e vírgula.",
            parse_mode="Markdown"
        )
        return

    if type(estado) is dict and estado.get("estado") == "aguardando_ccs_add":
        cat = estado["categoria"]
        linhas = [item.strip() for item in re.split(r"[\n,;]+", message.text) if item.strip()]
        
        db.adicionar_cartoes_estoque(cat, linhas)
            
        user_state.pop(chat_id, None)
        bot.send_message(chat_id, f"✅ Adicionados {len(linhas)} cartões à categoria *{cat}*!", parse_mode="Markdown")
        return

    if estado == "aguardando_cat_rem":
        cat = message.text.strip().upper()
        db.limpar_categoria_estoque(cat)
        if cat == "TUDO":
            bot.send_message(chat_id, "✅ Todo o estoque foi zerado!", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, f"✅ A categoria *{cat}* foi limpa!", parse_mode="Markdown")
            
        user_state.pop(chat_id, None)
        return

    if estado == "aguardando_valor_saldo":
        texto = re.sub(r'[^\d.,]', '', message.text.strip()).replace(',', '.')
        try:
            valor = float(texto)
            if valor <= 0:
                raise ValueError("zero")
        except ValueError:
            bot.send_message(chat_id, "⚠️ Valor inválido. Digite apenas números. Ex: *50* ou *29.90*", parse_mode="Markdown")
            return

        if valor < 15:
            bot.send_message(chat_id, "⚠️ O valor mínimo para adicionar saldo é *R$ 15,00*.", parse_mode="Markdown")
            return

        user_state.pop(chat_id, None)

        nome = message.from_user.first_name or "Usuário"
        uname = message.from_user.username or ""
        msg_aguarde = bot.send_message(chat_id, "⏳ Gerando seu Pix, aguarde...")

        resultado = gerar_pix(valor, chat_id, nome)

        try:
            bot.delete_message(chat_id, msg_aguarde.message_id)
        except Exception:
            pass

        # Registra no histórico e notifica o dono
        if resultado.get("status") in ("OK", "PENDING"):
            registrar_evento(chat_id, nome, uname, "gerou Pix", f"R$ {valor:.2f}")
            notificar_dono(
                f"💰 *Novo Pix gerado!*\n\n"
                f"👤 Nome: {nome}\n"
                f"📱 Username: @{uname if uname else 'sem @'}\n"
                f"🆔 ID: `{chat_id}`\n"
                f"💵 Valor: R$ {valor:.2f}\n"
                f"🕐 Horário: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            )
        else:
            registrar_evento(chat_id, nome, uname, "falha ao gerar Pix", f"R$ {valor:.2f}")

        enviar_pix_ao_usuario(chat_id, valor, resultado)
        bot.send_message(chat_id, "Menu principal:", reply_markup=menu_principal(message.from_user.username or ""))

# ─────────────────────────────────────────────
# CALLBACKS DOS BOTÕES
# ─────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    uname = call.from_user.username or ""

    if call.data == "comprar":
        tabela = (
            "💳 *Produtos disponíveis:*\n\n"
            "```\n"
            "Tipo           | Valor \n"
            "---------------+-------\n"
            "AMEX           | R$ 30 \n"
            "B2B            | R$ 20 \n"
            "BLACK          | R$ 30 \n"
            "BUSINESS       | R$ 20 \n"
            "CLASSIC        | R$ 15 \n"
            "CORPORATE      | R$ 30 \n"
            "ELECTRON       | R$ 20 \n"
            "ELO            | R$ 40 \n"
            "GOLD           | R$ 15 \n"
            "INDEFINIDO     | R$ 20 \n"
            "INFINITE       | R$ 30 \n"
            "NUBA GOLD      | R$ 15 \n"
            "NUBA PLATINUM  | R$ 20 \n"
            "PLATINUM       | R$ 25 \n"
            "PREPAID        | R$ 29 \n"
            "SIGNATURE      | R$ 20 \n"
            "STANDARD       | R$ 15 \n"
            "TRAD REWARDS   | R$ 20 \n"
            "WORLD          | R$ 20 \n"
            "```\n\n"
            "Selecione o tipo de cartão abaixo:"
        )
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=tabela,
            parse_mode="Markdown",
            reply_markup=menu_produtos()
        )

    elif call.data == "voltar":
        user_state.pop(chat_id, None)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="👋 Olá! Bem-vindo. Escolha uma opção abaixo:",
            reply_markup=menu_principal(uname)
        )



    elif call.data == "adm_saldo":
        if call.from_user.id != DONO_ID:
            return
        bot.answer_callback_query(call.id, "Consultando saldo...")
        dados = consultar_saldo()
        if dados.get("error"):
            texto = f"❌ Erro: `{dados['error']}`"
        else:
            disponivel = dados.get("available", 0)
            pendente   = dados.get("pending", 0)
            retido     = dados.get("fundLock", 0)
            texto = (
                f"💼 *Saldo PoseidonPay*\n\n"
                f"💰 *Disponível:* R$ {disponivel:.2f}\n"
                f"⏳ *Pendente:* R$ {pendente:.2f}\n"
                f"🔒 *Retido:* R$ {retido:.2f}"
            )
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=texto,
            parse_mode="Markdown",
            reply_markup=menu_adm()
        )

    elif call.data == "adm_hist":
        if call.from_user.id != DONO_ID:
            return
        bot.answer_callback_query(call.id)
        historico = carregar_historico()
        if not historico:
            texto = "📋 Histórico vazio."
        else:
            ultimos = historico[-15:]
            linhas = ["📋 *Últimos eventos:*\n"]
            for ev in reversed(ultimos):
                linhas.append(
                    f"🕐 `{ev['data']}` | 👤 {ev['nome']} | 📌 {ev['acao']} {ev['detalhe']}"
                )
            texto = "\n".join(linhas)
            if len(texto) > 4000:
                texto = texto[:4000] + "\n..."
        
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=texto,
            parse_mode="Markdown",
            reply_markup=menu_adm()
        )

    elif call.data == "adm_add_cc":
        if call.from_user.id != DONO_ID:
            return
        user_state[chat_id] = "aguardando_cat_add"
        bot.answer_callback_query(call.id)
        bot.send_message(
            chat_id,
            "➕ *Adicionar Cartões*\n\n"
            "Digite a Categoria do cartão que deseja adicionar.\n"
            "Exemplo: *AMEX*",
            parse_mode="Markdown"
        )

    elif call.data == "adm_rem_cc":
        if call.from_user.id != DONO_ID:
            return
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="📦 *Estoque por Categoria*\nSelecione a categoria para visualizar os cartões e remover:",
            parse_mode="Markdown",
            reply_markup=menu_categorias_estoque()
        )

    elif call.data == "adm_voltar_menu":
        if call.from_user.id != DONO_ID:
            return
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text="🛠️ *Painel do Administrador*\n\nEscolha uma opção:",
            parse_mode="Markdown",
            reply_markup=menu_adm()
        )

    elif call.data == "adm_criar_ticket":
        if call.from_user.id != DONO_ID:
            return
        user_state[chat_id] = "aguardando_dados_ticket"
        bot.answer_callback_query(call.id)
        bot.send_message(
            chat_id,
            "🎟️ *Criar Novo Ticket de Saldo*\n\n"
            "Digite o código do ticket e o valor separados por espaço.\n"
            "Exemplo: `PROMO10 15` ou `BEMVINDO 20.00`\n\n"
            "_Dica: Você também pode usar o comando /criarticket CODIGO VALOR_",
            parse_mode="Markdown"
        )

    elif call.data == "resgatar_ticket":
        user_state[chat_id] = "aguardando_codigo_ticket"
        bot.answer_callback_query(call.id)
        bot.send_message(
            chat_id,
            "🎟️ *Resgatar Ticket de Saldo*\n\n"
            "Digite o código do seu ticket para resgatar o saldo.\n"
            "Exemplo: `PROMO10`\n\n"
            "_Dica: Você também pode usar o comando /resgatar SEUCODIGO_",
            parse_mode="Markdown"
        )

    elif call.data.startswith("adm_cat_rem_"):
        if call.from_user.id != DONO_ID:
            return
        cat_clean = call.data.replace("adm_cat_rem_", "")
        mapa_cats = {
            "NUBAGOLD": "NUBA GOLD",
            "NUBAPLATINUM": "NUBA PLATINUM",
            "TRADREWARDS": "TRAD REWARDS"
        }
        cat = mapa_cats.get(cat_clean, cat_clean)
        
        cartoes = db.obter_cartoes_detalhados_categoria(cat)
        bot.answer_callback_query(call.id)
        
        if not cartoes:
            bot.send_message(chat_id, f"⚠️ A categoria *{cat}* está vazia no momento!", parse_mode="Markdown")
            return
            
        linhas = [f"📦 *Estoque da categoria {cat}* (Total: {len(cartoes)}):\n"]
        for idx, c in enumerate(cartoes, 1):
            linhas.append(f"`{idx}.` `{c['conteudo']}`")
            
        linhas.append("\n📌 *Como remover:*")
        linhas.append("• Digite o *número* do cartão que deseja remover (ex: `1` para o primeiro).")
        linhas.append("• Digite *TUDO* para apagar todos os cartões desta categoria.")
        
        texto = "\n".join(linhas)
        if len(texto) > 4000:
            texto = texto[:4000] + "\n\n_...lista truncada_"
            
        user_state[chat_id] = {"estado": "aguardando_rem_cartao_indice", "categoria": cat}
        bot.send_message(chat_id, texto, parse_mode="Markdown")


    elif call.data == "saldo":
        user_state[chat_id] = "aguardando_valor_saldo"
        bot.answer_callback_query(call.id)
        bot.send_message(
            chat_id,
            "💰 *Adicionar Saldo via Pix*\n\n"
            "Digite o valor que deseja adicionar (em reais):\n"
            "Valor mínimo: *R$ 15,00*\n"
            "Exemplo: `50` ou `29.90`",
            parse_mode="Markdown"
        )

    elif call.data == "conta":
        bot.answer_callback_query(call.id)
        user_id = call.from_user.id
        nome = call.from_user.first_name or "Usuário"
        uname = call.from_user.username or ""
        saldo = saldo_usuario(user_id)

        uname_clean = uname.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`') if uname else "sem @"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💰 Adicionar saldo", callback_data="saldo"))
        markup.add(InlineKeyboardButton("🎟️ Resgatar Ticket", callback_data="resgatar_ticket"))
        markup.add(InlineKeyboardButton("⬅️ Voltar", callback_data="voltar"))

        texto = (
            f"👤 *Minha Conta*\n\n"
            f"🆔 *ID:* `{user_id}`\n"
            f"👤 *Nome:* {nome}\n"
            f"📱 *Username:* @{uname_clean}\n\n"
            f"💰 *Seu Saldo no Bot:* R$ {saldo:.2f}"
        )

        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=texto,
                parse_mode="Markdown",
                reply_markup=markup
            )
        except Exception:
            try:
                bot.send_message(
                    chat_id,
                    texto,
                    parse_mode="Markdown",
                    reply_markup=markup
                )
            except Exception:
                texto_puro = (
                    f"👤 Minha Conta\n\n"
                    f"🆔 ID: {user_id}\n"
                    f"👤 Nome: {nome}\n"
                    f"📱 Username: @{uname if uname else 'sem @'}\n\n"
                    f"💰 Seu Saldo no Bot: R$ {saldo:.2f}"
                )
                bot.send_message(
                    chat_id,
                    texto_puro,
                    reply_markup=markup
                )



    elif call.data.startswith("prod_"):
        partes     = call.data.replace("prod_", "").split("|")
        nome_prod  = partes[0] if len(partes) > 0 else "Produto"
        preco_str  = partes[1] if len(partes) > 1 else "0"
        
        try:
            preco = float(preco_str.replace(',', '.'))
        except ValueError:
            preco = 0.0

        saldo = saldo_usuario(call.from_user.id)

        # 1. Checa primeiro se o usuário tem saldo suficiente
        if saldo < preco:
            bot.answer_callback_query(call.id, "Saldo insuficiente!")
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("💰 Adicionar saldo", callback_data="saldo"))
            markup.add(InlineKeyboardButton("⬅️ Voltar", callback_data="voltar"))
            bot.send_message(
                chat_id,
                f"💳 *{nome_prod}* custa R$ {preco:.2f}.\n"
                f"Seu saldo atual é *R$ {saldo:.2f}*.\n\n"
                "⚠️ Você não tem saldo suficiente para esta compra. Adicione saldo abaixo:",
                parse_mode="Markdown",
                reply_markup=markup
            )
            return

        # 2. Se o usuário tiver saldo suficiente, checa o estoque
        estoque_val = db.obter_quantidade_estoque(nome_prod)
        if estoque_val <= 0:
            bot.answer_callback_query(call.id, "Produto sem estoque!")
            bot.send_message(
                chat_id,
                f"⚠️ Ops! Não temos cartões *{nome_prod}* no estoque no momento.\n"
                "Por favor, volte mais tarde.",
                parse_mode="Markdown"
            )
            return

        # 3. Retira o cartão do estoque e realiza a cobrança do saldo
        cartao = db.retirar_cartao_estoque(nome_prod)
        if not cartao:
            bot.answer_callback_query(call.id, "Produto sem estoque!")
            bot.send_message(
                chat_id,
                f"⚠️ Ops! Não temos cartões *{nome_prod}* no estoque no momento.\n"
                "Por favor, volte mais tarde.",
                parse_mode="Markdown"
            )
            return

        # Desconta o saldo do usuário
        db.descontar_saldo(call.from_user.id, preco)
        novo_saldo = saldo_usuario(call.from_user.id)

        bot.answer_callback_query(call.id, "Compra realizada com sucesso!")
        bot.send_message(
            chat_id,
            f"✅ *Compra realizada com sucesso!*\n\n"
            f"💳 *Produto:* {nome_prod}\n"
            f"💰 *Valor pago:* R$ {preco:.2f}\n"
            f"💼 *Saldo restante:* R$ {novo_saldo:.2f}\n\n"
            f"📋 *Dados do Cartão:*\n`{cartao}`",
            parse_mode="Markdown"
        )

        # Registra o evento e notifica o dono
        registrar_evento(call.from_user.id, call.from_user.first_name or "Usuário", uname, "comprou CC", f"{nome_prod} (R$ {preco:.2f})")
        notificar_dono(
            f"🛍️ *Nova Compra Realizada!*\n\n"
            f"👤 Nome: {call.from_user.first_name}\n"
            f"📱 Username: @{uname if uname else 'sem @'}\n"
            f"🆔 ID: `{call.from_user.id}`\n"
            f"💳 Cartão: *{nome_prod}*\n"
            f"💵 Valor: R$ {preco:.2f}"
        )


# ─────────────────────────────────────────────
# INICIALIZAÇÃO E SERVIDOR WEB FALSO PARA A RENDER
# ─────────────────────────────────────────────
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot rodando com sucesso!")

def keep_alive():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

print("Iniciando servidor web falso para a Render...")
threading.Thread(target=keep_alive, daemon=True).start()

print("Bot iniciado com sucesso!")
bot.infinity_polling()
