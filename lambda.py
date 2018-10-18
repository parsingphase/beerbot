import boto3
import email
import re

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

            message_text = message_payload.get_payload(decode=True).decode('utf-8')
            print(message_text)

            export_type_match = re.search('you requested an export of ([\w ]+) on Untappd', message_text)
            download_link_match = re.search('You can download your data export here: (https:\S+)', message_text)

            export_type = export_type_match[1]
            download_link = download_link_match[1]


'''
> Recently, you requested an export of a list on Untappd. Good news - your export is ready!
> Recently, you requested an export of your check-ins on Untappd. Good news - your export is ready!
> 
> You can download your data export here: https://untappd-user-exports.s3.amazonaws.com/123456/3cbe3f16f4cbaa962cf4f98a999f2030.json <https://untappd-user-exports.s3.amazonaws.com/3357624/3cbe3f16f4cbaa962cf4f98a999f2030.json>
'''
