import time
import os
import csv
import requests
from playwright.sync_api import sync_playwright

# ================== TELEGRAM ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def enviar_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        })
    except Exception as e:
        print("Erro Telegram:", e)

# ================== ESTRATEGIA ==================
class Estrategia:
    def __init__(self, nome, padrao, numeros_str, numeros_list, gales):
        self.nome = nome
        self.padrao = padrao
        self.numeros_str = numeros_str
        self.numeros_list = numeros_list
        self.gales = gales

def carregar_estrategias():
    estrategias = []
    with open("estrategias.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=';')
        for row in reader:
            if len(row) < 4:
                continue

            nome = row[0].strip()
            padrao = [x.strip().upper() for x in row[1].split('-') if x.strip()]
            numeros_str = row[2].replace('"', '').strip()

            numeros_list = []
            for item in numeros_str.split(','):
                item = item.strip().upper()
                if item.startswith("G"):
                    g = int(item[1:])
                    if g == 1:
                        numeros_list.extend(range(10, 20))
                    elif g == 2:
                        numeros_list.extend(range(20, 30))
                    elif g == 3:
                        numeros_list.extend(range(30, 37))
                elif item.isdigit():
                    numeros_list.append(int(item))

            gales = int(row[3].strip())
            estrategias.append(Estrategia(nome, padrao, numeros_str, numeros_list, gales))

    return estrategias

def extrair_numeros(page):
    elementos = page.query_selector_all(".cell__wrapper")
    nums = []
    for el in elementos:
        txt = el.inner_text().split("\n")[0]
        if txt.isdigit():
            nums.append(int(txt))
    return nums

def corresponde(valor, padrao_item):
    if padrao_item.startswith("G"):
        g = int(padrao_item[1:])
        if g == 1:
            return 10 <= valor <= 19
        elif g == 2:
            return 20 <= valor <= 29
        elif g == 3:
            return 30 <= valor <= 36
        return False
    return valor == int(padrao_item)

def padrao_bate(resultados, padrao):
    if len(resultados) < len(padrao):
        return False
    ultimos = resultados[:len(padrao)][::-1]
    for num, p in zip(ultimos, padrao):
        if not corresponde(num, p):
            return False
    return True

def monitorar():
    estrategias = carregar_estrategias()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.tipminer.com/br/historico/evolution/lightning-roulette")
        page.wait_for_selector(".cell__wrapper")

        ultimo = None
        aguardando = False
        estrategia_ativa = None
        gale = 0

        while True:
            try:
                numeros = extrair_numeros(page)

                if numeros and numeros[0] != ultimo:
                    atual = numeros[0]
                    ultimo = atual

                    print("Número:", atual)

                    if aguardando:
                        if atual in estrategia_ativa.numeros_list:
                            enviar_telegram("✅ *VITÓRIA*")
                            aguardando = False
                            gale = 0
                        else:
                            gale += 1
                            if gale > estrategia_ativa.gales:
                                enviar_telegram("❌ *DERROTA*")
                                aguardando = False
                                gale = 0

                    if not aguardando:
                        for e in estrategias:
                            if padrao_bate(numeros, e.padrao):
                                estrategia_ativa = e
                                aguardando = True
                                gale = 0

                                enviar_telegram(
                                    f"🔥 *ENTRADA*\n"
                                    f"📌 {e.nome}\n"
                                    f"🎯 {e.numeros_str}\n"
                                    f"♻️ Gales: {e.gales}"
                                )
                                break

                time.sleep(5)

            except Exception as erro:
                print("Erro monitor:", erro)
                time.sleep(5)

if __name__ == "__main__":
    monitorar()
