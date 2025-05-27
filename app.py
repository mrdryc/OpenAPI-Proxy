from flask import Flask, request, jsonify
import requests
import base64

app = Flask(__name__)

EMAIL = "maurizio.secco@taxdry.com"
API_KEY = "w2l5e7ckhmqqzawtbvqw9nnkhbsskqsz"
TOKEN_URL = "https://company.openapi.com/tokens"
DATA_URL = "https://company.openapi.com/IT-full"

def get_token():
    credentials = f"{EMAIL}:{API_KEY}"
    headers = {
        "Authorization": "Basic " + base64.b64encode(credentials.encode()).decode()
    }
    response = requests.post(TOKEN_URL, headers=headers)
    if response.status_code == 200:
        return response.json()["token"]
    else:
        raise Exception("Errore token: " + response.text)

@app.route("/company-info")
def company_info():
    vat_code = request.args.get("vatCode")
    if not vat_code:
        return jsonify({"error": "Parametro vatCode mancante"}), 400
    try:
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(DATA_URL, headers=headers, params={"vatCode": vat_code})
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)


