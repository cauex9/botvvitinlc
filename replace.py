with open('bot.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("DONO_USERNAME = 'Cl7_ww'      # <-- @ do dono no Telegram (sem @)", "DONO_ID = 8241738977      # <-- ID do dono no Telegram")
text = text.replace('f"https://t.me/{DONO_USERNAME}"', 'f"tg://user?id={DONO_ID}"')
text = text.replace("if uname == DONO_USERNAME:", "if user.id == DONO_ID:")
text = text.replace("if message.from_user.username != DONO_USERNAME:", "if message.from_user.id != DONO_ID:")
text = text.replace("if uname != DONO_USERNAME:", "if call.from_user.id != DONO_ID:")

with open('bot.py', 'w', encoding='utf-8') as f:
    f.write(text)
