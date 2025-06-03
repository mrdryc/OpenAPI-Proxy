from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import requests
import base64
import logging

# Configura il logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carica il file .env
load_dotenv()

app = Flask(__name__)

# Configurazioni
EMAIL = os.getenv("OPENAPI_EMAIL")
API_KEY = os.getenv("OPENAPI_API_KEY")
STATIC_TOKEN = os.getenv("OPENAPI_STATIC_TOKEN")
TOKEN_URL = "https://company.openapi.com/tokens"
DATA_URL = "https://company.openapi.com/IT-full"

def get_token():
    """Ottiene il token di autenticazione"""
    try:
        if STATIC_TOKEN:
            logger.info("Utilizzo token statico")
            return STATIC_TOKEN

        credentials = f"{EMAIL}:{API_KEY}"
        encoded_creds = base64.b64encode(credentials.encode()).decode()
        
        logger.info("Richiesta nuovo token")
        response = requests.post(
            TOKEN_URL,
            headers={"Authorization": f"Basic {encoded_creds}"},
            timeout=10
        )
        response.raise_for_status()
        
        return response.json()["token"]
    
    except Exception as e:
        logger.error(f"Errore generazione token: {str(e)}")
        raise

@app.route("/")
def home():
    return "Hello, world! The app is running."

@app.route("/company-info")
def company_info():
    """Endpoint dati aziendali"""
    try:
        vat_code = request.args.get("vatCode")
        logger.info(f"Richiesta per VAT: {vat_code}")
        
        if not vat_code or not vat_code.isdigit() or len(vat_code) != 11:
            logger.warning(f"VAT code non valido: {vat_code}")
            return jsonify({"error": "VAT code deve essere 11 cifre numeriche"}), 400
        
        token = get_token()
        logger.debug(f"Token utilizzato: {token[:6]}...")  # Log parziale per sicurezza
        
        response = requests.get(
            DATA_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={"vatCode": vat_code},
            timeout=15
        )
        
        logger.info(f"Status code API: {response.status_code}")
        logger.debug(f"Risposta API: {response.text[:200]}...")  # Log parziale
        
        response.raise_for_status()
        return jsonify(response.json()), response.status_code
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"Errore HTTP: {str(e)}")
        return jsonify({
            "error": f"Errore API esterna: {e.response.text}",
            "status_code": e.response.status_code
        }), e.response.status_code
    
    except ValueError as e:
        logger.error(f"Risposta non JSON: {str(e)}")
        return jsonify({
            "error": "Formato risposta non valido",
            "raw_response": response.text[:200]  # Mostra solo parte della risposta
        }), 500
    
    except Exception as e:
        logger.error(f"Errore generico: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Errore interno del server",
            "details": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
