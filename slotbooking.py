import copy
import time
from types import SimpleNamespace
import requests, datetime
from utils import check_and_book, BENEFICIARIES_URL, collect_user_details, get_dose_num, get_logger

logger = get_logger()

def book_slot(mobile, token, state_name, district_name):
    base_request_header = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36',
        }

    request_header = copy.deepcopy(base_request_header)
    request_header["Authorization"] = f"Bearer {token}"

    collected_details, error = collect_user_details(request_header, state_name, district_name)
    if error:
        return False, error
    info = SimpleNamespace(**collected_details)

    retry_count = 1
    while retry_count < 5:
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
                return True, "Slot has been booked. You will get notification on your registered mobile number."
            else:
                # if token invalid, retry 5 times
                logger.info('Token is INVALID.')
                retry_count = retry_count + 1

                logger.info('Retryin in 5 seconds')
                time.sleep(5)    
        except Exception as e:
            logger.error(e)
            logger.info('Retryin in 5 seconds')
            retry_count = retry_count + 1
            time.sleep(5)
    return False, "Slot Booking Failed. Please Try again in Sometime."