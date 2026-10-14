from twilio.rest import Client

# in this part you have to replace account_sid
# auth_token, twilio_number, recipient_number with your actual credential

account_sid = 'ACab48159ed5d6bebac4c2ced2ea112141'
auth_token = 'd253d5350f160a78844c78c73ba16851'
twilio_number = '+21692464423'
recipient_number = '+21694617435'

# Create Twilio client
client = Client(account_sid, auth_token)

# Send SMS
# in body part you have to write your message
message = client.messages.create(
    body='7asbi ALLAH wa ni3ma alwakil !',
    from_=twilio_number,
    to=recipient_number
)

print(f"Message sent with SID: {message.sid}")