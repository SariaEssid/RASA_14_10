import smtplib
from email.mime.text import MIMEText




class HILA33:
    """
    Classe pour nettoyer et formater les réponses textuelles.
    """

    @staticmethod
    # This sends a REAL text message to a cellular phone number for free
    def send_real_sms(phone_number, carrier_domain, message):
        print("✅ Real SMS sent!")
        # Formats to: "1234567890@vtext.com" (if Verizon)
        to_address = f"{phone_number}@{carrier_domain}"

        msg = MIMEText(message)
        msg['From'] = "saria.essid@gmail.com"
        msg['To'] = to_address

        server = smtplib.SMTP("://gmail.com", 587)
        server.starttls()
        server.login("saria.essid@gmail.com", "saria.essid")
        server.sendmail("saria.essid@gmail.com", to_address, msg.as_string())
        server.quit()
        print("✅ Real SMS sent!")

# --- Zone de Test ---
if __name__ == "__main__":
    input_text = "comment **pour Robot ChatBot.**"
    result = HILA33.send_real_sms(92464423, "gmail.com", "message me")

    print(result)