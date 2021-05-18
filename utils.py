import time
import re
import json
import uuid
import logging
from hashlib import sha256
import copy, time, requests, random, os
from collections import Counter
from datetime import datetime, timedelta

from captcha import captcha_builder, captcha_builder_auto
from dblayer import get_otp_txnid

BOOKING_URL = "https://cdn-api.co-vin.in/api/v2/appointment/schedule"
BENEFICIARIES_URL = "https://cdn-api.co-vin.in/api/v2/appointment/beneficiaries"
CALENDAR_URL_DISTRICT = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/calendarByDistrict?district_id={0}&date={1}"
CALENDAR_URL_PINCODE = "https://cdn-api.co-vin.in/api/v2/appointment/sessions/calendarByPin?pincode={0}&date={1}"
CAPTCHA_URL = "https://cdn-api.co-vin.in/api/v2/auth/getRecaptcha"
OTP_PUBLIC_URL = "https://cdn-api.co-vin.in/api/v2/auth/public/generateOTP"
OTP_PRO_URL = "https://cdn-api.co-vin.in/api/v2/auth/generateMobileOTP"
VALIDATE_MOBILE_OTP_URL = "https://cdn-api.co-vin.in/api/v2/auth/validateMobileOtp"
STATES_URL = "https://cdn-api.co-vin.in/api/v2/admin/location/states"
DISTRICTS_URL = "https://cdn-api.co-vin.in/api/v2/admin/location/districts/"
CERTIFICATE_URL = "https://cdn-api.co-vin.in/api/v2/registration/certificate/public/download"

def get_logger():
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG)
    return logging.getLogger()

logger = get_logger()

def get_help_text(is_telegram=False):
    if is_telegram:
        help_text = "Type /query <query> for example: /query hospital in kanpur to get relavant results.\n\nType /feed <query> to feed data. eg; /feed 10 oxygen bed provided by smart care hospital available at swaroop nagar kanpur contact at <provider-contact-number> verified by <verifier-contact-number>.\n\nType /add <message> to add city or entity eg; /add city kanpur\n\n\nDeveloped by : Raman Pandey"
    else:
        help_text = "Type <query> for example: hospital in kanpur to get relavant results.\n\nType <query> to feed data. just put feed before your query. eg; feed 10 oxygen bed provided by smart care hospital available at swaroop nagar kanpur contact at <provider-contact-number> verified by <verifier-contact-number>.\n\nType add <message> to add city or entity eg; add city kanpur\n\n\nDeveloped by : Raman Pandey"
    return help_text

def current_milli_time():
    return round(time.time() * 1000)

def get_verified_at(filed_at):
    try:
        verifieddt = datetime.strptime(filed_at, '%Y-%m-%dT%H:%M:%S.%f%z')
    except Exception as e:
        logger.error(e)
        verifieddt = datetime.strptime(filed_at, '%Y-%m-%dT%H:%M:%S.%f')
    verified_at = f'{verifieddt:%d/%m/%Y %H:%M:%S}'
    return verified_at

def get_data_from_field(query_fields, field):
    entity = query_fields[field].string_value
    if not entity:
        entity = query_fields[field].list_value.values[0].string_value
    return entity
     
def get_numbers_str(mixed_str):
    temp = re.findall(r'\d+', mixed_str)
    return ",".join(temp)

def viable_options(resp, minimum_slots, min_age_booking, fee_type, dose_num):
    options = []
    if len(resp["centers"]) >= 0:
        for center in resp["centers"]:
            for session in center["sessions"]:
                # Cowin uses slot number for display post login, but checks available_capacity before booking appointment is allowed
                available_capacity = min(session[f'available_capacity_dose{dose_num}'], session['available_capacity'])
                if ((available_capacity >= minimum_slots) and (session["min_age_limit"] <= min_age_booking)):
                    out = {
                        "name": center["name"],
                        "district": center["district_name"],
                        "pincode": center["pincode"],
                        "center_id": center["center_id"],
                        "available": available_capacity,
                        "date": session["date"],
                        "slots": session["slots"],
                        "session_id": session["session_id"],
                    }
                    options.append(out)

                else:
                    pass
    else:
        pass

    return options

def get_dose_num(beneficiary_vaccine_status):
    dose_num = 1
    if beneficiary_vaccine_status == "Partially Vaccinated":
        dose_num = 2
    return dose_num

