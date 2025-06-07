from flask import Flask, jsonify, request
from dotenv import load_dotenv
import os
import requests
import base64
import logging
import time
from datetime import datetime, timedelta
from flask_caching import Cache
from flask_cors import CORS

# Configurazione logging avanzata
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://chat.openai.com", "https://chatgpt.com"])

# Configurazione centralizzata
CONFIG = {
    "email": os.getenv("OPENAPI_EMAIL"),
    "api_key": os.getenv("OPENAPI_API_KEY"),
    "static_token": os.getenv("OPENAPI_STATIC_TOKEN"),
    "token_url": "https://company.openapi.com/tokens",
    "data_url": "https://company.openapi.com/IT-full",
    "timeout": 30,
    "max_retries": 3,
    "backoff_factor": 1.5,
    "token_refresh": timedelta(minutes=55)
}

# Cache per il token e le risposte
TOKEN_CACHE = {
    "value": None,
    "expiry": None,
    "refresh_count": 0
}

cache = Cache(config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})
cache.init_app(app)

def get_token():
    """Gestisce l'autenticazione con cache e refresh automatico"""
    try:
        if CONFIG["static_token"]:
            if TOKEN_CACHE["value"] != CONFIG["static_token"]:
                TOKEN_CACHE["value"] = CONFIG["static_token"]
                TOKEN_CACHE["expiry"] = datetime.now() + CONFIG["token_refresh"]
                logger.info("Token statico configurato")
            return TOKEN_CACHE["value"]
        
        if not TOKEN_CACHE["value"] or datetime.now() > TOKEN_CACHE["expiry"]:
            logger.info("Generazione nuovo token dinamico")
            credentials = f"{CONFIG['email']}:{CONFIG['api_key']}"
            encoded_creds = base64.b64encode(credentials.encode()).decode()
            
            response = requests.post(
                CONFIG["token_url"],
                headers={"Authorization": f"Basic {encoded_creds}"},
                timeout=CONFIG["timeout"]
            )
            response.raise_for_status()
            
            TOKEN_CACHE["value"] = response.json().get("token")
            TOKEN_CACHE["expiry"] = datetime.now() + CONFIG["token_refresh"]
            TOKEN_CACHE["refresh_count"] += 1
            logger.debug(f"Nuovo token generato: {TOKEN_CACHE['value'][:6]}...")
        
        return TOKEN_CACHE["value"]
    
    except Exception as e:
        logger.error(f"Errore generazione token: {str(e)}")
        raise

@app.route("/openapi.json")
def openapi_spec():
    """Endpoint per la specifica OpenAPI"""
    return jsonify({
        "openapi": "3.0.0",
        "info": {
            "title": "Company Info API",
            "version": "1.0.0",
            "description": "API per dati aziendali verificati"
        },
        "paths": {
            "/company-info/{vat_code}": {
                "get": {
                    "summary": "Ottieni dati aziendali",
                    "parameters": [{
                        "name": "vat_code",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string",
                            "pattern": "^\\d{11}$"
                        }
                    }],
                    "responses": {
                        "200": {
                            "description": "Dati aziendali",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/CompanyData"
                                    }
                                }
                            }
                        },
                        "400": {"$ref": "#/components/responses/InvalidVAT"},
                        "401": {"$ref": "#/components/responses/Unauthorized"},
                        "500": {"$ref": "#/components/responses/ServerError"}
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "CompanyData": {
                    "type": "object",
                    "properties": {
                        "ragione_sociale": {"type": "string"},
                        "sede_legale": {"type": "string"},
                        "fatturato": {"type": "number"},
                        "dipendenti": {"type": "integer"}
                    }
                }
            },
            "responses": {
                "InvalidVAT": {
                    "description": "VAT code non valido",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "error": {"type": "string"},
                                    "example": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
    })

@app.route("/company-info/<vat_code>")
@cache.cached(timeout=300, query_string=True)
def company_info(vat_code):
    """Endpoint principale per i dati aziendali"""
    start_time = time.time()
    try:
        logger.info(f"Nuova richiesta VAT: {vat_code}")
        
        # Validazione input
        if not vat_code.isdigit() or len(vat_code) != 11:
            logger.warning(f"VAT non valido: {vat_code}")
            return jsonify({
                "error": "Formato VAT code non valido",
                "example": "12345678901"
            }), 400

        # Autenticazione
        token = get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "OpenAPI-Proxy/1.0"
        }
        api_url = f"{CONFIG['data_url']}/{vat_code}"

        # Richiesta all'API esterna
        response = requests.get(
            api_url,
            headers=headers,
            timeout=CONFIG["timeout"]
        )
        
        # Gestione errori HTTP
        response.raise_for_status()
        
        return jsonify({
            "success": True,
            "data": response.json(),
            "vat_code": vat_code,
            "timestamp": int(time.time())
        }), 200

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        logger.error(f"Errore API {status_code}: {e.response.text[:200]}")
        
        if status_code == 401:
            TOKEN_CACHE["value"] = None  # Forza refresh token
        
        return jsonify({
            "success": False,
            "error": "Errore servizio esterno",
            "code": status_code,
            "details": e.response.text[:200]
        }), 502

    except requests.exceptions.Timeout:
        logger.error("Timeout servizio esterno")
        return jsonify({
            "success": False,
            "error": "Timeout servizio esterno",
            "action": "Riprova tra 30 secondi"
        }), 504

    except Exception as e:
        logger.error(f"Errore interno: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Errore temporaneo del server",
            "details": str(e)
        }), 500

    finally:
        logger.info(f"Richiesta {vat_code} completata in {time.time() - start_time:.2f}s")

@app.route("/health")
def health_check():
    """Endpoint per health check"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "token_refreshes": TOKEN_CACHE["refresh_count"]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
