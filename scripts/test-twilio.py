from twilio.rest import Client

account_sid = "ACb8490dcdfffc9d2a1ba861fd6a894969"
auth_token = "4e452023c8a12fc5003ecc0f59fe73a3"
client = Client(account_sid, auth_token)

call = client.calls.create(
    to="+375293662296",
    from_="+19289687676",
    twiml="<Response><Say language='ru-RU'>Тест</Say></Response>"
)

print(call.sid)
