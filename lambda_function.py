import json
import logging
import re
from datetime import datetime, timedelta
from email import encoders
from email.message import Message
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.parser import Parser as EmailParser
from hashlib import sha256
from io import StringIO
from typing import List, Optional

import boto3
import requests
from botocore.exceptions import ClientError

import daily_visualisation
import imbibed
import stock_check
from bot_version import version
from utils import build_csv_from_list, debug_print, get_config


EXPORT_TYPE_LIST = 'list'
EXPORT_TYPE_CHECKINS = 'checkins'


# noinspection PyUnusedLocal
def lambda_handler(event, context):
    logger = logging.getLogger()
    logger.setLevel(logging.WARN)

    for record in event['Records']:
        if 'ses' in record:

            mail_data = record['ses']['mail']
            headers = mail_data['commonHeaders']
            reply_to = headers['returnPath'] if 'returnPath' in headers else mail_data['source']
            message_id = mail_data['messageId']

            try:
                message_payload = fetch_message_from_bucket(message_id)

                if not message_payload:
                    raise Exception('Incoming message could not be loaded')

                message_text = message_payload.get_payload(decode=True).decode('utf-8')
                export_type = detect_export_type(message_text)
                download_link = detect_download_link(message_text)

                if export_type:
                    r = requests.get(download_link)
                    export_data = r.content.decode('utf-8')  # string
                    loaded_data = json.loads(export_data)

                    if export_type == EXPORT_TYPE_LIST:
                        subject = headers['subject'] if 'subject' in headers else ''
                        subject_match = re.search(r'List:\s*(\w.*)', subject)
                        list_name = subject_match[1]
                        if list_name:
                            list_name = list_name.strip()
                        process_list_export(loaded_data, reply_to, list_name)

                    elif export_type == EXPORT_TYPE_CHECKINS:
                        process_checkins_export(loaded_data, reply_to)

                else:
                    exception_message = 'Unfamiliar export type: "%s"' % export_type
                    logger.error(exception_message)
                    raise Exception(exception_message)

            except Exception as e:
                error_message = 'BeerBot had a problem handling your message:\n\n' \
                                ' Here\'s a hint to the problem: %s %s' % (type(e), e)
                send_email_response(reply_to, error_message)
                if get_config('debug'):
                    raise e


def process_checkins_export(loaded_data: list, reply_to: str):
    """
    Process loaded checkin export data to create an email containing appropriate reports
    Args:
        loaded_data: Unpacked JSON data
        reply_to: Address email was submitted from

    Returns:

    """
    weekly_buffer = StringIO()
    styles_buffer = StringIO()
    breweries_buffer = StringIO()
    image_buffer = StringIO()

    daily = {}
    weekly = {}
    styles = {}
    breweries = {}

    imbibed.build_checkin_summaries(
        loaded_data,
        daily=daily,
        weekly=weekly,
        styles=styles,
        breweries=breweries,
    )

    imbibed.write_weekly_summary(weekly, weekly_buffer)
    imbibed.write_styles_summary(styles, styles_buffer)
    imbibed.write_breweries_summary(breweries, breweries_buffer)

    count_all_checkins = len(daily.keys())
    count_with_measure = len([1 for d in daily if 'beverage_ml' in daily[d]])

    if count_with_measure > (count_all_checkins / 3):
        measure = 'units'
    else:
        measure = 'drinks'

    print('%d measures in %d checkins, visualising %s' % (count_with_measure, count_all_checkins, measure))

    image = daily_visualisation.build_daily_visualisation_image(
        daily,
        measure=measure,
        show_legend=True
    )

    image.write(image_buffer, True)

    body = 'BeerBot found a check-in export in your email and' \
           ' created the following summaries:\n\n' \
           ' bb-checkin-summary.csv: summarises consumption and score by week\n' \
           ' bb-checkin-styles.csv: styles you\'ve checked in, most common first\n' \
           ' bb-checkin-breweries.csv: average score by brewery of all checkins & unique beers \n\n' \
           'plus a visualisation of your consumption over time in bb-units-vis.svg \n\n' \
           'bb-checkin-summary.csv may contain notes on estimated consumption: \n' \
           '* = Some measures guessed from serving. \n' \
           '** = Some beers skipped due to no serving or measure\n'
    attachments = [
        make_attachment(image_buffer, 'bb-units-vis.svg', 'image/svg+xml', disposition='inline'),
        make_attachment(weekly_buffer, 'bb-checkin-summary.csv', 'text/csv'),
        make_attachment(styles_buffer, 'bb-checkin-styles.csv', 'text/csv'),
        make_attachment(breweries_buffer, 'bb-checkin-breweries.csv', 'text/csv'),
    ]
    send_email_response(reply_to, body, attachments)


