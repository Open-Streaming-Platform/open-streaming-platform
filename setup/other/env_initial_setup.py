#! /usr/bin/env python
import os
import sys
import time
import requests

wait_time = 30
url = "http://localhost"
initial_endpoint = "/settings/initialSetup"


def wait_for_ready(timeout=30):
    timeout_time = time.time() + timeout
    while True:
        try:
            r = requests.get(url)
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            continue
        if r.ok:
            return True
        if timeout_time <= time.time():
            return False
        time.sleep(1)

def to_bool(value):
    try:
        ret_value = int(value)
    except ValueError:
        ret_value = 0

if __name__ == '__main__':
    username = os.environ.get("OSP_ADMIN_USER")
    email = os.environ.get("OSP_ADMIN_EMAIL")
    password = os.environ.get("OSP_ADMIN_PASSWORD")
    if username and password and email:
        data = {"username": username,
                "password1": password,
                "password2": password,
                "email": email}
        try:
            data["serverName"] = os.environ["OSP_SERVER_NAME"]
            data["siteProtocol"] = os.environ.get("OSP_SERVER_PROTOCOL", "http")
            data["serverAddress"] = os.environ["OSP_SERVER_ADDRESS"]
            data["smtpSendAs"] = os.environ.get("OSP_SMTP_SEND_AS", "")
            data["smtpAddress"] = os.environ["OSP_SMTP_SERVER"]
            data["smtpPort"] = os.environ.get("OSP_SMTP_PORT", 25)
            data["smtpUser"] = os.environ.get("OSP_SMTP_USER", "")
            data["smtpPassword"] = os.environ.get("OSP_SMTP_PASSWORD", "")
            data["smtpTLS"] = os.environ.get("OSP_SMTP_TLS")
            data["smtpSSL"] = os.environ.get("OSP_SMTP_SSL")
            data["recordSelect"] = os.environ.get("OSP_ALLOW_RECORDING")
            data["uploadSelect"] = os.environ.get("OSP_ALLOW_UPLOAD")
            data["adaptiveStreaming"] = os.environ.get("OSP_ADAPTIVE_STREAMING")
            data["allowComments"] = os.environ.get("OSP_ALLOW_COMMENT")
            data["showEmptyTables"] = os.environ.get("OSP_DISPLAY_EMPTY")
        except KeyError as e:
            print("""Environment provisioning:
                  When OSP_ADMIN_USER, OSP_ADMIN_EMAIL and OSP_ADMIN_PASSWORD are set I'm expecting at least the following other variables to be also set:
                  OSP_SERVER_NAME
                  OSP_SERVER_PROTOCOL
                  OSP_SERVER_ADDRESS
                  OSP_SMTP_SERVER
                  """)
            sys.exit(1)
        if wait_for_ready(wait_time):
            r = requests.post(
                url=f"{url}{initial_endpoint}",
                data=data
            )
            if r.ok:
                print("Environment provisioning: Provisioning OK!")
            else:
                print(f"Environment provisioning: Prov failed! Make sure all environment variables are provided: {r.status_code} - {r.text}")
                sys.exit(3)
        else:
            print(f"Environment provisioning: Unable to perform provisioning via environment - http server not up in {wait_time} seconds")
            sys.exit(2)
    else:
        print("Environment provisioning: vars not set, not doing anything")