import requests

# Token statico che hai generato via OpenAPI Console
TOKEN = "683630af5750ead9fd034507"
URL = "https://company.openapi.com/scopes"  # Endpoint di test gratuito

# Header con autenticazione
headers = {
    "Authorization": f"Bearer {TOKEN}"
}

# Esegui la richiesta
response = requests.get(URL, headers=headers)

# Stampa risultato
print("Status:", response.status_code)
print("Body:", response.text)

if response.status_code == 200:
    print("✅ Token valido e funzionante.")
else:
    print("❌ Errore nel token o permessi insufficienti.")