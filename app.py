from flask import Flask, redirect, url_for, session, request, jsonify, render_template_string
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os
import json

app = Flask(__name__)
app.secret_key = 'YOUR_SECRET_KEY'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # for development only

# Load credentials from the credentials.json file
with open('credentials.json', 'r') as f:
    credentials_info = json.load(f)['web']

# Set the scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Get the port from environment variable or default to 8080
port = int(os.environ.get('PORT', 8080))
REDIRECT_URI = f'http://localhost:{port}/oauth2callback'

@app.route('/')
def index():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

    credentials = Credentials(**session['credentials'])
    service = build('gmail', 'v1', credentials=credentials)

    results = service.users().messages().list(userId='me', maxResults=10).execute()
    messages = results.get('messages', [])

    emails = []
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        emails.append(msg)

    session['credentials'] = credentials_to_dict(credentials)
    
    return render_template_string("""
        <h1>Emails</h1>
        <ul>
        {% for email in emails %}
            <li>{{ email['snippet'] }}</li>
        {% endfor %}
        </ul>
        """, emails=emails)

@app.route('/authorize')
def authorize():
    flow = Flow.from_client_config(
        {'web': credentials_info},
        scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )

    session['state'] = state

    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_config(
        {'web': credentials_info},
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = REDIRECT_URI

    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials
    session['credentials'] = credentials_to_dict(credentials)

    return redirect(url_for('index'))

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
