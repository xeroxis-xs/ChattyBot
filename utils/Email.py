import os
import time
from dotenv import load_dotenv
from azure.communication.email import EmailClient

load_dotenv()

POLLER_WAIT_TIME = 10


class AzureEmailClient:
    def __init__(self):
        try:
            self.email_client = EmailClient.from_connection_string(os.environ["COMMUNICATION_SERVICES_CONNECTION_STRING"])
        except Exception as e:
            print("Error connecting to Azure Email Comms Service: " + str(e))

    def draft_email(self, subject, html_body, plain_text_body, to_email_add, to_email_name, from_email_add):
        if len(to_email_add) == 2:
            to = [
                {"address": to_email_add[0], "displayName": to_email_name[0]},
                {"address": to_email_add[1], "displayName": to_email_name[1]},
            ]
        else:
            to = [
                {"address": to_email_add[0], "displayName": to_email_name[0]}
            ]
        message = {
            "content": {
                "subject": subject,
                "plainText": plain_text_body,
                "html": html_body
            },
            "recipients": {
                "to": to
            },
            "senderAddress": from_email_add
        }
        return message

    def send_email(self, message):
        poller = self.email_client.begin_send(message)

    def send_email_timeout(self, message):
        try:
            poller = self.email_client.begin_send(message)
            time_elapsed = 0
            while not poller.done():
                print("Email send poller status: " + poller.status())
                poller.wait(POLLER_WAIT_TIME)
                time_elapsed += POLLER_WAIT_TIME

                if time_elapsed > 18 * POLLER_WAIT_TIME:
                    raise RuntimeError("Polling timed out.")

            if poller.result()["status"] == "Succeeded":
                print(f"Successfully sent the email (operation id: {poller.result()['id']})")
            else:
                raise RuntimeError(str(poller.result()["error"]))
        except Exception as e:
            print("Error sending email: " + str(e))

    def read_html_template(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            template = file.read()
        return template


if __name__ == '__main__':
    print("Starting Local Test...")
    email_client = AzureEmailClient()

    subject = "This is the subject"
    plain_text_body = "This is the plain text body"
    html_body = "<html><h1>This is the body</h1></html>"
    to_email = "C210101@e.ntu.edu.sg"
    to_name = "TEOH XI SHENG"
    from_email = "DoNotReply@140197c9-8f19-4c8a-9bb4-23adfc6600ef.azurecomm.net"

    message = email_client.draft_email(subject, html_body, plain_text_body, to_email, to_name, from_email)
    email_client.send_email(message)
