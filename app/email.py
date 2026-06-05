from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from . import mail
import os
import smtplib
import time
import logging

logger = logging.getLogger(__name__)

def send_async_email(app, msg, max_retries=3, retry_delay=5):
    with app.app_context():
        for attempt in range(max_retries):
            try:
                mail.send(msg)
                logger.info(f'Email sent successfully to {msg.recipients}')
                print('msg========================')
                return
            except smtplib.SMTPConnectError as e:
                if attempt < max_retries - 1:
                    logger.warning(f'SMTP connection failed (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {retry_delay} seconds...')
                    time.sleep(retry_delay)
                else:
                    logger.error(f'Failed to send email after {max_retries} attempts: {e}')
                    logger.error(f'Recipients: {msg.recipients}, Subject: {msg.subject}')
            except smtplib.SMTPException as e:
                logger.error(f'SMTP error occurred while sending email: {e}')
                logger.error(f'Recipients: {msg.recipients}, Subject: {msg.subject}')
                return
            except Exception as e:
                logger.error(f'Unexpected error occurred while sending email: {e}')
                logger.error(f'Recipients: {msg.recipients}, Subject: {msg.subject}')
                return

def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender='NoReply@lab.tools.com', recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

def send_cdu_email(to, subject, template, logs,**kwargs):
    Attachment = 'logs/system.log'
    Attachments = ['logs/system.log']
    app = current_app._get_current_object()
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender='NoReply@lab.tools.com', recipients=[to])
    msg.body = 'The Devices were be power off on schedule, you can check the executing log in appendix.'
    for f in Attachments:
        with app.open_resource(f) as fp:
            msg.attach(filename=os.path.basename(f), data=fp.read(), content_type='application/octet-stream')
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

def send_pwd_email(to, subject, template, pc_id, to_username, **kwargs):
    app = current_app._get_current_object()
    # to = 'horace365@163.com'
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender='NoReply@lab.tools.com', recipients=[to])

    msg.html = render_template(template + '.html', pc_id=pc_id, sender_name=to_username, sender_mail=to, **kwargs )
    print('msg-----%s' % msg)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

def send_vlab_pwd_email(to, subject, template, user_info, to_username, **kwargs):
    app = current_app._get_current_object()
    # to = 'horace365@163.com'
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender='NoReply@lab.tools.com', recipients=[to])

    msg.html = render_template(template + '.html', user_info=user_info, sender_name=to_username, sender_mail=to, **kwargs)
    print('msg-----%s' % msg)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

def send_all_email(to, subject, template, user_id, to_username, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender='NoReply@lab.tools.com', recipients=[to])
    msg.html = render_template(template + '.html', user_id=user_id, sender_name=to_username, sender_mail=to, **kwargs )

    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

def dut_change_user_email(to, subject, template, product_info, sender, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender='NoReply@lab.tools.com', recipients=[to])
    msg.html = render_template(template + '.html', product_info=product_info, sender_name=sender, sender_mail=to, **kwargs )

    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

def ticket_email(to, subject, template, mailcontent, sender, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender='NoReply@lab.tools.com', recipients=[to])
    msg.html = render_template(template + '.html', mailcontent=mailcontent, sender_name=sender, sender_mail=to, **kwargs )

    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

def jira_issues_email(to, subject, template, mailcontent, touser, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender='NoReply@lab.tools.com', recipients=[to])
    msg.html = render_template(template + '.html', mailcontent=mailcontent, to_user=touser, sender_mail=to, **kwargs )

    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr


def send_crash_email(to, subject, template, dut_info, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender='NoReply@lab.tools.com', recipients=[to])

    msg.html = render_template(template + '.html', dut_info=dut_info, sender_mail=to, **kwargs)
    print('msg-----%s' % msg)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

def send_device_borrow_request_email(to, subject, template, device_info, requester_name, owner_name, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender='NoReply@lab.tools.com', recipients=[to])
    msg.html = render_template(template + '.html', device_info=device_info, requester_name=requester_name, owner_name=owner_name, sender_mail=to, **kwargs)
    print('msg-----%s' % msg)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr
