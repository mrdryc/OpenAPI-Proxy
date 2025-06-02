#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Client Python per il servizio Company di Openapi

Questo script fornisce funzionalità per autenticarsi e scaricare dati
dal servizio Company di Openapi, con supporto per diversi endpoint e
opzioni di esportazione.
"""

import os
import json
import base64
import argparse
import requests
from datetime import datetime


class OpenApiCompanyClient:
    """Client per interagire con le API Company di Openapi."""

    def __init__(self, environment="production"):
        """
        Inizializza il client.
        
        Args:
            environment (str): Ambiente da utilizzare ('production' o 'sandbox')
        """
        self.token = None
        self.api_key = None
        self.email = None
        
        # Imposta i domini in base all'ambiente
        if environment.lower() == "production":
            self.oauth_domain = "oauth.openapi.it"
            self.company_domain = "company.openapi.com"
        else:
            self.oauth_domain = "test.oauth.openapi.it"
            self.company_domain = "test.company.openapi.com"
    
    def set_credentials(self, email, api_key):
        """
        Imposta le credenziali per l'autenticazione.
        
        Args:
            email (str): Email dell'account Openapi
            api_key (str): API key dell'account
        """
        self.email = email
        self.api_key = api_key
    
    def set_token(self, token):
        """
        Imposta direttamente un token esistente.
        
        Args:
            token (str): Token di autenticazione
        """
        self.token = token
    
    def generate_basic_auth(self):
        """
        Genera l'header di autenticazione Basic.
        
        Returns:
            str: Header di autenticazione in formato Basic
        """
        if not self.email or not self.api_key:
            raise ValueError("Email e API key devono essere impostati prima di generare l'autenticazione")
        
        auth_string = f"{self.email}:{self.api_key}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        return f"Basic {encoded_auth}"
    
    def generate_token(self, scopes=None, ttl_hours=24):
        """
        Genera un nuovo token di accesso.
        
        Args:
            scopes (list): Lista di scope da assegnare al token
            ttl_hours (int): Durata del token in ore
            
        Returns:
            str: Token generato
        """
        if not scopes:
            # Scope predefinito per Company API
            scopes = ["company.openapi.com/marketing"]
        
        url = f"https://{self.oauth_domain}/token"
        
        # Calcola la data di scadenza
        expiry_date = datetime.now().strftime("%Y-%m-%d")
        
        headers = {
            "Authorization": self.generate_basic_auth(),
            "Content-Type": "application/json"
        }
        
        payload = {
            "scopes": scopes,
            "ttl": ttl_hours * 3600  # Converti ore in secondi
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            self.token = result.get("token")
            return self.token
            
        except requests.exceptions.RequestException as e:
            print(f"Errore durante la generazione del token: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Dettagli: {e.response.text}")
            return None
    
    def get_company_data(self, endpoint, **params):
        """
        Ottiene dati aziendali da un endpoint specifico.
        
        Args:
            endpoint (str): Endpoint da chiamare (es. 'IT', 'IT-marketing')
            **params: Parametri di ricerca (vat, fiscalCode, ecc.)
            
        Returns:
            dict: Dati aziendali in formato JSON
        """
        if not self.token:
            raise ValueError("Token non impostato. Utilizzare set_token() o generate_token() prima di effettuare richieste")
        
        url = f"https://{self.company_domain}/{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Errore durante la richiesta all'endpoint {endpoint}: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Dettagli: {e.response.text}")
                print(f"Codice di stato: {e.response.status_code}")
            return None
    
    def save_to_file(self, data, filename, format="json"):
        """
        Salva i dati in un file.
        
        Args:
            data (dict): Dati da salvare
            filename (str): Nome del file
            format (str): Formato del file ('json' o 'txt')
            
        Returns:
            bool: True se il salvataggio è avvenuto con successo
        """
        try:
            if format.lower() == "json":
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(str(data))
            
            print(f"Dati salvati con successo in {filename}")
            return True
            
        except Exception as e:
            print(f"Errore durante il salvataggio del file: {e}")
            return False


def main():
    """Funzione principale per l'esecuzione da riga di comando."""
    
    parser = argparse.ArgumentParser(description='Client Python per il servizio Company di Openapi')
    
    # Argomenti per le credenziali
    parser.add_argument('--email', help='Email dell\'account Openapi')
    parser.add_argument('--api-key', help='API key dell\'account Openapi')
    parser.add_argument('--token', help='Token di autenticazione (se già disponibile)')
    
    # Argomenti per la ricerca
    parser.add_argument('--endpoint', default='IT', help='Endpoint da utilizzare (es. IT, IT-marketing)')
    parser.add_argument('--vat', help='Numero di Partita IVA')
    parser.add_argument('--fiscal-code', help='Codice Fiscale')
    parser.add_argument('--company-number', help='Numero di registrazione aziendale')
    
    # Argomenti per l'output
    parser.add_argument('--output', default='company_data.json', help='Nome del file di output')
    parser.add_argument('--format', default='json', choices=['json', 'txt'], help='Formato del file di output')
    
    # Argomenti per l'ambiente
    parser.add_argument('--env', default='production', choices=['production', 'sandbox'], 
                        help='Ambiente da utilizzare (production o sandbox)')
    
    args = parser.parse_args()
    
    # Crea il client
    client = OpenApiCompanyClient(environment=args.env)
    
    # Gestione dell'autenticazione
    if args.token:
        client.set_token(args.token)
        print(f"Token impostato: {args.token[:10]}...")
    elif args.email and args.api_key:
        client.set_credentials(args.email, args.api_key)
        token = client.generate_token()
        if token:
            print(f"Nuovo token generato: {token[:10]}...")
        else:
            print("Impossibile generare il token. Verifica le credenziali.")
            return
    else:
        print("È necessario fornire un token o le credenziali (email e api-key)")
        return
    
    # Prepara i parametri di ricerca
    search_params = {}
    if args.vat:
        search_params['vat'] = args.vat
    if args.fiscal_code:
        search_params['fiscalCode'] = args.fiscal_code
    if args.company_number:
        search_params['companyNumber'] = args.company_number
    
    if not search_params:
        print("È necessario fornire almeno un parametro di ricerca (vat, fiscal-code, company-number)")
        return
    
    # Esegui la richiesta
    print(f"Richiesta dati all'endpoint {args.endpoint} con parametri: {search_params}")
    data = client.get_company_data(args.endpoint, **search_params)
    
    if data:
        # Salva i risultati
        client.save_to_file(data, args.output, args.format)
    else:
        print("Nessun dato ricevuto.")


if __name__ == "__main__":
    main()