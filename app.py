from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import requests
import base64
import logging

# Configura il logging più dettagliato
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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

def check_environment():
    """Verifica le variabili d'ambiente"""
    missing = []
    if not EMAIL:
        missing.append("OPENAPI_EMAIL")
    if not API_KEY and not STATIC_TOKEN:
        missing.append("OPENAPI_API_KEY o OPENAPI_STATIC_TOKEN")
    
    if missing:
        logger.error(f"Variabili d'ambiente mancanti: {missing}")
        return False
    
    logger.info("Variabili d'ambiente configurate correttamente")
    return True

def get_token():
    """Ottiene il token di autenticazione"""
    try:
        if STATIC_TOKEN:
            logger.info("Utilizzo token statico")
            return STATIC_TOKEN

        if not EMAIL or not API_KEY:
            raise ValueError("EMAIL e API_KEY sono richiesti se non si usa STATIC_TOKEN")

        credentials = f"{EMAIL}:{API_KEY}"
        encoded_creds = base64.b64encode(credentials.encode()).decode()
        
        logger.info(f"Richiesta nuovo token per email: {EMAIL}")
        logger.debug(f"Credentials encoded: {encoded_creds[:20]}...")
        
        response = requests.post(
            TOKEN_URL,
            headers={"Authorization": f"Basic {encoded_creds}"},
            timeout=10
        )
        
        logger.info(f"Token response status: {response.status_code}")
        logger.debug(f"Token response: {response.text}")
        
        response.raise_for_status()
        token_data = response.json()
        return token_data["token"]
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Errore richiesta token: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response text: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"Errore generico token: {str(e)}")
        raise

@app.route("/")
def home():
    env_status = check_environment()
    return jsonify({
        "message": "Hello, world! The app is running.",
        "environment_ok": env_status,
        "endpoints": ["/company-info?vatCode=XXXXXXXXXXX"]
    })

@app.route("/health")
def health():
    """Endpoint per verificare lo stato dell'applicazione"""
    try:
        env_ok = check_environment()
        if env_ok:
            # Test di connessione al servizio token
            if STATIC_TOKEN:
                token_ok = True
                token_message = "Static token configured"
            else:
                try:
                    token = get_token()
                    token_ok = bool(token)
                    token_message = "Token generation successful"
                except Exception as e:
                    token_ok = False
                    token_message = f"Token generation failed: {str(e)}"
        else:
            token_ok = False
            token_message = "Environment not configured"
        
        return jsonify({
            "status": "healthy" if env_ok and token_ok else "unhealthy",
            "environment": env_ok,
            "token_service": token_ok,
            "message": token_message
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route("/company-info")
def company_info():
    """Endpoint dati aziendali"""
    try:
        vat_code = request.args.get("vatCode")
        logger.info(f"Richiesta company-info per VAT: {vat_code}")
        
        # Verifica environment
        if not check_environment():
            return jsonify({"error": "Configurazione ambiente non valida"}), 500
        
        # Validazione VAT code
        if not vat_code:
            logger.warning("VAT code mancante")
            return jsonify({"error": "Parametro 'vatCode' richiesto"}), 400
            
        if not vat_code.isdigit() or len(vat_code) != 11:
            logger.warning(f"VAT code non valido: {vat_code}")
            return jsonify({
                "error": "VAT code deve essere 11 cifre numeriche",
                "received": vat_code,
                "length": len(vat_code) if vat_code else 0
            }), 400
        
        # Ottieni token
        logger.info("Ottenimento token...")
        token = get_token()
        logger.debug(f"Token ottenuto: {token[:10]}..." if token else "Token vuoto")
        
        # Chiamata API
        logger.info(f"Chiamata API per VAT: {vat_code}")
        response = requests.get(
            DATA_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={"vatCode": vat_code},
            timeout=15
        )
        
        logger.info(f"Status code API: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")
        logger.debug(f"Response text (primi 500 char): {response.text[:500]}")
        
        if response.status_code != 200:
            logger.error(f"API returned non-200 status: {response.status_code}")
            return jsonify({
                "error": f"API esterna ha restituito errore {response.status_code}",
                "details": response.text,
                "status_code": response.status_code
            }), response.status_code
        
        # Parse JSON response
        try:
            json_data = response.json()
            logger.info("Risposta JSON parsata con successo")
            return jsonify(json_data), 200
        except ValueError as json_error:
            logger.error(f"Errore parsing JSON: {json_error}")
            return jsonify({
                "error": "Risposta API non è JSON valido",
                "raw_response": response.text[:500],
                "content_type": response.headers.get('content-type')
            }), 500
    
    except requests.exceptions.Timeout:
        logger.error("Timeout nella richiesta API")
        return jsonify({"error": "Timeout nella richiesta API"}), 504
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Errore di connessione: {str(e)}")
        return jsonify({"error": "Errore di connessione all'API esterna"}), 503
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"Errore HTTP: {str(e)}")
        return jsonify({
            "error": f"Errore HTTP: {e.response.status_code}",
            "details": e.response.text if hasattr(e, 'response') else str(e)
        }), getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500
    
    except Exception as e:
        logger.error(f"Errore generico: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Errore interno del server",
            "details": str(e),
            "type": type(e).__name__
        }), 500

if __name__ == "__main__":
    logger.info("Avvio applicazione Flask")
    logger.info(f"Environment check: {check_environment()}")
    app.run(host="0.0.0.0", port=5000, debug=True)