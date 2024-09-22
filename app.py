import flask
from flask import request
import os
import json
import boto3
from bot import ObjectDetectionBot, Bot
from botocore.exceptions import ClientError
from loguru import logger
import ssl

# Load SSL Certificates
context = ssl.SSLContext(ssl.PROTOCOL_TLS)
context.load_cert_chain(certfile='/usr/src/app/tls.crt', keyfile='/usr/src/app/tls.key')

secret_name = os.environ['secret_name']
TELEGRAM_APP_URL = os.environ['TELEGRAM_APP_URL']



def get_secret():
    region_name = "eu-west-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e
    else:
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            secret_dict = json.loads(secret)  # Convert the string to a dictionary
            token_value = secret_dict.get('token')  # Get the value corresponding to the 'token' key

            # Print the extracted token value
            return token_value


app = flask.Flask(__name__)

# Load TELEGRAM_TOKEN value from Secret Manager
TELEGRAM_TOKEN = get_secret()
logger.info(f"TELEGRAM_TOKEN IS : {TELEGRAM_TOKEN}")

TELEGRAM_APP_URL = os.getenv('TELEGRAM_APP_URL')  # Use os.getenv for environment variable access
logger.info(f"TELEGRAM_APP_URL IS : {TELEGRAM_APP_URL}")


@app.route('/', methods=['GET'])
def index():
    return 'Ok'


@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    logger.info(f"Received webhook data: {req}")
    bot.handle_message(req['message'])
    return 'Ok'




@app.route('/results', methods=['POST'])
def results():
    prediction_id = request.args.get('predictionId')
    logger.info(f"your prediction id: {prediction_id}")

    dynamodb = boto3.resource('dynamodb', region_name='eu-west-3')
    table = dynamodb.Table('loay-PolybotService-DynamoDB-tf')

    try:
        response = table.get_item(Key={'prediction_id': prediction_id})

        if 'Item' in response:
            results = response['Item']
            logger.info(f"Results retrieved successfully: {results}")

            my_chat_id = str(results['chat_id'])
            logger.info(f"your chat id: {my_chat_id}")

            if not results.get('labels'):
                message = "No prediction: empty labels"
                bot_send_text = Bot(TELEGRAM_TOKEN, TELEGRAM_APP_URL)
                bot_send_text.send_text(my_chat_id, message)
            else:
                labels = results['labels']
                class_counts = {}
                for label in labels:
                    class_name = label['class']
                    if class_name in class_counts:
                        class_counts[class_name] += 1
                    else:
                        class_counts[class_name] = 1

                message = "Prediction ID: {}\n\nClass Counts:\n".format(results['prediction_id'])
                for class_name, count in class_counts.items():
                    message += f"{class_name}: {count}\n"

                bot_send_text = Bot(TELEGRAM_TOKEN, TELEGRAM_APP_URL)
                bot_send_text.send_text(my_chat_id, message)

            return results
        else:
            logger.info("No results found for the given prediction_id")
    except Exception as e:
        logger.error(f"Error retrieving results from DynamoDB: {str(e)}")

    return "Error: The provided key element does not match the schema"


@app.route('/loadTest/', methods=['POST'])
def load_test():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


if __name__ == "__main__":
    bot = ObjectDetectionBot(TELEGRAM_TOKEN, TELEGRAM_APP_URL)

    # Start Flask application with SSL context
    app.run(host='0.0.0.0', port=8443)
