import time
import board
import busio
from adafruit_bme280 import basic as adafruit_bme280
import json
from datetime import datetime
import subprocess
import logging
import os

# Configura logging
logging.basicConfig(
    filename='/home/egrillo/meteo.log', 
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Inizializza sensore BME280
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
    bme280.sea_level_pressure = 1013.25
    logging.info("Sensore BME280 inizializzato correttamente")
except Exception as e:
    logging.error(f"Errore inizializzazione sensore: {e}")
    exit(1)

repo_path = "/home/egrillo/projectscarousel.github.io"
json_file = f"{repo_path}/dati.json"

def esegui_comando_git(comando):
    """Esegue un comando git e restituisce il risultato"""
    try:
        result = subprocess.run(comando, cwd=repo_path, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logging.error(f"Errore git {comando}: {result.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout comando git: {comando}")
        return False
    except Exception as e:
        logging.error(f"Eccezione comando git {comando}: {e}")
        return False

def main():
    logging.info("Avvio servizio meteo")
    
    while True:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Lettura dati dal sensore
            dati = {
                "orario": now,
                "temperatura": round(bme280.temperature, 1),
                "umidita": round(bme280.humidity, 1),
                "pressione": round(bme280.pressure, 1),
                "altitudine": round(bme280.altitude, 2)
            }

            # Scrivi dati.json
            with open(json_file, "w") as f:
                json.dump(dati, f, indent=2)
            
            logging.info(f"Dati aggiornati: {dati}")

            # Git operations
            if (esegui_comando_git(["git", "add", "dati.json"]) and
                esegui_comando_git(["git", "commit", "-m", f"Aggiornamento dati {now}"]) and
                esegui_comando_git(["git", "pull", "--rebase"]) and  # importante per evitare conflitti
                esegui_comando_git(["git", "push"])):
                
                logging.info("Push completato con successo")
            else:
                logging.warning("Problemi con operazioni Git, riprovo al prossimo ciclo")

        except Exception as e:
            logging.error(f"Errore generale nel loop principale: {e}")
        
        # Aspetta 15 minuti (900 secondi)
        time.sleep(900)

if __name__ == "__main__":
    main()
