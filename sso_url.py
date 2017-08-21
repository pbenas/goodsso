#!/usr/bin/env python

# Created by GoodData Corporation
# Requirements:
# - python2.7 OR python2.6 with argparse package
# - (optional) gnupg package

from urllib import quote
from time import time
import getpass

HELP_MESSAGE = """
Testing testing, do you read me? This script is to test SSO functionality
a little bit easier. Remember, you still need to import our testing public key
to your keystore.

If you are unable to use keystore for some reason, you need to encrypt file
on your own. Usually something like:
echo "{\"email\": \"$LOGIN\",\"validity\": $((`date +%s` + 24*60*60))}" \
> json.txt
gpg --armor -u $KEY_OWNER --output signed.txt --sign json.txt
gpg --armor --output enc.txt --encrypt --recipient security@gooddata.com \
signed.txt

Examples:
# you need gnupg package
./sso_url.py --server-url "qa.gooddata.com" --customer-user \
"qa+sso@gooddata.com" --login "user@gooddata.com"
# you need to see your result now!
./sso_url.py --server-url "qa.gooddata.com" --customer-user \
"qa+sso@gooddata.com" --login "user@gooddata.com" --open-browser
# you don't need gnupg
./sso_url.py --server-url "qa.gooddata.com" --encrypted-file /tmp/enc.txt
"""


def parse_arguments():
    """
    Parse arguments.
    """
    import argparse
    from argparse import RawDescriptionHelpFormatter

    parser = argparse.ArgumentParser(
        description=HELP_MESSAGE,
        formatter_class=RawDescriptionHelpFormatter)

    parser.add_argument(
        '--target-url',
        dest='target_url',
        action='store',
        help=('target dashboard url, default is FoodMartDemo dashboard '
              '/dashboard.html#project=/gdc/projects/CustomerAnalytics'
              '&dashboard=/gdc/md/CustomerAnalytics/obj/923'),
        default=('/dashboard.html#project=/gdc/projects/CustomerAnalytics'
                 '&dashboard=/gdc/md/CustomerAnalytics/obj/923'))

    parser.add_argument(
        '--destination-server',
        dest='destination',
        action='store',
        default='https://sso-r73-test-devel.getgooddata.com/',
        help=('destination server, https://secure.gooddata.com/ for our '
              'production cluster. Default is testing single node instnace: '
              'https://sso-r73-test-devel.getgooddata.com/'))

    parser.add_argument(
        '--server-url',
        dest='server_url',
        action='store',
        help=('this is your domain you have registered as SSO domain, '
              'something like http://ourdomain.com'),
        required=True)

    parser.add_argument(
        '--encrypted-file',
        dest='encrypted_file',
        action='store',
        help=('name of your encrypted file. You must provide either '
              '--encrypted-file or --gooddata AND --customer. This option '
              'has higher priority.'))

    parser.add_argument(
        '--gnupg-home',
        dest='gnupg_home',
        action='store',
        default=None,
        help=('GNU PG home, default is what gnupg package can find '
              'on your system.'))

    parser.add_argument(
        '--customer-resource',
        dest='customer_resource',
        action='store',
        default='gdc/account/customerlogin',
        help=('if you really need to change it for some reason, default value '
              'is "gdc/account/customerlogin".'))

    parser.add_argument(
        '--open-browser',
        dest='open_browser',
        action='store_true',
        help='cosmetic thing, tries to open your browser.')

    parser.add_argument(
        '--customer-user',
        dest='customer_user',
        action='store',
        help=("customer's user (e-mail) associated with his private key. You "
              "need gnupg package if you want to provide this option!"))

    parser.add_argument(
        '--login',
        dest='login',
        action='store',
        help=('login of your (or given by us for testing purpose) user on our '
              'platform. You need gnupg package if you want to provide '
              'this option!'))

    parser.add_argument(
        '--gooddata-user',
        dest='gooddata_user',
        action='store',
        default="ops@gooddata.com",
        help=('e-mail associated with testing public gooddata key, default is '
              'testing public key owner ops@gooddata.com'))

    parser.add_argument(
        '--validity',
        dest='validity',
        action='store',
        default=(
            time() + 24 * 60 * 60),
        type=int,
        help='validity of generated url, default is 24 hours.')

    parser.add_argument('--dont-print', dest='dont_print', action='store_true',
                        help='don\'t print pretty long url.')

    arguments = parser.parse_args()

    return arguments


def generate_url(destination_url, customer_resource,
                 server_url, target_url, security_token):
    """
    Generate url.
    """
    return '%s%s?sessionId=%s&serverURL=%s&targetURL=%s' % (
        destination_url, customer_resource, quote(security_token),
        quote(server_url), quote(target_url))


def get_security_token_from_file(filename):
    """
    Get security token from given file.
    """
    file = open(filename)
    token = file.read()
    file.close()
    return token


def create_security_token(
        gnupg_home, login, gooddata_user, customer_user, validity):
    """
    Create token, you need gnugp module.
    """
    # import locally to avoid potential missing package error
    import gnupg
    gpg = gnupg.GPG(gnupghome=gnupg_home)
    # json to be encryted
    # json to be encryted
    json = '{"email": "%s","validity": %i}' % (login, validity)
    # message, keyid
    result = gpg.sign(json, keyid=customer_user, clearsign=False)
    signed = result.data

    error = result.stderr
    # NEED_PASSPHRASE? ok, try again with passphrase request
    if error.find("NEED_PASSPHRASE") != -1:
        passphrase = getpass.getpass("Passphrase: ")
        result = gpg.sign(
            json,
            keyid=customer_user,
            clearsign=False,
            passphrase=passphrase)
        # remove passphrase as soon as possible
        passphrase = None
        signed = result.data

    if len(signed) == 0:
        raise Exception(
            "Signed message is empty, see error message:%s" %
            result.stderr)

    result = gpg.encrypt(signed, recipients=gooddata_user, always_trust=True)
    encpryted = result.data

    if len(encpryted) == 0:
        raise Exception(
            "Encrypted message is empty, see error message:%s" %
            result.stderr)

    return encpryted


def open_url(url):
    # import locally to avoid potential missing package error
    import webbrowser
    webbrowser.open(url)


if __name__ == "__main__":
    arguments = parse_arguments()

    security_token = None
    if arguments.encrypted_file:
        security_token = get_security_token_from_file(arguments.encrypted_file)
    elif arguments.customer_user and arguments.login:
        security_token = create_security_token(
            arguments.gnupg_home,
            arguments.login,
            arguments.gooddata_user,
            arguments.customer_user,
            arguments.validity)
    else:
        raise Exception(
            "you must provide either --encrypted-file or"
            " --login AND --customer--user")

    url = generate_url(
        arguments.destination,
        arguments.customer_resource,
        arguments.server_url,
        arguments.target_url,
        security_token)

    if not arguments.dont_print:
        print(url)

    if arguments.open_browser:
        open_url(url)
