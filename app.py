from flask import Flask, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
import os

app = Flask(__name__)

# Load environment variables
app.secret_key = os.getenv('DB_SECRET_KEY')

# Set the database URI
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(basedir, 'users.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)

# Twitter API Keys (OAuth 2.0)
TWITTER_CLIENT_ID = os.getenv('TWITTER_CLIENT_ID')
TWITTER_CLIENT_SECRET = os.getenv('TWITTER_CLIENT_SECRET')
TWITTER_CALLBACK_URL = os.getenv('TWITTER_CALLBACK_URL')

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv('API_KEY')


# ✅ Database Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String(20), unique=True, nullable=False)
    twitter_handle = db.Column(db.String(100), nullable=False)
    access_token = db.Column(db.String(200), nullable=False)


# ✅ Step 1: Redirect User to Twitter OAuth 2.0 Login
@app.route('/login', methods=['GET'])
def login():
    chat_id = request.args.get('chat_id')
    if not chat_id:
        return "❌ Error: No chat_id provided.", 400

    # Generate the OAuth 2.0 authorization URL
    url = f"https://twitter.com/i/oauth2/authorize?response_type=code&client_id={TWITTER_CLIENT_ID}&redirect_uri={TWITTER_CALLBACK_URL}&scope=tweet.read%20users.read%20offline.access&state={chat_id}&code_challenge=challenge&code_challenge_method=plain"
    return redirect(url)


# ✅ Step 2: Handle Twitter OAuth 2.0 Callback
@app.route('/callback', methods=['GET'])
def callback():
    # Retrieve chat_id from the 'state' parameter (which we passed)
    chat_id = request.args.get('state')
    code = request.args.get('code')

    if not code or not chat_id:
        return "❌ Error: Invalid request.", 400

    # ✅ Step 3: Exchange Authorization Code for Access Token
    token_url = "https://api.twitter.com/2/oauth2/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": TWITTER_CALLBACK_URL,
        "code_verifier": "challenge"
    }

    # Use HTTP Basic Authentication
    auth = (TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET)

    # Debug: Print the request payload
    print("Token Exchange Request Payload:", data)
    print("Using Client ID:", TWITTER_CLIENT_ID)

    response = requests.post(token_url, data=data, auth=auth)
    
    # Debug: Print the response
    print("Token Exchange Response Status Code:", response.status_code)
    print("Token Exchange Response Body:", response.text)

    if response.status_code != 200:
        return "❌ Error: Failed to get access token.", 400

    # ✅ Step 4: Get Access Token
    token_response = response.json()
    access_token = token_response['access_token']

    # ✅ Step 5: Get Twitter User Profile (Twitter Handle)
    user_response = requests.get(
        "https://api.twitter.com/2/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if user_response.status_code != 200:
        return "❌ Error: Failed to get Twitter profile.", 400

    twitter_data = user_response.json()
    twitter_handle = twitter_data['data']['username']

    # ✅ Step 6: Store in Database (Auto-Bind Telegram ↔ Twitter)
    existing_user = User.query.filter_by(chat_id=chat_id).first()
    if existing_user:
        existing_user.twitter_handle = twitter_handle
        existing_user.access_token = access_token
    else:
        new_user = User(
            chat_id=chat_id,
            twitter_handle=twitter_handle,
            access_token=access_token
        )
        db.session.add(new_user)

    db.session.commit()

    # ✅ Step 7: Send Success Message to Telegram
    send_message_to_telegram(chat_id, f"✅ Successfully linked your Twitter account (@{twitter_handle}).")

    # ✅ Step 8: Return Success Page
    return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Success! ✅</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f8fb;
                    text-align: center;
                    padding: 50px;
                }}
                .container {{
                    max-width: 500px;
                    margin: auto;
                    padding: 20px;
                    background: white;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                    border-radius: 10px;
                }}
                h2 {{
                    color: #1DA1F2;
                }}
                p {{
                    font-size: 18px;
                    color: #333;
                }}
                .icons {{
                    font-size: 50px;
                    margin: 20px 0;
                }}
                .icons i {{
                    margin: 0 10px;
                    color: #1DA1F2;
                }}
                .back-btn {{
                    display: inline-block;
                    margin-top: 20px;
                    padding: 10px 20px;
                    color: white;
                    background-color: #1DA1F2;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                }}
                .back-btn:hover {{
                    background-color: #0c85d0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>✅ Success!</h2>
                <div class="icons">🐦 🔗 💬</div>
                <p>Your Twitter account <b>@{twitter_handle}</b> has been linked to your Telegram.</p>
                <p>You will now receive tweets directly in Telegram!</p>
                <a class="back-btn" href="https://t.me/DeepXVBot">Go to Telegram</a>
            </div>
        </body>
        </html>
        """


# ✅ Send Telegram Message After Binding
def send_message_to_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)


# ✅ Test Route
@app.route('/', methods=['GET'])
def home():
    return "✅ Telegram ↔ Twitter Bot (OAuth 2.0) is running!"


# ✅ Automatically Create Database (Fix)
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)
