import smtplib
import os

EMAIL_ACCOUNT = os.getenv("EMAIL_ACCOUNT")
EMAIL_PASS = os.getenv("EMAIL_PASS")
SENDER = os.getenv("SENDER")
RECEIVER = os.getenv("RECEIVER")

def algo_notify(body):
    mail = smtplib.SMTP('smtp.gmail.com',587)
    mail.ehlo()
    mail.starttls()
    mail.login(EMAIL_ACCOUNT,EMAIL_PASS)

    
    subject = "Algo notification"
    content = body
    content  = f'Suject: {subject}\n\n{body}'
    print('sending mail...')
    mail.sendmail(EMAIL_ACCOUNT, RECEIVER, content)
    mail.close()