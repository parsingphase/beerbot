import boto3
import json
import re
import requests
import stock_check
import imbibed

from botocore.exceptions import ClientError
from email.parser import Parser as EmailParser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from io import StringIO
from typing import Optional, List

S3_BUCKET = 'org.phase.beerbot.mail.incoming'

EXPORT_TYPE_LIST = 'list'
EXPORT_TYPE_CHECKINS = 'checkins'


# noinspection PyUnusedLocal
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
            download_link = detect_download_link(message_text)

            if export_type:
                r = requests.get(download_link)
                export_data = r.content.decode('utf-8')  # string
                loaded_data = json.loads(export_data)

                if export_type == EXPORT_TYPE_LIST:
                    stocklist_buffer = StringIO()
                    styles_buffer = StringIO()
                    stock_check.build_dated_stocklist(
                        loaded_data,
                        stocklist_output=stocklist_buffer,
                        styles_output=styles_buffer)
                    body = 'BeerBot found a list export in your email and generated a stock list, attached below.'
                    stock_list = make_attachment(stocklist_buffer, 'beerbot-stocklist.csv', 'text/csv')
                    style_summary = make_attachment(styles_buffer, 'beerbot-list-summary.csv', 'text/csv')
                    send_email_response(reply_to, body, [stock_list, style_summary])

                elif export_type == EXPORT_TYPE_CHECKINS:
                    weekly_buffer = StringIO()
                    styles_buffer = StringIO()
                    imbibed.analyze_checkins(loaded_data, weekly_output=weekly_buffer, styles_output=styles_buffer)
                    body = 'BeerBot found a check-in export in your email and created summaries by week & style,' \
                           ' attached below.\n\n'
                    body += 'Note on "estimated" field: ' \
                            '* = Some measures guessed from serving. ** = some servings missing'
                    weekly = make_attachment(weekly_buffer, 'beerbot-weekly-summary.csv', 'text/csv')
                    styles = make_attachment(styles_buffer, 'beerbot-checkin-styles.csv', 'text/csv')
                    send_email_response(reply_to, body, [weekly, styles])

            else:
                raise Exception('Unfamiliar export type: "%s"' % export_type)


def detect_download_link(message_text: str) -> Optional[str]:
    """
    Find the download link in a forwarded message
    Args:
        message_text:

    Returns:
        url
    """
    download_link_match = re.search('You can download your data export here: (https:\S+)', message_text)
    download_link = download_link_match[1]
    return download_link


def detect_export_type(message_text: str) -> Optional[str]:
    """
    Work out from message text what sort of import we've got
    Args:
        message_text:

    Returns:
        EXPORT_TYPE_*
    """
    export_match = re.search('you requested an export of ([-\w ]+) on Untappd', message_text)
    export_description = export_match[1]  # 'a list' or 'your check-ins'
    if export_description == 'a list':
        export_type = EXPORT_TYPE_LIST
    elif export_description == 'your check-ins':
        export_type = EXPORT_TYPE_CHECKINS
    else:
        raise Exception('Export type cannot be detected')

    return export_type


def send_email_response(to: str, action_message: str, files: List[MIMEApplication]):
    """

    Args:
        to: Recipient address
        action_message: Description of what's been processed
        files: List of mime attachments

    Returns:

    """
    client = boto3.client('ses')
    sender = 'BeerBot at Phase.org <no-reply@beerbot.phase.org>'
    title = 'Your Untappd submission to BeerBot'

    print('Sending message to %s' % to)

    msg = MIMEMultipart()
    msg['Subject'] = title
    msg['From'] = sender

    body = action_message + '''

BeerBot was created by @parsingphase (https://untappd.com/user/parsingphase).

Contribute to caffeinated coding at https://ko-fi.com/parsingphase

'''
    part = MIMEText(body)
    msg.attach(part)

    for part in files:
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


def make_attachment(file_data: StringIO, filename: str = None, mime_type: str = 'application/csv') -> MIMEApplication:
    part = MIMEApplication(file_data.getvalue(), mime_type.split('/')[1])
    if filename is None:
        filename = 'beerbot-export.csv'
    part.add_header('Content-Disposition', 'attachment', filename=filename)
    return part
