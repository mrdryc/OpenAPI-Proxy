from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import requests
import base64
import logging

# Configurazione logging avanzata
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Caricamento variabili d'ambiente
load_dotenv()  # Solo per sviluppo locale

app = Flask(__name__)

# Configurazione centralizzata
CONFIG = {
    "email": os.getenv("EMAIL"),
    "api_key": os.getenv("API_KEY"),
    "static_token": os.getenv("TOKEN"),
    "token_url": "https://company.openapi.com/tokens",
    "data_url": "https://company.openapi.com/IT-full",
    "timeout": 15
}

def get_token():
    """Gestisce l'autenticazione con fallback al token statico"""
    try:
        if CONFIG["static_token"]:
            logger.info("Using static token")
            return CONFIG["static_token"]
        
        logger.debug("Generating new token with credentials")
        credentials = f"{CONFIG['email']}:{CONFIG['api_key']}"
        
        # Verifica encoding Base64
        encoded_creds = base64.b64encode(credentials.encode()).decode()
        logger.debug(f"Encoded credentials: {encoded_creds[:6]}...")
        
        response = requests.post(
            CONFIG["token_url"],
            headers={"Authorization": f"Basic {encoded_creds}"},
            timeout=CONFIG["timeout"]
        )
        response.raise_for_status()
        
        token = response.json().get("token")
        logger.debug(f"Token received: {token[:6]}...")
        return token
        
    except Exception as e:
        logger.error(f"Token error: {str(e)}")
        raise

@app.route("/")
def home():
    return jsonify({
        "status": "active",
        "version": "1.0.0",
        "routes": {
            "company_info": "/company-info?vatCode=<VAT_CODE>"
        }
    })

@app.route("/company-info")
def company_info():
    """Endpoint principale per i dati aziendali"""
    try:
        vat_code = request.args.get("vatCode")
        logger.info(f"New request - VAT: {vat_code}")
        
        # Validazione avanzata
        if not vat_code or not vat_code.isdigit() or len(vat_code) != 11:
            logger.warning(f"Invalid VAT: {vat_code}")
            return jsonify({
                "error": "VAT code must be 11 numeric characters",
                "example": "12345678901"
            }), 400
        
        # Autenticazione
        token = get_token()
        logger.debug(f"Using token: {token[:6]}...")
        
        # Richiesta API
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "OpenAPI-Proxy/1.0"
        }
        
        logger.debug(f"Request headers: {headers}")
        response = requests.get(
            CONFIG["data_url"],
            headers=headers,
            params={"vatCode": vat_code},
            timeout=CONFIG["timeout"]
        )
        
        logger.info(f"API response code: {response.status_code}")
        
        # Gestione risposta
        response.raise_for_status()
        return jsonify(response.json()), 200
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"API Error: {e.response.status_code} - {e.response.text[:100]}"
        logger.error(error_msg)
        return jsonify({
            "error": "External API error",
            "details": error_msg
        }), e.response.status_code
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