def collect_user_details(request_header, state_name, district_name):
    # Get Beneficiaries
    logger.debug("Fetching registered beneficiaries.. ")
    beneficiary_dtls = get_beneficiaries(request_header)

    if not beneficiary_dtls:
        return None, "There should be at least one beneficiary."

    # Make sure all beneficiaries have the same type of vaccine
    vaccine_types = [beneficiary["vaccine"] for beneficiary in beneficiary_dtls]
    # vaccines = Counter(vaccine_types)

    # if len(vaccines.keys()) != 1:
    #     return None, f"All beneficiaries in one attempt should have the same vaccine type. Found {len(vaccines.keys())}"

    vaccine_type = vaccine_types[0]  
    # if all([beneficiary['status'] == 'Partially Vaccinated' for beneficiary in beneficiary_dtls]) else None
    if not vaccine_type:
        vaccine_type = get_vaccine_preference(0)

    # Collect vaccination center preferance
    location_dtls, error = get_districts(request_header, state_name, district_name)
    if error:
        return None, error

    minimum_slots = len(beneficiary_dtls)

    refresh_freq = 15

    # Get search start date
    start_date = 2

    # Get preference of Free/Paid option
    fee_type = get_fee_type_preference(0)

    auto_book = "yes-please"
    captcha_automation = "y"
    captcha_automation_api_key = os.getenv("ANTICAPTCHAKEY")

    search_option = 2

    # captcha_automation = input("Do you want to automate captcha autofill? (y/n) Default n: ")
    # captcha_automation = "n" if not captcha_automation else captcha_automation
    # if captcha_automation=="y":
    #     captcha_automation_api_key = input("Enter your Anti-Captcha API key: ")
    # else:
    #     captcha_automation_api_key = None

    collected_details = {
        "beneficiary_dtls": beneficiary_dtls,
        "location_dtls": location_dtls,
        "search_option": search_option,
        "minimum_slots": minimum_slots,
        "refresh_freq": refresh_freq,
        "auto_book": auto_book,
        "start_date": start_date,
        "vaccine_type": vaccine_type,
        "fee_type": fee_type,
        'captcha_automation': captcha_automation,
        'captcha_automation_api_key': captcha_automation_api_key
    }

    return collected_details, None


def filter_centers_by_age(resp, min_age_booking):

    if min_age_booking >= 45:
        center_age_filter = 45
    else:
        center_age_filter = 18

    if "centers" in resp:
        for center in list(resp["centers"]):
            for session in list(center["sessions"]):
                if session['min_age_limit'] != center_age_filter:
                    center["sessions"].remove(session)
                    if(len(center["sessions"]) == 0):
                        resp["centers"].remove(center)

    return resp    


def check_calendar_by_district(
    request_header,
    vaccine_type,
    location_dtls,
    start_date,
    minimum_slots,
    min_age_booking,
    fee_type,
    dose_num
):
    """
    This function
        1. Takes details required to check vaccination calendar
        2. Filters result by minimum number of slots available
        3. Returns False if token is invalid
        4. Returns list of vaccination centers & slots if available
    """
    try:
        today = datetime.today()
        base_url = CALENDAR_URL_DISTRICT

        if vaccine_type:
            base_url += f"&vaccine={vaccine_type}"

        options = []
        for location in location_dtls:
            resp = requests.get(base_url.format(location["district_id"], start_date), headers=request_header)

            if resp.status_code == 401:
                logger.debug("TOKEN INVALID")
                return False

            elif resp.status_code == 200:
                resp = resp.json()

                resp = filter_centers_by_age(resp, min_age_booking)

                if "centers" in resp:
                    logger.debug(
                        f"Centers available in {location['district_name']} from {start_date} as of {today.strftime('%Y-%m-%d %H:%M:%S')}: {len(resp['centers'])}"
                    )
                    options += viable_options(resp, minimum_slots, min_age_booking, fee_type, dose_num)

        return options
    except Exception as e:
        logger.error(e)

def generate_captcha(request_header, captcha_automation, api_key):
    logger.debug(
        "================================= GETTING CAPTCHA =================================================="
    )
    resp = requests.post(CAPTCHA_URL, headers=request_header)
    logger.debug(f'Captcha Response Code: {resp.status_code}')

    if resp.status_code == 200 and captcha_automation=="n":
        return captcha_builder(resp.json())
    elif resp.status_code == 200 and captcha_automation=="y":
        return captcha_builder_auto(resp.json(), api_key)


