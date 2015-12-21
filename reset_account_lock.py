#!/usr/bin/python2.7

import os
import glob
import logging
from datetime import datetime
import subprocess
import time


# Define file paths and constants


log_location = '/var/log/LoginWatch.log'
fail_temp_folder = '/var/tmp/'
max_loggedout_fails = 7
failure_int = None

def get_failed_login_count():
    try:
        output = subprocess.check_output(['/usr/bin/dscl', '.', '-readpl', '/Users/' + locked_user,
                                          'accountPolicyData', 'failedLoginCount'])
        logging.debug('Result of Failed Logins check: %s', str(output))
        global num_failures
        num_failures = output.split(':')[-1]
        num_failures = int(num_failures.strip())
        logging.info('Failed logins for %s: %s', locked_user, num_failures)
    except ValueError:
        logging.error('Could not convert data to an integer.')
        logging.warn('No Failed logins found for %s', locked_user)
        raise SystemExit


def get_lockout_details():
    global locked_user
    global failure_count
    global lockout_time
    global lockout_duration
    lock_search_string = "Account locked for:"
    for line in reversed(open(log_location).readlines()):
        if lock_search_string in line:
            lockout_time = (line[0:22])
            list_of_words = line.split()
            locked_user = list_of_words[list_of_words.index('for:') + 1]
            locked_user = locked_user[:-1]
            lockout_duration = list_of_words[list_of_words.index('to:') + 1]
            lockout_duration = lockout_duration[:-1]
            failure_count = list_of_words[list_of_words.index('Failures:') + 1]
            failure_count = failure_count[:-1]
            logging.debug('Found Locked User: %s, Time: %s, Duration: %s, Failures: %s',
                          locked_user, lockout_time, lockout_duration, failure_count)
            break


def increment_fail_temp_counter():
    global fail_tempcounter
    fail_temp_file = fail_temp_folder + locked_user + '.log'
    logging.debug('Fail Temp File is %s', fail_temp_file)
    try:
        with open(fail_temp_file, 'r+') as tempfile:
            for line in tempfile:
                if line.strip():
                    logging.debug('Contents of FailTempCounter: %s', line)
                    fail_tempcounter = int(line)
                    break
            logging.debug('Fail Temp Counter before change is %s', fail_tempcounter)
            fail_tempcounter = (fail_tempcounter + 1)
            tempfile.seek(0)
            tempfile.truncate(0)
            tempfile.write(str(fail_tempcounter))
            logging.debug('Fail Temp Counter after change is %s', fail_tempcounter)
    except IOError:
        with open(fail_temp_file, 'w') as tempfile:
            logging.debug('%s file not found', fail_temp_file)
            tempfile.write("0")
        with open(fail_temp_file, 'r') as tempfile:
            fail_tempcounter = int(tempfile.read())
            logging.info('Login Failures have not been reset.  Fail Counter is %s.', fail_tempcounter)


def unlock_account():
    logging.debug('Attempting to unlock account.')
    subprocess.call(['/usr/bin/dscl', '.', '-deletepl', '/Users/' + locked_user,
                     'accountPolicyData', 'failedLoginCount'])
    subprocess.call(['/usr/bin/dscl', '.', '-createpl', '/Users/' + locked_user,
                     'accountPolicyData', 'failedLoginCount', '0'])


def main():
    logging.basicConfig(filename=log_location, format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logging.info('***   Initializing Account Lock Reset   ***')

    get_lockout_details()
    get_failed_login_count()

    current_time = datetime.now()
    lockout_date_object = datetime.strptime(lockout_time, '%m/%d/%Y %I:%M:%S%f %p')
    logging.debug('Lockout Time: %s', lockout_date_object)
    logging.debug('Current Time: %s', current_time)
    logging.debug('Lockout Duration: %s', lockout_duration)
    logging.debug('Locked Users: %s', locked_user)
    logging.debug('Failed Logins %s', int(num_failures))
    logging.debug('Failure Count from Log %s', int(failure_count))

    global failure_int
    failure_int = int(failure_count)

    logging.debug('TYPE: Failed Logins %s', type(num_failures))
    logging.debug('TYPE: Failure Count from Log %s', type(failure_int))

    if num_failures >= failure_int:

        time_diff = (current_time - lockout_date_object).total_seconds()
        logging.debug('Time diff: %s', time_diff)

        loopwait = (int(lockout_duration) - int(time_diff) + 1)
        starttime = time.time()
        while True:
            time_diff = (datetime.now() - lockout_date_object).total_seconds()
            logging.debug('Time diff: %s', time_diff)

            if int(time_diff) > int(lockout_duration):
                logging.debug('Time since lockout: %s is greater than wait time %s', int(time_diff),
                              int(lockout_duration))
                unlock_account()
                get_failed_login_count()
                increment_fail_temp_counter()
                break
            else:
                logging.info('Not time to unlock yet. Time since lockout: %s is less than wait time: %s',
                             int(time_diff), int(lockout_duration))
            time.sleep(loopwait - ((time.time() - starttime) % loopwait))
    else:
        logging.info("Last locked account has already been reset.")


if __name__ == '__main__':
    main()
