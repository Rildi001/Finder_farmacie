"""
FARMACIE FINDER MONDIALE - VERSIONE COMPLETA

Funzionalità:
- Login utente con sistema "Ricordati di me" (sessione.json)
- Registrazione utente con validazione licenza (GitHub remoto)
- Salvataggio utenti in utenti.json
- Log degli accessi con: nome, email, licenza, data, IP pubblico (licenze/accessi_log.json)
- Ricerca automatica di farmacie usando Google Places API
- Salvataggio contatti in CSV personalizzato
- Sincronizzazione automatica con GitHub (git add/commit/push)
"""

import json
import hashlib
import os
import requests
from datetime import datetime
import time
import re
import csv
import subprocess

# === CONFIG ===
UTENTI_FILE = "utenti.json"
SESSIONE_FILE = "sessione.json"
DUPLICATI_FILE = "place_ids_farmacie.json"
LICENZE_URL = "https://raw.githubusercontent.com/Rildi001/Finder_farmacie/main/licenze.json"
API_KEY = "AIzaSyAySM5ozPWAlKCHHQ-QifF3TSTzYKAOLvs"
CARTELLA_LOG = "licenze"
LOG_FILE = os.path.join(CARTELLA_LOG, "accessi_log.json")

EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@(?!.*?(?:gmail|yahoo|hotmail|outlook|aol|protonmail))[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', re.IGNORECASE)
SOCIAL_PATTERN = re.compile(r'(https?://(?:www\.)?(facebook|instagram|tiktok|linkedin|twitter)\.com/[^\s"\'\)]+)', re.IGNORECASE)

# === UTILS ===
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def carica_utenti():
    if not os.path.exists(UTENTI_FILE):
        return {}
    with open(UTENTI_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salva_utenti(dati):
    with open(UTENTI_FILE, "w", encoding="utf-8") as f:
        json.dump(dati, f, indent=2)

def salva_sessione(username):
    with open(SESSIONE_FILE, "w", encoding="utf-8") as f:
        json.dump({"username": username}, f)

def carica_sessione():
    if os.path.exists(SESSIONE_FILE):
        with open(SESSIONE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("username")
    return None

def get_ip_pubblico():
    try:
        return requests.get("https://api.ipify.org").text
    except:
        return "IP non disponibile"

def log_accesso(username, nome, email, licenza):
    if not os.path.exists(CARTELLA_LOG):
        os.makedirs(CARTELLA_LOG)
    log = {
        "username": username,
        "nome": nome,
        "email": email,
        "licenza": licenza,
        "data_accesso": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": get_ip_pubblico()
    }
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"accessi": []}
    data["accessi"].append(log)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    push_su_github(LOG_FILE)

def push_su_github(file_path):
    try:
        subprocess.run(["git", "add", file_path], check=True)
        subprocess.run(["git", "add", UTENTI_FILE], check=True)
        subprocess.run(["git", "commit", "-m", "Aggiornamento utenti e accessi"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("🚀 Dati sincronizzati su GitHub!")
    except Exception as e:
        print("⚠️ Impossibile sincronizzare con GitHub:", e)

# === LICENZA ===
def licenza_valida(chiave):
    try:
        # URL del file licenze su GitHub
        r = requests.get(LICENZE_URL, timeout=10)
        if r.status_code == 200:
            data = r.json()
            scadenza = data.get("chiavi_valide", {}).get(chiave)
            if not scadenza:
                return False
            oggi = datetime.now().date()
            scad = datetime.strptime(scadenza, "%Y-%m-%d").date()
            return oggi <= scad
        else:
            print("⚠️ Errore nel recupero delle licenze da GitHub.")
            return False
    except requests.RequestException as e:
        print(f"Errore di rete: {e}")
        return False

# === REGISTRAZIONE ===
def registra():
    utenti = carica_utenti()
    username = input("\n👤 Scegli uno username: ").strip()
    if username in utenti:
        print("❌ Username già registrato.")
        return False
    nome = input("🧍 Inserisci il tuo nome: ").strip()
    email = input("📧 Inserisci la tua email: ").strip()
    password = input("🔐 Crea una password: ").strip()
    licenza = input("🔑 Inserisci la tua chiave di licenza: ").strip()
    if not licenza_valida(licenza):
        print("❌ Licenza non valida o scaduta.")
        return False
    utenti[username] = {
        "nome": nome,
        "email": email,
        "password": hash_password(password),
        "licenza": licenza
    }
    salva_utenti(utenti)
    salva_sessione(username)
    log_accesso(username, nome, email, licenza)
    print("✅ Registrazione completata!")
    return True

# === LOGIN ===
def login():
    utenti = carica_utenti()
    username = input("\n👤 Username: ").strip()
    password = input("🔐 Password: ").strip()
    utente = utenti.get(username)
    if not utente or hash_password(password) != utente["password"]:
        print("❌ Credenziali errate.")
        return None
    salva_sessione(username)
    log_accesso(username, utente['nome'], utente['email'], utente['licenza'])
    print(f"✅ Bentornato, {utente['nome']}!")
    return utente

# === LOGIN AUTOMATICO ===
def login_automatico():
    last_user = carica_sessione()
    if last_user:
        print(f"\n👋 Bentornato {last_user}! Vuoi accedere direttamente?")
        scelta = input("[S/n]: ").strip().lower()
        if scelta in ["", "s", "si"]:
            utenti = carica_utenti()
            return utenti.get(last_user)
    return None

# === GET FARMACIE ===
def get_file_name(stato, provincia, numero_contatti):
    safe_provincia = provincia.replace(" ", "_") if provincia else "all"
    safe_stato = stato.replace(" ", "_")
    return f"farmacie_{safe_stato}_{safe_provincia}_{numero_contatti}.csv"

def carica_place_ids():
    if os.path.exists(DUPLICATI_FILE):
        try:
            with open(DUPLICATI_FILE, "r", encoding="utf-8") as f:
                data = f.read().strip()
                if not data:
                    return set()
                return set(json.loads(data))
        except json.JSONDecodeError:
            return set()
    return set()

def salva_place_ids(ids):
    with open(DUPLICATI_FILE, "w", encoding="utf-8") as f:
        json.dump(list(ids), f, ensure_ascii=False, indent=2)

def salva_negozi(file_name, contatti_trovati):
    righe = []
    for contatto in contatti_trovati:
        nuova_riga = {
            "Nome": contatto.get("Nome", ""),
            "Indirizzo": contatto.get("Indirizzo", ""),
            "Sito Web": contatto.get("Sito Web", "")
        }
        email_list = [e.strip() for e in contatto.get("Email", "").split(",") if e.strip()]
        for i in range(1, 4):
            nuova_riga[f"Email {i}"] = email_list[i-1] if i <= len(email_list) else ""
        tel_list = [t.strip() for t in re.split(r"[,/]", contatto.get("Telefono", "")) if t.strip()]
        for i in range(1, 4):
            nuova_riga[f"Telefono {i}"] = tel_list[i-1] if i <= len(tel_list) else ""
        for social in ["Facebook", "Instagram", "TikTok", "LinkedIn", "Twitter"]:
            nuova_riga[social] = contatto.get(social, "")
        righe.append(nuova_riga)
    intestazioni = sorted(righe[0].keys())
    with open(file_name, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=intestazioni)
        writer.writeheader()
        writer.writerows(righe)

def get_dettagli(place_id):
    url_base = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "placeid": place_id,
        "key": API_KEY
    }
    try:
        response = requests.get(url_base, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        result = data.get("result", {})
        telefono = result.get("formatted_phone_number", "N/D")
        sito_web = result.get("website", "N/D")
        return telefono, sito_web
    except requests.RequestException as e:
        print(f"Errore nel recupero dei dettagli: {e}")
        return "N/D", "N/D"

def trova_negozi_farmacie(stato, provincia, numero_contatti, file_name):
    url_base = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    contatti_trovati = []
    pagetoken = None
    visti_ids = carica_place_ids()

    while len(contatti_trovati) < numero_contatti:
        params = {"key": API_KEY}
        if pagetoken:
            params["pagetoken"] = pagetoken
            time.sleep(5)
        else:
            query = f"pharmacies in {provincia}, {stato}" if provincia else f"pharmacies in {stato}"
            params["query"] = query

        try:
            response = requests.get(url_base, params=params, timeout=15)
            response.raise_for_status()
        except:
            break

        data = response.json()
        results = data.get("results", [])
        for risultato in results:
            if len(contatti_trovati) >= numero_contatti:
                break
            place_id = risultato.get("place_id")
            if not place_id or place_id in visti_ids:
                continue
            nome = risultato.get("name", "N/D")
            indirizzo = risultato.get("formatted_address", "N/D")
            telefono, sito_web = get_dettagli(place_id)
            social_links = estrai_social(sito_web) if sito_web != "N/D" else {}
            email = estrai_email(sito_web) if sito_web != "N/D" else ""
            contatto = {
                "Nome": nome,
                "Indirizzo": indirizzo,
                "Telefono": telefono,
                "Sito Web": sito_web,
                "Email": email,
                **social_links
            }
            contatti_trovati.append(contatto)
            visti_ids.add(place_id)

        pagetoken = data.get("next_page_token")
        if not pagetoken:
            break

    salva_place_ids(visti_ids)
    salva_negozi(file_name, contatti_trovati)
    return contatti_trovati

# === AVVIO ===
def avvia_programma():
    print("\n=== FARMACIE FINDER ===")
    stato = input("🌍 Inserisci lo STATO (es. Italy, Brazil, USA): ").strip()
    provincia = input("🏙️ Inserisci la PROVINCIA o lascia vuoto per tutto lo stato: ").strip()
    while True:
        try:
            numero = int(input("🔢 Quanti contatti vuoi trovare? (es. 20): "))
            if numero > 0:
                break
        except:
            pass
    file_name = get_file_name(stato, provincia, numero)
    risultati = trova_negozi_farmacie(stato, provincia, numero, file_name)
    print(f"\n✅ {len(risultati)} contatti salvati in: {file_name}\n")

def main():
    print("""
=============================================
      🌍 FARMACIE FINDER MONDIALE 🌍
   Login e Licenza richiesti per iniziare
=============================================
""")
    utente = login_automatico()
    if not utente:
        while True:
            print("\n1. Login\n2. Registrati\n3. Esci")
            scelta = input("Scegli un'opzione: ").strip()
            if scelta == "1":
                utente = login()
                if utente:
                    break
            elif scelta == "2":
                if registra():
                    utente = login()
                    if utente:
                        break
            elif scelta == "3":
                print("👋 Uscita dal programma.")
                return
            else:
                print("❌ Scelta non valida.")
    avvia_programma()

if __name__ == "__main__":
    main()