def process_list_export(loaded_data: list, reply_to: str, list_name: str = None):
    """
    Process loaded list export data to create an email containing appropriate reports, and an uploaded HTML version

    Args:
        list_name: Optional list name to store under
        loaded_data: Unpacked JSON data
        reply_to: Address email was submitted from

    Returns:

    """
    stocklist = []
    stocklist_styles = []
    stock_check.build_stocklists(
        loaded_data,
        stocklist=stocklist,
        style_summary=stocklist_styles
    )
    stocklist_buffer_csv = StringIO()
    styles_buffer_csv = StringIO()
    build_csv_from_list(stocklist, stocklist_buffer_csv)
    build_csv_from_list(stocklist_styles, styles_buffer_csv)
    del stocklist_styles
    body = 'BeerBot found a list export in your email and generated a stock list and' \
           ' summary of styles, attached below.'
    attachments = [
        make_attachment(stocklist_buffer_csv, 'bb-stocklist.csv', 'text/csv'),
        make_attachment(styles_buffer_csv, 'bb-stocklist-summary.csv', 'text/csv'),
    ]
    del stocklist_buffer_csv
    del styles_buffer_csv
    stocklist_buffer_html = StringIO()
    stock_check.build_html_from_list(stocklist, stocklist_buffer_html, list_name)
    uploaded_to = upload_report_to_s3(
        stocklist_buffer_html,
        filename='sl' if list_name is None else list_name,
        source_address=reply_to,
        expiry_days=get_config('upload_expiry_days')
    )
    if uploaded_to:
        body += '\n\nYour list was also uploaded to a private location at %s' % uploaded_to
        body += '\nThis location will remain constant for all future submissions from your email '
        body += 'address, so feel free to bookmark it.'

        if list_name is None:
            body += '\nHint: Forward your message with a subject of "List: YOUR CHOICE" to save it under that name.'

    send_email_response(reply_to, body, attachments)


def upload_report_to_s3(buffer: StringIO, filename: str, source_address: str, expiry_days: int = None) -> str:
    """
    Upload a file to the S3 bucket
    Args:
        buffer: StringIO buffer containing file data
        filename: Name of the file to save
        source_address: Email address of the file's submitter
        expiry_days: Numbed of days in future for file expiry date, if any

    Returns:
        URL of uploaded file
    """
    destination = None

    secret = get_config('secret')
    upload_bucket = get_config('upload_bucket')
    upload_web_root = get_config('upload_web_root')

    if secret and upload_bucket and upload_web_root:
        s3_resource = boto3.resource('s3')
        bucket = s3_resource.Bucket(upload_bucket)
        path = sha256((get_config('secret') + '/' + source_address.lower()).encode('utf8')).hexdigest()[0:20]
        relative_path = path + '/' + filename
        expires = (datetime.now() + timedelta(expiry_days)) if expiry_days is not None else None
        bucket.put_object(
            Body=buffer.getvalue(),
            Key=relative_path,
            GrantRead='uri="http://acs.amazonaws.com/groups/global/AllUsers"',
            ContentType='text/html',
            Expires=expires,
            Tagging='ReportType=Stocklist',
        )
        url_path = relative_path.replace(' ', '+')
        invalidate_path_cache('/' + url_path)
        destination = upload_web_root + url_path
        debug_print('Upload to s3: %s, url: %s, expiry %s' % (relative_path, url_path, expires))
    else:
        print('No upload dest specified, so no HTML storage')

    return destination


