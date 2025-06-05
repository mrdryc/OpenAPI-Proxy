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
    "email": os.getenv("OPENAPI_EMAIL"),
    "api_key": os.getenv("OPENAPI_API_KEY"),
    "static_token": os.getenv("OPENAPI_STATIC_TOKEN"),
    "token_url": "https://company.openapi.com/tokens",
    "data_url": "https://company.openapi.com/IT-full",  # Base URL senza VAT code
    "timeout": int(os.getenv("API_TIMEOUT", 15))
}

def get_token():
    """Gestisce l'autenticazione con fallback al token statico"""
    try:
        if CONFIG["static_token"]:
            logger.info("Using static token")
            return CONFIG["static_token"]

        logger.debug("Generating new token with credentials")
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
        logger.error(f"Token error: {str(e)}")
        raise

@app.route("/")
def home():
    return jsonify({
        "status": "active",
        "version": "1.0.0",
        "routes": {
            "company_info": "/company-info/<vat_code> (es: /company-info/01114601006)"
        }
    })

@app.route("/company-info/<vat_code>")
def company_info(vat_code):
    """Endpoint principale per i dati aziendali"""
    try:
        logger.info(f"New request - VAT: {vat_code}")

        # Validazione VAT code
        if not vat_code.isdigit() or len(vat_code) != 11:
            logger.warning(f"Invalid VAT: {vat_code}")
            return jsonify({
                "error": "VAT code must be 11 numeric characters",
                "example": "12345678901"
            }), 400

        # Autenticazione
        token = get_token()
        if not token:
            logger.error("No token available")
            return jsonify({"error": "Authentication failed"}), 500

        # Costruzione URL corretta secondo documentazione OpenAPI
        api_url = f"{CONFIG['data_url']}/{vat_code}"
        
        # Richiesta API
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "OpenAPI-Proxy/1.0"
        }
        
        logger.debug(f"Request to: {api_url}")
        response = requests.get(
            api_url,
            headers=headers,
            timeout=CONFIG["timeout"]
        )

        logger.info(f"API response code: {response.status_code}")
        
        # Gestione risposta
        response.raise_for_status()
        return jsonify(response.json()), 200
        
    except requests.exceptions.HTTPError as e:
        error_msg = f"API Error {e.response.status_code}: {e.response.text[:200]}"
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