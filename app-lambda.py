import json
import os
import boto3
import requests
from urllib.parse import urlencode

# Load environment variables
TWITTER_CLIENT_ID = os.getenv('TWITTER_CLIENT_ID')
TWITTER_CLIENT_SECRET = os.getenv('TWITTER_CLIENT_SECRET')
TWITTER_CALLBACK_URL = os.getenv('TWITTER_CALLBACK_URL')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DYNAMO_TABLE = os.getenv('DYNAMO_TABLE', 'TwitterTelegramBindings')

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMO_TABLE)

# ✅ Step 1: Redirect to Twitter OAuth 2.0
def lambda_login(event, context):
    query_params = event.get('queryStringParameters', {})
    chat_id = query_params.get('chat_id')

    if not chat_id:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Missing chat_id parameter"})
        }

    # Generate Twitter OAuth 2.0 URL
    twitter_auth_url = (
        f"https://twitter.com/i/oauth2/authorize?"
        f"response_type=code&client_id={TWITTER_CLIENT_ID}"
        f"&redirect_uri={TWITTER_CALLBACK_URL}&scope=tweet.read%20users.read%20offline.access"
        f"&state={chat_id}&code_challenge=challenge&code_challenge_method=plain"
    )

    return {
        "statusCode": 302,
        "headers": {"Location": twitter_auth_url},
        "body": ""
    }

# ✅ Step 2: Handle Twitter OAuth 2.0 Callback
def lambda_callback(event, context):
    query_params = event.get('queryStringParameters', {})
    chat_id = query_params.get('state')
    code = query_params.get('code')

    if not chat_id or not code:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid request"})
        }

    try:
        # ✅ Step 3: Exchange Authorization Code for Access Token
        token_url = "https://api.twitter.com/2/oauth2/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": TWITTER_CALLBACK_URL,
            "code_verifier": "challenge"
        }

        auth = (TWITTER_CLIENT_ID, TWITTER_CLIENT_SECRET)
        response = requests.post(token_url, data=data, auth=auth)

        if response.status_code != 200:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Failed to get access token"})
            }

        access_token = response.json().get("access_token")

        # ✅ Step 4: Get Twitter User Profile
        user_response = requests.get(
            "https://api.twitter.com/2/users/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if user_response.status_code != 200:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Failed to get Twitter profile"})
            }

        twitter_data = user_response.json()
        twitter_handle = twitter_data['data']['username']

        # ✅ Step 5: Store in DynamoDB
        table.put_item(Item={
            "chat_id": chat_id,
            "twitter_handle": twitter_handle,
            "access_token": access_token
        })

        # ✅ Step 6: Send Success Message to Telegram
        send_message_to_telegram(chat_id, f"✅ Successfully linked your Twitter account (@{twitter_handle}).")

        return {
            "statusCode": 200,
            "body": json.dumps({"success": True, "message": f"Twitter account (@{twitter_handle}) linked to Telegram."})
        }

    except Exception as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }

# ✅ Send Telegram Message After Binding
def send_message_to_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

# ✅ Step 7: Lambda Handler (AWS API Gateway Routes)
def lambda_handler(event, context):
    if event['path'] == "/login":
        return lambda_login(event, context)
    elif event['path'] == "/callback":
        return lambda_callback(event, context)

    return {
        "statusCode": 404,
        "body": json.dumps({"error": "Route not found"})
    }