def book_appointment(request_header, details, mobile, generate_captcha_pref, api_key=None):
    """
    This function
        1. Takes details in json format
        2. Attempts to book an appointment using the details
        3. Returns True or False depending on Token Validity
    """
    try:
        valid_captcha = True
        while valid_captcha:
            captcha = generate_captcha(request_header, generate_captcha_pref, api_key)
            details["captcha"] = captcha

            resp = requests.post(BOOKING_URL, headers=request_header, json=details)
            logger.debug(f"Booking Response Code: {resp.status_code}")
            logger.debug(f"Booking Response : {resp.text}")

            if resp.status_code == 401:
                return False, "TOKEN INVALID"

            elif resp.status_code == 200:
                return True, "Appointment Booked"

            elif resp.status_code == 400:
                return False, f"Response: {resp.status_code} : {resp.text}"
            else:
                return True, f"Response: {resp.status_code} : {resp.text}"

    except Exception as e:
        logger.error(e)


def check_and_book(request_header, beneficiary_dtls, location_dtls, search_option, **kwargs):
    """
    This function
        1. Checks the vaccination calendar for available slots,
        2. Lists all viable options,
        3. Takes user's choice of vaccination center and slot,
        4. Calls function to book appointment, and
        5. Returns True or False depending on Token Validity
    """
    try:
        min_age_booking = get_min_age(beneficiary_dtls)

        minimum_slots = kwargs["min_slots"]
        refresh_freq = kwargs["ref_freq"]
        auto_book = kwargs["auto_book"]
        start_date = kwargs["start_date"]
        vaccine_type = kwargs["vaccine_type"]
        fee_type = kwargs["fee_type"]
        mobile = kwargs["mobile"]
        captcha_automation = kwargs['captcha_automation']
        captcha_automation_api_key = kwargs['captcha_automation_api_key']

        beneficiary_options = []
        for beneficiary in beneficiary_dtls:
            dose_num = get_dose_num(beneficiary['status'])

            if isinstance(start_date, int) and start_date == 2:
                start_date = (datetime.today() + timedelta(days=1)).strftime("%d-%m-%Y")
            elif isinstance(start_date, int) and start_date == 1:
                start_date = datetime.today().strftime("%d-%m-%Y")

            options = check_calendar_by_district(request_header, vaccine_type, location_dtls, start_date, minimum_slots, min_age_booking, fee_type, dose_num)
            if isinstance(options, bool):
                return False, "Sorry, no viable options found for slot booking"

            if options:
                options = sorted(
                    options,
                    key=lambda k: (
                        k["district"].lower(),
                        k["pincode"],
                        k["name"].lower(),
                        datetime.strptime(k["date"], "%d-%m-%Y"),
                    ),
                )
                beneficiary_options_dict = {'beneficiary': beneficiary, 'options': options }
                beneficiary_options.append(beneficiary_options_dict)
        if beneficiary_options:
            appointment_status = book_appointment(request_header, beneficiary_options, mobile, captcha_automation, captcha_automation_api_key)
            return True, "Congrats, Your slot has been booked."
        else:
            return False, "Sorry no slot has been found. Please Try again later."
            
                # new_req = {
                #     "beneficiaries": [
                #         beneficiary["bref_id"] for beneficiary in beneficiary_dtls
                #     ],
                #     "dose": 2
                #     if [beneficiary["status"] for beneficiary in beneficiary_dtls][0]
                #     == "Partially Vaccinated"
                #     else 1,
                #     "center_id": options[choice[0] - 1]["center_id"],
                #     "session_id": options[choice[0] - 1]["session_id"],
                #     "slot": options[choice[0] - 1]["slots"][choice[1] - 1],
                # }

                # logger.debug(f"Booking with info: {new_req}")
                # book_appointment(request_header, new_req, mobile, captcha_automation, captcha_automation_api_key)

    except TimeoutOccurred:
        time.sleep(1)
        return False, "Timeout happened"


