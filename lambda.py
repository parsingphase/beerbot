import boto3
import json
import re
import requests
import stock_check

from botocore.exceptions import ClientError
from email.parser import Parser as EmailParser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from io import StringIO
from typing import Optional

S3_BUCKET = 'org.phase.beerbot.mail.incoming'

EXPORT_TYPE_LIST = 'list'
EXPORT_TYPE_CHECKINS = 'checkins'


def lambda_handler(event, context):
    client = boto3.client("s3")

    for record in event['Records']:
        if 'ses' in record:

            mail_data = record['ses']['mail']
            headers = mail_data['commonHeaders']
            reply_to = headers['returnPath'] if 'returnPath' in headers else mail_data['source']
            message_id = mail_data['messageId']

            result = client.get_object(Bucket=S3_BUCKET, Key=message_id)
            # Read the object (not compressed):
            text = result["Body"].read().decode()
            parser = EmailParser()
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

            export_type = detect_export_type(message_text)

            download_link_match = re.search('You can download your data export here: (https:\S+)', message_text)

            download_link = download_link_match[1]

            r = requests.get(download_link)
            export_data = r.content.decode('utf-8')  # string

            if export_type == EXPORT_TYPE_LIST:
                csv_buffer = StringIO()
                stock_check.build_dated_list_summary(json.loads(export_data), csv_buffer)
                body = 'BeerBot found a list export in the email you sent and has used it to generate a stock list.'
                send_email_response(reply_to, body, csv_buffer, 'beerbot-stocklist.csv')

            else:
                raise Exception('Unfamiliar export type: "%s"' % export_type)


def detect_export_type(message_text: str) -> Optional[str]:
    """
    Work out from message text what sort of import we've got
    Args:
        message_text:

    Returns:
        EXPORT_TYPE_*
    """
    export_match = re.search('you requested an export of ([\w ]+) on Untappd', message_text)
    export_description = export_match[1]  # 'a list' or 'your check-ins'
    if export_description == 'a list':
        export_type = EXPORT_TYPE_LIST
    elif export_description == 'your checkins':
        export_type = EXPORT_TYPE_CHECKINS
    else:
        raise Exception('Export type cannot be detected')

    return export_type


def send_email_response(to: str, action_message: str, attachment: StringIO = None, filename: str = None):
    """

    Args:
        to: Recipient address
        action_message: Description of what's been processed
        attachment: String buffer containing generated CSV data
        filename: optional download filename

    Returns:

    """
    client = boto3.client('ses')
    sender = 'BeerBot at Phase.org <no-reply@beerbot.phase.org>'
    title = 'Your Untappd submission to BeerBot'

    print('Sending message to %s' % to)

    msg = MIMEMultipart()
    msg['Subject'] = title
    msg['From'] = sender

    body = action_message + ''' This file is attached below.

BeerBot was created by @parsingphase (https://twitter.com/parsingphase, https://untappd.com/user/parsingphase)

'''
    part = MIMEText(body)
    msg.attach(part)

    part = MIMEApplication(attachment.getvalue(), 'csv')
    if filename is None:
        filename = 'beerbot-export.csv'

    part.add_header('Content-Disposition', 'attachment', filename=filename)
    msg.attach(part)

    try:
        # Provide the contents of the email.
        response = client.send_raw_email(
            Destinations=[to],
            RawMessage={
                'Data': msg.as_string()
            },
            Source=sender
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
