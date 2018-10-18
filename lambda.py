import boto3
import email
import quopri

S3_BUCKET = 'org.phase.beerbot.mail.incoming'


def lambda_handler(event, context):
    client = boto3.client("s3")

    for record in event['Records']:
        if 'ses' in record:
            message_id = record['ses']['mail']['messageId']
            result = client.get_object(Bucket=S3_BUCKET, Key=message_id)
            # Read the object (not compressed):
            text = result["Body"].read().decode()
            parser = email.parser.Parser()
            message = parser.parsestr(text)
            message_payload = None
            # AWS returns old Message format: https://docs.python.org/3.6/library/email.compat32-message.html
            if message.is_multipart():
                payloads = message.get_payload()
                for payload in payloads:
                    if payload.get_content_type() == 'text/plain':
                        message_payload = payload
                        break
            else:
                message_payload = message

            if not message_payload:
                raise Exception('Cannot find message')

            print(message_payload.get_payload(decode=True).decode('utf-8'))
