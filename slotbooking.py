import copy
import time
from types import SimpleNamespace
import requests, datetime
from utils import generate_token_OTP_manual, check_and_book, BENEFICIARIES_URL, collect_user_details, get_dose_num, get_logger

logger = get_logger()

def book_slot(mobile, otp, state_name, district_name):
    base_request_header = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
        }
    token, error = generate_token_OTP_manual(mobile, otp, base_request_header)
    if error:
        return error

    request_header = copy.deepcopy(base_request_header)
    request_header["Authorization"] = f"Bearer {token}"

    collected_details = collect_user_details(request_header, state_name, district_name)
    info = SimpleNamespace(**collected_details)

    token_valid = True
    while token_valid:
        request_header = copy.deepcopy(base_request_header)
        request_header["Authorization"] = f"Bearer {token}"

        # call function to check and book slots
        try:
            token_valid = check_and_book(request_header, info.beneficiary_dtls, info.location_dtls, info.search_option,
                                            min_slots=info.minimum_slots,
                                            ref_freq=info.refresh_freq,
                                            auto_book=info.auto_book,
                                            start_date=info.start_date,
                                            vaccine_type=info.vaccine_type,
                                            fee_type=info.fee_type,
                                            mobile=mobile,
                                            captcha_automation=info.captcha_automation,
                                            captcha_automation_api_key=info.captcha_automation_api_key,
                                            dose_num=get_dose_num(collected_details))

            # check if token is still valid
            beneficiaries_list = requests.get(BENEFICIARIES_URL, headers=request_header)
            if beneficiaries_list.status_code == 200:
                token_valid = True

            else:
                # if token invalid, regenerate OTP and new token
                # beep(WARNING_BEEP_DURATION[0], WARNING_BEEP_DURATION[1])
                logger.info('Token is INVALID.')
                token_valid = False
                token = None

                while token is None:
                    token = generate_token_OTP_manual(mobile, base_request_header)
                token_valid = True
        except Exception as e:
            logger.error(e)
            logger.info('Retryin in 5 seconds')
            time.sleep(5)