def get_vaccine_preference(vaccine_preference):
    preference = int(vaccine_preference) if vaccine_preference and int(vaccine_preference) in [0, 1, 2, 3] else 0

    if preference == 1:
        return "COVISHIELD"
    elif preference == 2:
        return "COVAXIN"
    elif preference == 3:
        return "SPUTNIK V"
    else:
        return None


def get_fee_type_preference(fee_preference):
    preference = int(fee_preference) if fee_preference and int(fee_preference) in [0, 1, 2] else 0

    if preference == 1:
        return ["Free"]
    elif preference == 2:
        return ["Paid"]
    else:
        return ["Free", "Paid"]


def get_districts(request_header, state_name, district_name):
    """
    This function
        1. Lists all states, prompts to select one,
        2. Lists all districts in that state, prompts to select required ones, and
        3. Returns the list of districts as list(dict)
    """
    states = requests.get(STATES_URL, headers=request_header)

    if states.status_code == 200:
        states = states.json()["states"]
        state_id = None
        for state in states:
            if state_name == state["state_name"].lower():
                state_id = state["state_id"]
                break

        if not state_id:
            return [], "State is not found with Name {}".format(state_name)

        districts = requests.get(DISTRICTS_URL + str(state_id), headers=request_header)

        if districts.status_code == 200:
            districts = districts.json()["districts"]

            refined_districts = []
            for district in districts:
                if district_name == district["district_name"].lower():
                    district_info = {
                        "district_id": district["district_id"],
                        "district_name": district["district_name"]
                    }
                    refined_districts.append(district_info)

            return refined_districts, None

        else:
            return [], "Unable to fetch districts"

    else:
        return [], "Unable to fetch states"


def get_beneficiaries(request_header):
    """
    This function
        1. Fetches all beneficiaries registered under the mobile number,
        2. Prompts user to select the applicable beneficiaries, and
        3. Returns the list of beneficiaries as list(dict)
    """
    beneficiaries = requests.get(BENEFICIARIES_URL, headers=request_header)

    if beneficiaries.status_code == 200:
        beneficiaries = beneficiaries.json()["beneficiaries"]

        refined_beneficiaries = []
        for beneficiary in beneficiaries:
            beneficiary["age"] = datetime.today().year - int(beneficiary["birth_year"])

            tmp = {
                "bref_id": beneficiary["beneficiary_reference_id"],
                "name": beneficiary["name"],
                "vaccine": beneficiary["vaccine"],
                "age": beneficiary["age"],
                "status": beneficiary["vaccination_status"],
            }
            refined_beneficiaries.append(tmp)

        reqd_beneficiaries = 10
        beneficiary_idx = [int(idx) - 1 for idx in range(reqd_beneficiaries)]
        reqd_beneficiaries = [
            {
                "bref_id": item["beneficiary_reference_id"],
                "name": item["name"],
                "vaccine": item["vaccine"],
                "age": item["age"],
                "status": item["vaccination_status"],
            }
            for idx, item in enumerate(beneficiaries)
            if idx in beneficiary_idx
        ]
        return reqd_beneficiaries

def get_min_age(beneficiary_dtls):
    """
    This function returns a min age argument, based on age of all beneficiaries
    :param beneficiary_dtls:
    :return: min_age:int
    """
    age_list = [item["age"] for item in beneficiary_dtls]
    min_age = min(age_list)
    return min_age

def sendCowinOTP(mobile):
    data = {"mobile": mobile, "secret": os.getenv("COWINOTPSECRET")}
    request_header = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    txnResp = requests.post(url=OTP_PRO_URL, json=data, headers=request_header)

    if txnResp.status_code == 200:
        logger.debug(f"Successfully requested OTP for mobile number {mobile} at {datetime.today()}..")
        txnId = txnResp.json()['txnId']
        return txnId

def validateCowinOTP(coll, mobile, otp):
    otpTxnId = get_otp_txnid(coll, mobile)
    request_header = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}
    try:
        data = {"otp": sha256(str(otp).encode('utf-8')).hexdigest(), "txnId": otpTxnId}
        logger.debug(f"Validating OTP..")

        token = requests.post(url=VALIDATE_MOBILE_OTP_URL, json=data, headers=request_header)
        if token.status_code == 200:
            token = token.json()['token']
            logger.debug(f'Token Generated: {token}')
            return token, None
        else:
            return None, "Token not generated for given OTP and Mobile Number"
    except Exception as e:
        logger.error(e)
        return None, str(e)