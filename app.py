from flask import Flask, jsonify
from dotenv import load_dotenv
import os
import requests
import base64
import logging
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from flask_caching import Cache

# Configurazione logging avanzata
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)

CONFIG = {
    "email": os.getenv("OPENAPI_EMAIL"),
    "api_key": os.getenv("OPENAPI_API_KEY"),
    "static_token": os.getenv("OPENAPI_STATIC_TOKEN"),
    "token_url": "https://company.openapi.com/tokens",
    "data_url": "https://company.openapi.com/IT-full",
    "timeout": 30,  # Timeout aumentato
    "max_retries": 3,  # Numero massimo di tentativi
    "backoff_factor": 1.5  # Fattore di backoff esponenziale
}

cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})
cache.init_app(app)

def get_token():
    """Gestisce l'autenticazione con backoff esponenziale"""
    for attempt in range(CONFIG["max_retries"] + 1):
        try:
            if CONFIG["static_token"]:
                return CONFIG["static_token"]
            credentials = f"{CONFIG['email']}:{CONFIG['api_key']}"
            encoded_creds = base64.b64encode(credentials.encode()).decode()
            response = requests.post(
                CONFIG["token_url"],
                headers={"Authorization": f"Basic {encoded_creds}"},
                timeout=CONFIG["timeout"]
            )
            response.raise_for_status()
            return response.json().get("token")
        except Exception as e:
            if attempt == CONFIG["max_retries"]:
                logger.error(f"Token error after {CONFIG['max_retries']} attempts: {str(e)}")
                raise
            wait_time = CONFIG["backoff_factor"] ** attempt
            logger.warning(f"Token request failed (attempt {attempt+1}), retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)

@app.route("/company-info/<vat_code>")
@cache.cached(timeout=300)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def company_info(vat_code):
    """Endpoint con gestione avanzata dei timeout e retry"""
    start_time = time.time()
    try:
        logger.info(f"Inizio richiesta VAT: {vat_code}")
        # Validazione VAT code
        if not vat_code.isdigit() or len(vat_code) != 11:
            logger.warning(f"VAT code non valido: {vat_code}")
            return jsonify({
                "error": "Formato VAT code non valido",
                "suggestion": "Usa 11 cifre numeriche (es: 12345678901)"
            }), 400

        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        api_url = f"{CONFIG['data_url']}/{vat_code}"

        response = requests.get(api_url, headers=headers, timeout=CONFIG["timeout"])
        response.raise_for_status()
        return jsonify(response.json()), 200

    except requests.exceptions.Timeout:
        logger.error("Timeout dopo 30 secondi")
        return jsonify({"error": "Timeout del servizio esterno"}), 504

    except requests.exceptions.HTTPError as e:
        logger.error(f"Errore API: {e.response.status_code}")
        return jsonify({
            "error": "Errore nel servizio esterno",
            "code": e.response.status_code,
            "details": str(e)
        }), 502

    except Exception as e:
        logger.error(f"Errore interno: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Errore temporaneo del server",
            "action": "Riprova tra qualche minuto"
        }), 500

    finally:
        elapsed = time.time() - start_time
        logger.info(f"Richiesta VAT:{vat_code} completata in {elapsed:.2f}s")

@app.errorhandler(500)
def handle_server_error(e):
    logger.error(f"Errore interno: {str(e)}", exc_info=True)
    return jsonify(error="Errore temporaneo, riprovare"), 500

@app.errorhandler(504)
def handle_gateway_timeout(e):
    logger.warning("Timeout Gateway dall'API esterna")
    return jsonify(error="Il servizio esterno non risponde"), 504

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
