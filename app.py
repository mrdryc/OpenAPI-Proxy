from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import requests
import base64
import logging

# Setup log visibili su Render
logging.basicConfig(level=logging.INFO)

# Carica variabili d'ambiente da .env (solo locale)
load_dotenv()

app = Flask(__name__)

EMAIL = os.getenv("EMAIL")
API_KEY = os.getenv("API_KEY")
STATIC_TOKEN = os.getenv("TOKEN")

TOKEN_URL = "https://company.openapi.com/tokens"
DATA_URL = "https://company.openapi.com/IT-full"

def get_token():
    if STATIC_TOKEN:
        logging.info("Utilizzo token statico")
        return STATIC_TOKEN
    credentials = f"{EMAIL}:{API_KEY}"
    headers = {
        "Authorization": "Basic " + base64.b64encode(credentials.encode()).decode()
    }
    response = requests.post(TOKEN_URL, headers=headers)
    if response.status_code == 200:
        return response.json()["token"]
    else:
        raise Exception("Errore ottenimento token: " + response.text)

@app.route("/")
def home():
    return "✅ OpenAPI Proxy attivo!"

@app.route("/company-info")
def company_info():
    vat_code = request.args.get("vatCode")
    if not vat_code:
        return jsonify({"error": "Parametro vatCode mancante"}), 400
    try:
        logging.info(f"Richiesta per VAT: {vat_code}")
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(DATA_URL, headers=headers, params={"vatCode": vat_code})
        logging.info(f"Status code API: {resp.status_code}")
        resp.raise_for_status()
        return jsonify(resp.json()), 200
    except requests.exceptions.HTTPError as e:
        logging.error("Errore HTTP: " + str(e))
        return jsonify({"error": str(e)}), resp.status_code
    except Exception as e:
        logging.error("Errore generico: " + str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

