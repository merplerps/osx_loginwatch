#!/usr/bin/python2.7

import os
import glob
import logging
from SystemConfiguration import SCDynamicStoreCopyConsoleUser
import sys
import subprocess

sys.path.append('/Library/Scripts/')

import reset_account_lock

# Define file paths and constants


log_location = '/var/log/LoginWatch.log'
user_path = '/var/db/dslocal/nodes/Default/users/*'
fail_temp_folder = '/var/tmp/'
changed_file = 'empty'
changed_user = 'empty'
fail_temp_file = fail_temp_folder + changed_user + '.log'
max_loggedout_fails = 7
max_loggedin_fails = 3
pause_time = 900
sleep_time = 1800
hibernate_time = 7200
wait_time = None


def get_logged_in_user():
    global username
    username = (SCDynamicStoreCopyConsoleUser(None, None, None) or [None])[0]
    username = [username, ""][username in [u"loginwindow", None, u""]]
    logging.debug('Logged in User: %s', username)


def get_failed_login_count():
    try:
        output = subprocess.check_output(['/usr/bin/dscl', '.', '-readpl', '/Users/' + changed_user,
                                          'accountPolicyData', 'failedLoginCount'])
        logging.debug('Failed Login Count Result: %s', str(output))
        global num_failures
        num_failures = output.split(':')[-1]
        num_failures = int(num_failures.strip())
    except ValueError:
        logging.error('Could not convert data to an integer.')
        logging.warn('No Failed logins found for %s', changed_user)
        raise SystemExit


def get_changed_file():
    global changed_file
    changed_path = max(glob.iglob(user_path), key=os.path.getctime)
    changed_file = os.path.basename(changed_path)
    logging.debug('Changed file is: %s', changed_file)


def get_changed_user():
    global changed_user
    changed_user = os.path.splitext(changed_file)[0]
    logging.debug('Username is %s', changed_user)


def set_failtempcounter():
    global fail_tempcounter
    global fail_temp_file
    fail_temp_file = fail_temp_folder + changed_user + '.log'
    logging.debug('Fail Temp File is %s', fail_temp_file)
    try:
        with open(fail_temp_file, 'r') as tempfile:
            fail_tempcounter = int(tempfile.read())
            logging.debug('Fail Temp Counter is now %s', fail_tempcounter)
    except IOError:
        with open(fail_temp_file, 'w') as tempfile:
            logging.debug('%s file not found', fail_temp_file)
            tempfile.write("0")
        with open(fail_temp_file, 'r') as tempfile:
            fail_tempcounter = int(tempfile.read())
        logging.info('Login Failures have not been reset.  Fail Counter is %s.', fail_tempcounter)


def reset_failtempcounter():
    global fail_temp_file
    global fail_tempcounter
    fail_temp_file = fail_temp_folder + changed_user + '.log'
    logging.debug('Fail Temp File is %s', fail_temp_file)
    try:
        with open(fail_temp_file, 'r+') as tempfile:
            for line in tempfile:
                if line.strip():
                    logging.debug ('Contents of FailTempCounter: %s', line)
                    fail_tempcounter = int(line)
                    break
            logging.debug('Fail Temp Counter before change is %s', fail_tempcounter)
            tempfile.seek(0)
            tempfile.truncate(0)
            tempfile.write(str("0"))
        with open(fail_temp_file, 'r') as tempfile:
            fail_tempcounter = int(tempfile.read())
            logging.debug('Fail Temp Counter after change is %s', fail_tempcounter)
    except IOError:
        with open(fail_temp_file, 'w') as tempfile:
            logging.debug('%s file not found', fail_temp_file)
            tempfile.write("0")
        with open(fail_temp_file, 'r') as tempfile:
            fail_tempcounter = int(tempfile.read())
            logging.info('Fail Temp Counter was reset.  Fail Counter is now %s.', fail_tempcounter)


def determine_wait_time():
    global wait_time
    global fail_tempcounter
    logging.debug('pause: %s, sleep: %s, hibernate: %s', pause_time, sleep_time, hibernate_time)
    logging.debug('Wait time at start is %s. Fail tempcounter is %s.',
                  wait_time, fail_tempcounter)
    if fail_tempcounter is 0:
        wait_time = pause_time
    elif fail_tempcounter is 1:
        wait_time = sleep_time
    elif fail_tempcounter > 1:
        wait_time = hibernate_time
    logging.debug('Wait time has been set to %s', wait_time)


def get_lockout_details():
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


def check_screensaver():
    global screensaver_status
    screensaver_status = None
    logging.debug('Checking for presence of screensaver.')
    try:
        process = subprocess.Popen('pgrep -q ScreenSaverEngine', shell=True, stderr=subprocess.STDOUT)
        my_pid, err = process.communicate()
        if not my_pid:
            logging.debug('Screensaver not found in pgrep')
            screensaver_status = False
            logging.info('Screensaver Running: %s', screensaver_status)
        else:
            logging.debug('Screensaver engine found: %s', output)
            screensaver_status = True
            logging.info('Screensaver Running: %s', screensaver_status)
    except:
        logging.debug('caught screensaver exception. Status %s', screensaver_status)

def main():
    logging.basicConfig(filename=log_location, format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    logger.info("***   Initializing Login Watch   ***")

    get_changed_file()
    get_changed_user()
    get_failed_login_count()
    get_logged_in_user()
    logger.info('Something changed in the watchpath.')
    logger.info('Modified user: %s Failed Login Count: %s', changed_user, num_failures)
    logger.info('Current logged in user is %s', username)

    if username is None or username is "":
        logging.debug('Logged in user is %s(none). Max Fails should be %s', username, max_loggedout_fails)
        if num_failures < max_loggedout_fails:
            logger.info('%s accountPolicyData has been modified.  Now failedLoginCount is %s', changed_user,
                        num_failures)
        else:
            set_failtempcounter()
            logging.info('Fail Temp Counter is: %s', fail_tempcounter)
            determine_wait_time()
            logging.info('Account locked for: %s. Failures: %s. Wait time has been set to: %s.',
                         changed_user, num_failures, wait_time)
            reset_account_lock.main()
    else:
        check_screensaver()
        if num_failures is 0 and screensaver_status is False:
            reset_failtempcounter()
            logging.debug('Logged in user is %s. Max Fails should be %s', username, max_loggedin_fails)
            logging.info('Fail Temp Counter has been reset.')
        elif num_failures < max_loggedin_fails:
            logger.info('%s accountPolicyData has been modified.  Now failedLoginCount is %s', changed_user,
                        num_failures)
        else:
            set_failtempcounter()
            logging.info('Fail Temp Counter is: %s', fail_tempcounter)
            determine_wait_time()
            logging.info('Account locked for: %s. Failures: %s. Wait time has been set to: %s.',
                         changed_user, num_failures, wait_time)
            reset_account_lock.main()

if __name__ == '__main__':
    main()