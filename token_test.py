import requests

TOKEN = "683630af5750ead9fd034507"  # Inserisci qui il tuo token valido
URL = "https://company.openapi.com/scopes"  # Endpoint gratuito e sempre accessibile

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

response = requests.get(URL, headers=headers)

print("Status:", response.status_code)
print("Body:", response.text)

if response.status_code == 200:
    print("✅ Token valido e funzionante.")
else:
    print("❌ Errore nel token o permessi insufficienti.")
