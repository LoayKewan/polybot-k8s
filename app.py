import flask
from flask import request
import os
from bot import ObjectDetectionBot
from bot import Bot
import json
import boto3
from botocore.exceptions import ClientError
from loguru import logger
from decimal import Decimal


def get_secret():
    secret_name = "loaytokensecret-for-amz-prolect"
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
            return (token_value)


app = flask.Flask(__name__)

# TODO load TELEGRAM_TOKEN value from Secret Manager
TELEGRAM_TOKEN = get_secret()

TELEGRAM_APP_URL = os.environ['TELEGRAM_APP_URL']


@app.route('/', methods=['GET'])
def index():
    return 'Ok'


@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
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
            logger.info("my_chat_id retrieved successfully ******loay************")

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


@app.route(f'/loadTest/', methods=['POST'])
def load_test():
    req = request.get_json()
    bot.handle_message(req['message'])
    return 'Ok'


if __name__ == "__main__":
    bot = ObjectDetectionBot(TELEGRAM_TOKEN, TELEGRAM_APP_URL)

    app.run(host='0.0.0.0', port=8443)
