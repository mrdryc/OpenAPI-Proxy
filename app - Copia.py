from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import requests
import base64

# Carica il file .env
load_dotenv()

app = Flask(__name__)

EMAIL = os.getenv("OPENAPI_EMAIL")
API_KEY = os.getenv("OPENAPI_API_KEY")
STATIC_TOKEN = os.getenv("OPENAPI_STATIC_TOKEN")  # Se vuoi usare token fisso

TOKEN_URL = "https://company.openapi.com/tokens"
DATA_URL = "https://company.openapi.com/IT-full"

def get_token():
    if STATIC_TOKEN:
        return STATIC_TOKEN  # Usa token già generato, se disponibile

    credentials = f"{EMAIL}:{API_KEY}"
    headers = {
        "Authorization": "Basic " + base64.b64encode(credentials.encode()).decode()
    }
    response = requests.post(TOKEN_URL, headers=headers)
    if response.status_code == 200:
        return response.json()["token"]
    else:
        raise Exception("Errore ottenimento token: " + response.text)

@app.route("/company-info")
def company_info():
    vat_code = request.args.get("vatCode")
    if not vat_code:
        return jsonify({"error": "Parametro vatCode mancante"}), 400
    try:
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(DATA_URL, headers=headers, params={"vatCode": vat_code})

        # 🔽 Questo è il punto 2 inserito correttamente
        try:
            return jsonify(resp.json()), resp.status_code
        except ValueError:
            return jsonify({
                "error": "Risposta non in formato JSON",
                "raw": resp.text
            }), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

