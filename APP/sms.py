import os
import urllib.request
import urllib.parse
import json

# Load configurations
FAST2SMS_API_KEY = os.getenv("FAST2SMS_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")

def send_sms_otp(mobile_number: str, otp_code: str) -> bool:
    """
    Sends the OTP code to the user's mobile number.
    Tries Fast2SMS first if FAST2SMS_API_KEY is configured,
    then tries Twilio if Twilio details are present.
    """
    # 1. FAST2SMS integration (Indian SMS Gateway)
    if FAST2SMS_API_KEY:
        try:
            import urllib.error
            # Use GET request for simpler and more robust url-query parameters
            query_params = urllib.parse.urlencode({
                "authorization": FAST2SMS_API_KEY,
                "route": "q",
                "message": f"Your MITS Chatbot verification code is: {otp_code}",
                "numbers": mobile_number
            })
            url = f"https://www.fast2sms.com/dev/bulkV2?{query_params}"
            
            req = urllib.request.Request(url)
            req.add_header("Authorization", FAST2SMS_API_KEY)
            
            with urllib.request.urlopen(req, timeout=5) as response:
                res_data = json.loads(response.read().decode())
                if res_data.get("return") is True:
                    print(f"[SMS SERVICE] Real SMS OTP sent successfully via Fast2SMS to {mobile_number}")
                    return True
                else:
                    print(f"[SMS ERROR] Fast2SMS returned error: {res_data}")
        except urllib.error.HTTPError as he:
            error_body = he.read().decode()
            print(f"[SMS ERROR] Fast2SMS returned HTTP {he.code}: {error_body}")
        except Exception as e:
            print(f"[SMS ERROR] Failed to send via Fast2SMS: {e}")

    # 2. TWILIO integration
    elif TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER:
        try:
            import base64
            # Twilio requires basic auth headers
            auth_str = f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}"
            auth_b64 = base64.b64encode(auth_str.encode()).decode()
            
            url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
            headers = {
                "Authorization": f"Basic {auth_b64}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Ensure number is in E.164 format (+91 for India if not specified)
            formatted_number = mobile_number.strip()
            if not formatted_number.startswith("+"):
                formatted_number = f"+91{formatted_number}"
                
            data = urllib.parse.urlencode({
                "From": TWILIO_FROM_NUMBER,
                "To": formatted_number,
                "Body": f"Your MITS Student Assistant verification code is: {otp_code}. Expirable in 5 mins."
            }).encode("utf-8")
            
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as response:
                print(f"[SMS SERVICE] Real SMS OTP sent successfully via Twilio to {formatted_number}")
                return True
        except Exception as e:
            print(f"[SMS ERROR] Failed to send via Twilio: {e}")

    # Fallback/Help message
    print(f"\n==========================================")
    print(f"[SMS CONFIG INFO] To send real SMS messages to {mobile_number}:")
    print(f"Option A: Add FAST2SMS_API_KEY to your .env file")
    print(f"Option B: Add TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_FROM_NUMBER to your .env file")
    print(f"==========================================\n")
    return False
