# Catalogo Telegram em Python

Bot demonstrativo de catalogo para produtos e servicos legitimos, com menu inline em duas colunas.

## Configuracao

1. Instale Python 3.11 ou superior.
2. Abra o terminal nesta pasta.
3. Crie um ambiente virtual:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

4. Instale as dependencias:

```powershell
python -m pip install -r requirements.txt
```

5. Copie `.env.example` para `.env` e coloque um token novo do BotFather:

```powershell
Copy-Item .env.example .env
```

Preencha tambem no `.env` as credenciais da Poseidon:

```env
POSEIDON_PUBLIC_KEY=sua_chave_publica
POSEIDON_SECRET_KEY=sua_chave_secreta
POSEIDON_CALLBACK_URL=https://seu-dominio.com/pix/callback
```

Ao clicar em `Pagar com Pix`, o bot coleta os dados obrigatorios do cliente,
cria a cobranca no endpoint de recebimento Pix e envia o codigo copia e cola.
As chaves nunca devem ser colocadas no codigo ou enviadas pelo chat.

6. Inicie o bot:

```powershell
python bot.py
```

## Personalizacao

Edite a lista `PRODUCTS` em `bot.py` para cadastrar produtos ou servicos legais. O bot nao solicita nem armazena dados de cartao.

## Seguranca

O token enviado anteriormente na conversa deve ser revogado no BotFather com `/revoke`. Gere um novo token e mantenha-o somente no arquivo `.env`, que ja esta no `.gitignore`.
