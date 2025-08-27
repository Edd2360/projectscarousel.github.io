#!/home/egrillo/dht-env/bin/python3

import time
import board
import busio
from adafruit_bme280 import basic as adafruit_bme280
import json
from datetime import datetime, date
import subprocess
import logging
import os

# Configura logging
logging.basicConfig(
    filename='/home/egrillo/meteo_storico.log', 
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info("=== AVVIO SERVIZIO METEO ===")

try:
    # Import delle librerie hardware
    import board
    import busio
    from adafruit_bme280 import basic as adafruit_bme280
    
    # Inizializza sensore
    i2c = busio.I2C(board.SCL, board.SDA)
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
    bme280.sea_level_pressure = 1013.25
    logging.info("Sensore BME280 inizializzato")
    sensore_attivo = True
    
except ImportError as e:
    logging.error(f"Librerie hardware non trovate: {e}")
    logging.warning("Modalità simulazione attivata")
    sensore_attivo = False
except Exception as e:
    logging.error(f"ERRORE sensore: {e}")
    sensore_attivo = False

# Percorsi file
repo_path = "/home/egrillo/projectscarousel.github.io"
json_file = os.path.join(repo_path, "dati.json")
storico_file = os.path.join(repo_path, "storico.json")

logging.info(f"Directory lavoro: {repo_path}")

def leggi_sensore():
    """Legge i dati dal sensore o simula se non disponibile"""
    if sensore_attivo:
        try:
            return {
                "temperatura": round(bme280.temperature, 1),
                "umidita": round(bme280.humidity, 1),
                "pressione": round(bme280.pressure, 1),
                "altitudine": round(bme280.altitude, 2)
            }
        except Exception as e:
            logging.error(f"Errore lettura sensore: {e}")
    
    # Modalità simulazione (per testing)
    import random
    return {
        "temperatura": round(20 + random.uniform(-2, 2), 1),
        "umidita": round(45 + random.uniform(-5, 5), 1),
        "pressione": round(1013 + random.uniform(-2, 2), 1),
        "altitudine": round(150 + random.uniform(-1, 1), 2)
    }

def carica_storico():
    """Carica il file storico se esiste"""
    try:
        if os.path.exists(storico_file):
            with open(storico_file, 'r') as f:
                storico = json.load(f)
                # Assicurati che ogni giorno abbia la chiave 'orari'
                for giorno in storico.values():
                    if 'orari' not in giorno:
                        giorno['orari'] = []
                return storico
        return {}
    except Exception as e:
        logging.error(f"Errore caricamento storico: {e}")
        return {}

def salva_storico(storico):
    """Salva il file storico"""
    try:
        with open(storico_file, 'w') as f:
            json.dump(storico, f, indent=2)
    except Exception as e:
        logging.error(f"Errore salvataggio storico: {e}")

def git_commit_push():
    """Esegue le operazioni Git in modo più robusto"""
    try:
        os.chdir(repo_path)
        
        # Configura Git per merge semplice (se non già configurato)
        subprocess.run(["git", "config", "pull.rebase", "false"], 
                      capture_output=True, timeout=10, check=False)
        
        # Add dei file
        result_add = subprocess.run(["git", "add", "dati.json", "storico.json"], 
                                  capture_output=True, text=True, timeout=30)
        if result_add.returncode != 0:
            logging.warning(f"Git add warning: {result_add.stderr}")
            return False
        
        # Commit
        result_commit = subprocess.run(["git", "commit", "-m", f"Aggiornamento {datetime.now()}"], 
                                     capture_output=True, text=True, timeout=30)
        if result_commit.returncode != 0:
            # Se il commit fallisce per "nothing to commit", non è un errore
            if "nothing to commit" in result_commit.stderr:
                logging.debug("Nessuna modifica da commitare")
            else:
                logging.warning(f"Git commit warning: {result_commit.stderr}")
                return False
        
        # Pull con strategia semplice
        result_pull = subprocess.run(["git", "pull"], 
                                   capture_output=True, text=True, timeout=60)
        if result_pull.returncode != 0:
            logging.warning(f"Git pull warning: {result_pull.stderr}")
            
            # Prova un approccio più aggressivo per risolvere i conflitti
            try:
                subprocess.run(["git", "fetch", "origin"], 
                             capture_output=True, timeout=30, check=False)
                subprocess.run(["git", "reset", "--hard", "origin/main"], 
                             capture_output=True, timeout=30, check=False)
                logging.info("Reset del repository eseguito")
            except Exception as e:
                logging.warning(f"Reset fallito: {e}")
                return False
        
        # Push
        result_push = subprocess.run(["git", "push"], 
                                   capture_output=True, text=True, timeout=60)
        if result_push.returncode == 0:
            logging.info("Git push completato")
            return True
        else:
            logging.warning(f"Git push warning: {result_push.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logging.warning("Timeout operazioni Git")
        return False
    except Exception as e:
        logging.warning(f"Git operation exception: {e}")
        return False

def main():
    logging.info("Servizio meteo avviato")
    os.chdir(repo_path)
    
    while True:
        try:
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            today_str = now.date().isoformat()
            
            # Lettura dati
            dati_sensore = leggi_sensore()
            dati = {
                "orario": now_str,
                **dati_sensore
            }
            
            logging.debug(f"Dati: {dati}")

            # Salva dati correnti
            with open(json_file, "w") as f:
                json.dump(dati, f, indent=2)
            
            # Aggiorna storico
            storico = carica_storico()
            
            if today_str not in storico:
                storico[today_str] = {
                    "temperature": [],
                    "umidita": [],
                    "pressione": [],
                    "altitudine": [],
                    "orari": [],
                    "conteggio": 0
                }
            else:
                # Assicurati che le chiavi esistano anche per i giorni esistenti
                if 'orari' not in storico[today_str]:
                    storico[today_str]['orari'] = []
            
            # Aggiungi dati allo storico con orario reale
            storico[today_str]["temperature"].append(dati["temperatura"])
            storico[today_str]["umidita"].append(dati["umidita"])
            storico[today_str]["pressione"].append(dati["pressione"])
            storico[today_str]["altitudine"].append(dati["altitudine"])
            storico[today_str]["orari"].append(now_str)
            storico[today_str]["conteggio"] += 1
            
            # Mantieni solo ultimi 7 giorni
            for giorno in list(storico.keys()):
                if (date.today() - date.fromisoformat(giorno)).days > 7:
                    del storico[giorno]
            
            salva_storico(storico)
            
            # Git operations (continua anche se fallisce)
            git_success = git_commit_push()
            if not git_success:
                logging.warning("Operazioni Git fallite, ma continuo l'esecuzione")
            
            logging.info(f"Aggiornato: {dati['temperatura']}°C, {dati['umidita']}%")
            
        except Exception as e:
            logging.error(f"Errore nel loop principale: {e}")
            # Continua l'esecuzione anche in caso di errore
            try:
                time.sleep(300)  # Aspetta 5 minuti prima di riprovare
            except:
                pass
        else:
            time.sleep(900)  # 15 minuti se tutto ok

if __name__ == "__main__":
    main()
