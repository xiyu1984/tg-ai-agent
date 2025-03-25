import { APIGatewayProxyEvent, APIGatewayProxyResult } from "aws-lambda";
import axios from "axios";
import AWS from "aws-sdk";
import * as dotenv from "dotenv";

dotenv.config();

// AWS DynamoDB setup
const dynamoDB = new AWS.DynamoDB.DocumentClient();
const TABLE_NAME = process.env.DYNAMO_TABLE || "TwitterTelegramBindings";

// Twitter OAuth 2.0 Credentials
const TWITTER_CLIENT_ID = process.env.TWITTER_CLIENT_ID!;
const TWITTER_CLIENT_SECRET = process.env.TWITTER_CLIENT_SECRET!;
const TWITTER_CALLBACK_URL = process.env.TWITTER_CALLBACK_URL!;

// Telegram Bot Token
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN!;

// ✅ Step 1: Redirect to Twitter OAuth 2.0
export const lambdaLogin = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
    const chatId = event.queryStringParameters?.chat_id;
    if (!chatId) {
        return {
            statusCode: 400,
            body: JSON.stringify({ error: "Missing chat_id parameter" }),
        };
    }

    // Generate Twitter OAuth 2.0 URL
    const twitterAuthUrl = `https://twitter.com/i/oauth2/authorize?response_type=code&client_id=${TWITTER_CLIENT_ID}&redirect_uri=${TWITTER_CALLBACK_URL}&scope=tweet.read%20users.read%20offline.access&state=${chatId}&code_challenge=challenge&code_challenge_method=plain`;

    return {
        statusCode: 302,
        headers: { Location: twitterAuthUrl },
        body: "",
    };
};

// ✅ Step 2: Handle Twitter OAuth 2.0 Callback
export const lambdaCallback = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
    const chatId = event.queryStringParameters?.state;
    const code = event.queryStringParameters?.code;

    if (!chatId || !code) {
        return {
            statusCode: 400,
            body: JSON.stringify({ error: "Invalid request" }),
        };
    }

    try {
        // ✅ Step 3: Exchange Authorization Code for Access Token
        const tokenResponse = await axios.post(
            "https://api.twitter.com/2/oauth2/token",
            new URLSearchParams({
                grant_type: "authorization_code",
                code: code,
                redirect_uri: TWITTER_CALLBACK_URL,
                code_verifier: "challenge",
            }).toString(),
            {
                auth: { username: TWITTER_CLIENT_ID, password: TWITTER_CLIENT_SECRET },
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
            }
        );

        const accessToken = tokenResponse.data.access_token;

        // ✅ Step 4: Get Twitter User Profile
        const userResponse = await axios.get("https://api.twitter.com/2/users/me", {
            headers: { Authorization: `Bearer ${accessToken}` },
        });

        const twitterHandle = userResponse.data.data.username;

        // ✅ Step 5: Store in DynamoDB
        await dynamoDB
            .put({
                TableName: TABLE_NAME,
                Item: {
                    chatId: chatId,
                    twitterHandle: twitterHandle,
                    accessToken: accessToken,
                },
            })
            .promise();

        // ✅ Step 6: Send Success Message to Telegram
        await sendTelegramMessage(chatId, `✅ Successfully linked your Twitter account (@${twitterHandle}).`);

        return {
            statusCode: 200,
            body: JSON.stringify({ success: true, message: `Twitter account (@${twitterHandle}) linked to Telegram.` }),
        };
    } catch (error: any) {
        return {
            statusCode: 400,
            body: JSON.stringify({ error: "Failed to authenticate with Twitter", details: error.message }),
        };
    }
};

// ✅ Step 7: Send Telegram Message After Binding
const sendTelegramMessage = async (chatId: string, text: string) => {
    await axios.post(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
        chat_id: chatId,
        text: text,
    });
};

// ✅ Step 8: Lambda Handler (AWS API Gateway Routes)
export const handler = async (event: APIGatewayProxyEvent): Promise<APIGatewayProxyResult> => {
    if (event.path === "/login") return lambdaLogin(event);
    if (event.path === "/callback") return lambdaCallback(event);

    return { statusCode: 404, body: JSON.stringify({ error: "Route not found" }) };
};
