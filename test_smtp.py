"""Test SMTP Connection"""
import smtplib

print('Testing SMTP connection...')
print('Server: smtp.gmail.com:587')
print('Email: emaxis.newsletter@gmail.com')

try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    print('Connection: OK')
    
    try:
        # Test with the password from .env
        server.login('emaxis.newsletter@gmail.com', '$MC@2110')
        print('Login: OK')
        server.quit()
        print('SUCCESS: SMTP authentication works!')
    except smtplib.SMTPAuthenticationError as e:
        print(f'Login FAILED: {e}')
        print('')
        print('The Gmail App Password is incorrect or expired.')
        print('Get a new one from: https://myaccount.google.com/apppasswords')
except Exception as e:
    print(f'Connection FAILED: {e}')