def fetch_message_from_bucket(message_id: str) -> Message:
    """
    Download the saved email from out local S3 and extract the relevant Message part from it
    Args:
        message_id:

    Returns:

    """
    source_bucket = get_config('incoming_email_bucket')
    if not source_bucket:
        raise Exception('config { "incoming_email_bucket" } must be specified')

    client = boto3.client("s3")
    result = client.get_object(Bucket=source_bucket, Key=message_id)
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
    return message_payload


def detect_download_link(message_text: str) -> Optional[str]:
    """
    Find the download link in a forwarded message
    Args:
        message_text:

    Returns:
        url
    """
    download_link_match = re.search(r'You can download your data export here: (https:\S+)', message_text)
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
    export_match = re.search(r'you requested an export of ([-\w ]+) on Untappd', message_text)
    export_description = export_match[1] if export_match is not None else ''  # 'a list' or 'your check-ins'
    if export_description == 'a list':
        export_type = EXPORT_TYPE_LIST
    elif export_description == 'your check-ins':
        export_type = EXPORT_TYPE_CHECKINS
    else:
        raise Exception('Export type cannot be detected')

    return export_type


def send_email_response(to: str, action_message: str, files: List[MIMEApplication] = None):
    """

    Args:
        to: Recipient address
        action_message: Description of what's been processed
        files: List of mime attachments

    Returns:

    """
    if not files:
        files = []

    client = boto3.client('ses')
    sender = get_config('reply_from', 'BeerBot at Phase.org <no-reply@beerbot.phase.org>')
    title = 'Your Untappd submission to BeerBot'

    print('Sending message to %s' % to)

    msg = MIMEMultipart()
    msg.add_header('X-BEERBOT-VERSION', version)
    msg['Subject'] = title
    msg['From'] = sender

    body = action_message + '''

BeerBot was created by @parsingphase (https://untappd.com/user/parsingphase).
Contribute to caffeinated coding at https://ko-fi.com/parsingphase

This report was created by "%s"

''' % version

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
        print("Email sent! Message ID:", response['MessageId'])


def make_attachment(file_data: StringIO, filename: str, mime_type: str, disposition='attachment') -> MIMEApplication:
    """
    Convert buffer into a MIME file attachment

    Args:
        disposition:
        file_data: buffer data
        filename: Filename for attachment
        mime_type: Content type, treated as application/*

    Returns:
        MIMEApplication part
    """
    mime_parts = mime_type.split('/')
    type = mime_parts[0]
    subtype = mime_parts[1]

    if type == 'text':
        part = MIMEApplication(file_data.getvalue(), subtype, _encoder=encoders.encode_noop)
        # Very annoying error on AWS above:
        # encode_base64 and encode_quopri both escape 3+byte unicode chars (above \u00ff) back to \u*** format
        # So - as we're sending UTF8 CSVs only at the moment, we just send them unencoded
        # - and accept the 'alternative' application/csv mimetype
    elif type == 'image':
        part = MIMEImage(file_data.getvalue(), subtype)
    else:
        raise Exception('Unsupported mime supertype %s' % type)

    part.add_header('Content-Disposition', disposition, filename=filename)
    part.add_header('Content-ID', '<%s>' % filename)

    return part


def invalidate_path_cache(path: str):
    """
    Create a CDN invalidation for the specified path

    Args:
        path: distribution-relative path to the file to be invalidated

    Returns:

    """
    cdn_id = get_config('cdn_distribution_id')
    if cdn_id:
        debug_print('Invalidate "%s" in "%s"' % (path, cdn_id))
        try:
            client = boto3.client('cloudfront')
            reference = datetime.now().strftime('%Y%m%d%H%M%S')
            invalidation = client.create_invalidation(
                DistributionId=cdn_id,
                InvalidationBatch={
                    'Paths': {
                        'Quantity': 1,
                        'Items': [path]
                    },
                    'CallerReference': 'beerbot_upload_' + reference
                }
            )
            print({'invalidation': invalidation})
            debug_print('end invalidation')
        except Exception as e:
            print({'invalidation: Exception': e})
