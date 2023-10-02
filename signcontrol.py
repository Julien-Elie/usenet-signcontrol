#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Script to help in managing Usenet hierarchies.  It generates control
# articles and handles PGP keys (generation and management).
#
# signcontrol.py -- v. 1.4.0 -- 2014/10/26
#
# Written and maintained by Julien ÉLIE.
#
# This script is distributed under the MIT License.  Please see the LICENSE
# section below for more information.
#
# Feel free to use it.  I would be glad to know whether you find it useful for
# your hierarchy.  Any bug reports, bug fixes, and improvements are very much
# welcome.
#
# Contact:
#   <https://www.trigofacile.com/maths/contact/index.htm>
# Issue tracker:
#   <https://github.com/Julien-Elie/usenet-signcontrol/issues>
#
# Upstream web site:
#   <https://www.trigofacile.com/divers/usenet/clefs/signcontrol.htm>
# Github repository:
#   <https://github.com/Julien-Elie/usenet-signcontrol>
# Please also read:
#   <https://www.eyrie.org/~eagle/faqs/usenet-hier.html>
#
# History:
#
# v. 1.4.0:  2014/10/26 -- add the --no-tty flag to gpg when --passphrase is
#            also used.  Otherwise, an error occurs when running signcontrol
#            from cron.  Thanks to Matija Nalis for the bug report.
#            - Add the PGP2_COMPATIBILITY parameter to generate control
#            articles compatible with MIT PGP 2.6.2 (or equivalent).
#            - When managing PGP keys, their full uid is now expected, instead
#            of only a subpart.
#            - Listing secret keys now also shows their fingerprint.
#            - Improve documentation, along with the creation of a Git
#             repository on Github.
#
# v. 1.3.3:  2011/07/11 -- automatically generate an Injection-Date: header
#            field, and sign it.  It will prevent control articles from being
#            maliciously reinjected into Usenet, and replayed by news servers
#            compliant with RFC 5537 (that is to say without cutoff on the
#            Date: header field when an Injection-Date: header field exists).
#
# v. 1.3.2:  2009/12/23 -- use local time instead of UTC (thanks to Adam
#            H. Kerman for the suggestion).
#            - Add flags to gpg when called:  --emit-version, --no-comments,
#            --no-escape-from-lines and --no-throw-keyids.  Otherwise, the
#            signature may not be valid (thanks to Robert Spier for the
#            bug report).
#
# v. 1.3.1:  2009/12/20 -- compliance with RFC 5322 (Internet Message Format):
#            use "-0000" instead of "+0000" to indicate a time zone at Universal
#            Time ("-0000" means that the time is generated on a system that
#            may be in a local time zone other than Universal Time); also remove
#            the Sender: header field.
#            - When a line in the body of a control article started with
#            "Sender", a bug in signcontrol prevented the article from being
#            properly signed.
#
# v. 1.3.0:  2009/07/28 -- remove the charset for a multipart/mixed block
#            in newgroup articles, change the default serial number from 0 to 1
#            in checkgroups articles, allow the user to interactively modify
#            his message (thanks to Matija Nalis for the idea).
#
# v. 1.2.1:  2008/12/07 -- ask for confirmation when "(Moderated)" is misplaced
#            in a newsgroup description.
#
# v. 1.2.0:  2008/11/17 -- support for USEPRO:  checkgroups scope, checkgroups
#            serial numbers and accurate Content-Type: header fields.
#
# v. 1.1.0:  2007/05/09 -- fix the newgroups line when creating a newsgroup,
#            use a separate config file, possibility to import signcontrol from
#            other scripts and use its functions.
#
# v. 1.0.0:  2007/05/01 -- initial release.


# THERE IS NOTHING USEFUL TO PARAMETER IN THIS FILE.
# The file "signcontrol.conf" contains all your parameters
# and it will be parsed.
CONFIGURATION_FILE = "signcontrol.conf"

import os
import re
import sys, traceback
import time
import shlex

# Current time.
TIME = time.localtime()


def str_input(string):
    """Get a value from the user, using input() in Python 3 or raw_input() in
    Python 2 as raw_input() is no longer defined in Python 3 (it was renamed
    input() but has a different behaviour in Python 2).
    Argument: string (the string to display)
    Return value: the input from the user
    """
    if sys.version_info[0] > 2:
        return input(string)
    else:
        return raw_input(string)


def treat_exceptions(type, value, stacktrace):
    """Pretty print stack traces of this script, in case an error occurs.
    Arguments: type (the type of the exception)
               value (the value of the exception)
               stacktrace (the traceback of the exception)
    No return value (the script exits with status 2)
    """
    print("-----------------------------------------------------------")
    print("\n".join(traceback.format_exception(type, value, stacktrace)))
    print("-----------------------------------------------------------")
    str_input("An error has just occurred.")
    sys.exit(2)


sys.excepthook = treat_exceptions


def print_error(error):
    """Pretty print error messages.
    Argument: error (the error to print)
    No return value
    """
    print("")
    print("--> " + error + " <--")
    print("")


def pretty_time(localtime):
    """Return the Date: header field.
    Argument: localtime (a time value, representing local time)
    Return value: a string suitable to be used in a Date: header field
    """
    # As "%z" does not work on every platform with strftime(), we compute
    # the time zone offset.
    # You might want to use UTC with either "+0000" or "-0000", also changing
    # time.localtime() to time.gmtime() for the definition of TIME above.
    if localtime.tm_isdst > 0 and time.daylight:
        offsetMinutes = -int(time.altzone / 60)
    else:
        offsetMinutes = -int(time.timezone / 60)
    offset = "%+03d%02d" % (offsetMinutes / 60.0, offsetMinutes % 60)
    return time.strftime("%a, %d %b %Y %H:%M:%S " + offset, localtime)


def serial_time(localtime):
    """Return a checkgroups serial number.
    Argument: localtime (a time value, representing local time)
    Return value: a string suitable to be used as a serial number
    """
    # Note that there is only one serial per day.
    return time.strftime("%Y%m%d", localtime)


def epoch_time(localtime):
    """Return the number of seconds since epoch.
    Argument: localtime (a time value, representing local time)
    Return value: the number of seconds since epoch, as a string
    """
    return str(int(time.mktime(localtime)))


def read_configuration(file):
    """Parse the configuration file.
    Argument: file (path to the signcontrol.conf configuration file)
    Return value: a dictionary {parameter: value} representing
                  the contents of the configuration file
    """
    TOKENS = [
        "PROGRAM_GPG",
        "PGP2_COMPATIBILITY",
        "ID",
        "MAIL",
        "HOST",
        "ADMIN_GROUP",
        "NAME",
        "CHECKGROUPS_SCOPE",
        "URL",
        "NEWGROUP_MESSAGE_MODERATED",
        "NEWGROUP_MESSAGE_UNMODERATED",
        "RMGROUP_MESSAGE",
        "PRIVATE_HIERARCHY",
        "CHECKGROUPS_FILE",
        "ENCODING",
    ]

    if not os.path.isfile(file):
        print("The configuration file is absent.")
        str_input("Please install it before using this script.")
        sys.exit(2)

    config_file = shlex.shlex(open(file, "r"), posix=True)
    config = dict()
    parameter = None
    while True:
        token = config_file.get_token()
        if not token:
            break
        if token[0] in "\"'":
            token = token[1:-1]
        if token in TOKENS:
            parameter = token
        elif token != "=" and parameter:
            if parameter == "PGP2_COMPATIBILITY":
                if token == "True" or token == "true":
                    config[parameter] = [("--pgp2", "-pgp2"), ("", "")]
                elif token == "Only" or token == "only":
                    config[parameter] = [("--pgp2", "-pgp2")]
                else:
                    config[parameter] = [("", "")]
            elif parameter == "PRIVATE_HIERARCHY":
                if token == "True" or token == "true":
                    config[parameter] = True
                else:
                    config[parameter] = False
            else:
                config[parameter] = token
            parameter = None
    for token in TOKENS:
        if token not in config:
            print("You must update the configuration file.")
            print("The parameter " + token + " is missing.")
            str_input(
                "Please download the latest version of the configuration file"
                " and parameter it before using this script."
            )
            sys.exit(2)
    return config


def read_checkgroups(path):
    """Parse a checkgroups file.
    Argument: path (path of the checkgroups file)
    Return value: a dictionary {newsgroup: description} representing
                  the contents of the checkgroups
    """
    # Usually for the first use of the script.
    if not os.path.isfile(path):
        print("No checkgroups file found.")
        print("Creating an empty checkgroups file...")
        write_checkgroups(dict(), path)

    groups = dict()

    for line in open(path):
        line2 = line.strip()
        while line2.find("\t\t") != -1:
            line2 = line2.replace("\t\t", "\t")
        try:
            group, description = line2.split("\t")
            groups[group] = description
        except:
            print_error("The current checkgroups is badly formed.")
            print("The offending line is:")
            print(line)
            print("")
            str_input("Please correct it before using this script.")
            sys.exit(2)

    return groups


def write_checkgroups(groups, path):
    """Write the current checkgroups file.
    Arguments: groups (a dictionary representing a checkgroups)
               path (path of the checkgroups file)
    No return value
    """
    keys = sorted(groups.keys())
    checkgroups_file = open(path, "w")
    for key in keys:
        if len(key) < 8:
            checkgroups_file.write(key + "\t\t\t" + groups[key] + "\n")
        elif len(key) < 16:
            checkgroups_file.write(key + "\t\t" + groups[key] + "\n")
        else:
            checkgroups_file.write(key + "\t" + groups[key] + "\n")
    checkgroups_file.close()
    print("Checkgroups file written.")
    print("")


def choice_menu():
    """Print the initial menu, and waits for the user to make a choice.
    Return value: the number representing the user's choice
    """
    while True:
        print("""
What do you want to do?
-----------------------
1. Generate a newgroup control article (create or change a newsgroup)
2. Generate an rmgroup control article (remove a newsgroup)
3. Generate a checkgroups control article (list of newsgroups)
4. Manage my PGP keys (generate/import/export/remove/revoke)
5. Quit
""")
        try:
            choice = int(str_input("Your choice (1-5): "))
            if int(choice) not in list(range(1, 6)):
                raise ValueError()
            print("")
            return choice
        except:
            print_error("Please enter a number between 1 and 5.")


def manage_menu():
    """Print the menu related to the management of PGP keys, and waits
    for the user to make a choice.
    Return value: the number representing the user's choice
    """
    while True:
        print("""
What do you want to do?
-----------------------
1. See the current installed keys
2. Generate a new pair of secret/public keys
3. Export a public key
4. Export a secret key
5. Import a secret key
6. Remove a pair of secret/public keys
7. Revoke a secret key
8. Quit
""")
        try:
            choice = int(str_input("Your choice (1-8): "))
            if int(choice) not in list(range(1, 9)):
                raise ValueError()
            print("")
            return choice
        except:
            print_error("Please enter a number between 1 and 8.")


def generate_signed_message(
    config, file_message, group, message_id, type, passphrase=None, flag=""
):
    """Generate signed control articles.
    Arguments: config (the dictionary of parameters from signcontrol.conf)
               file_message (the file name of the message to sign)
               group (the name of the newsgroup)
               message_id (the Message-ID of the message)
               type (the type of the control article)
               passphrase (if given, the passphrase of the private key)
               flag (if given, the additional flag(s) to pass to gpg)
    No return value
    """
    signatureWritten = False

    if passphrase:
        os.system(
            config["PROGRAM_GPG"]
            + " --emit-version --no-comments --no-escape-from-lines"
            ' --no-throw-keyids --armor --detach-sign --local-user "='
            + config["ID"]
            + '" --no-tty --passphrase "'
            + passphrase
            + '" --output '
            + file_message
            + ".pgp "
            + flag
            + " "
            + file_message
            + ".txt"
        )
    else:
        os.system(
            config["PROGRAM_GPG"]
            + " --emit-version --no-comments --no-escape-from-lines"
            ' --no-throw-keyids --armor --detach-sign --local-user "='
            + config["ID"]
            + '" --output '
            + file_message
            + ".pgp "
            + flag
            + " "
            + file_message
            + ".txt"
        )

    if not os.path.isfile(file_message + ".pgp"):
        print_error("Signature generation failed.")
        print("Please verify the availability of the secret key.")
        return

    result = open(file_message + ".sig", "w")
    for line in open(file_message + ".txt", "r"):
        if signatureWritten:
            result.write(line)
            continue

        if not line.startswith("X-Signed-Headers"):
            # From: is the last signed header field.
            if not line.startswith("From"):
                result.write(line)
            else:
                # Rewrite the From: line exactly as we already wrote it.
                result.write(
                    "From: " + config["NAME"] + " <" + config["MAIL"] + ">\n"
                )
                result.write("Approved: " + config["MAIL"] + "\n")
                if type == "checkgroups" and not config["PRIVATE_HIERARCHY"]:
                    result.write(
                        "Newsgroups: " + group + ",news.admin.hierarchies\n"
                    )
                    result.write("Followup-To: " + group + "\n")
                else:
                    result.write("Newsgroups: " + group + "\n")
                result.write("Path: not-for-mail\n")
                result.write("X-Info: " + config["URL"] + "\n")
                result.write(
                    "\thttps://ftp.isc.org/pub/pgpcontrol/README.html\n"
                )
                result.write("MIME-Version: 1.0\n")
                if type == "newgroup":
                    result.write(
                        "Content-Type: multipart/mixed;"
                        ' boundary="signcontrol"\n'
                    )
                elif type == "checkgroups":
                    result.write(
                        "Content-Type: application/news-checkgroups; charset="
                        + config["ENCODING"]
                        + "\n"
                    )
                else:  # if type == 'rmgroup':
                    result.write(
                        "Content-Type: text/plain; charset="
                        + config["ENCODING"]
                        + "\n"
                    )
                result.write("Content-Transfer-Encoding: 8bit\n")
                for line2 in open(file_message + ".pgp", "r"):
                    if line2.startswith("-"):
                        continue
                    if line2.startswith("Version:"):
                        version = line2.replace("Version: ", "")
                        version = version.replace(" ", "_")
                        result.write(
                            "X-PGP-Sig: "
                            + version.rstrip()
                            + " Subject,Control,Message-ID,Date"
                            + ",Injection-Date,From\n"
                        )
                    elif len(line2) > 2:
                        result.write("\t" + line2.rstrip() + "\n")
                signatureWritten = True

    result.close()

    os.remove(file_message + ".pgp")

    print("")
    if flag:
        print(
            "Do not worry if the program complains about detached signatures"
            " or MD5."
        )
    print("You can now post the file " + file_message + ".sig using rnews")
    print("or a similar tool.")
    print("")
    # print("Or you can also try to send it with IHAVE.  If it fails,"
    #       " it means that the article")
    # print("has not been sent.  You will then have to manually use rnews"
    #       " or a similar program.")
    # if str_input("Do you want to try? (y/n) ") == "y":
    #    import nntplib
    #    news_server = nntplib.NNTP(HOST, PORT, USER, PASSWORD)
    #    news_server.ihave(message_id, file_message + ".sig")
    #    news_server.quit()
    #    print("The control article has just been sent!")


def sign_message(
    config, file_message, group, message_id, type, passphrase=None
):
    """Sign a control article.
    Arguments: config (the dictionary of parameters from signcontrol.conf)
               file_message (the file name of the message to sign)
               group (the name of the newsgroup)
               message_id (the Message-ID of the message)
               type (the type of the control article)
               passphrase (if given, the passphrase of the private key)
    No return value
    """
    articles_to_generate = len(config["PGP2_COMPATIBILITY"])
    i = 1
    for flag, suffix in config["PGP2_COMPATIBILITY"]:
        if articles_to_generate > 1:
            print("")
            print(
                "Generation of control article "
                + str(i)
                + "/"
                + str(articles_to_generate)
            )
            i += 1
        if suffix:
            additional_file = open(file_message + suffix + ".txt", "w")
            additional_message_id = message_id.replace("@", suffix + "@", 1)
            for line in open(file_message + ".txt", "r"):
                if line == "Message-ID: " + message_id + "\n":
                    line = "Message-ID: " + additional_message_id + "\n"
                additional_file.write(line)
            additional_file.close()
            generate_signed_message(
                config,
                file_message + suffix,
                group,
                additional_message_id,
                type,
                passphrase,
                flag,
            )
            os.remove(file_message + suffix + ".txt")
        else:
            generate_signed_message(
                config, file_message, group, message_id, type, passphrase, flag
            )


def generate_newgroup(
    groups,
    config,
    group=None,
    moderated=None,
    description=None,
    message=None,
    passphrase=None,
):
    """Create a new group.
    Arguments: groups (the dictionary representing the checkgroups)
               config (the dictionary of parameters from signcontrol.conf)
               group (if given, the name of the newsgroup)
               moderated (if given, whether the newsgroup is moderated)
               description (if given, the description of the newsgroup)
               message (if given, the text to write in the control article)
               passphrase (if given, the passphrase of the private key)
    No return value
    """
    while not group:
        group = str_input("Name of the newsgroup to create: ").lower()
        components = group.split(".")
        if len(components) < 2:
            group = None
            print_error("The group must have at least two components.")
        elif not components[0][0:1].isalpha():
            group = None
            print_error("The first component must start with a letter.")
        elif components[0] in ["control", "example", "to"]:
            group = None
            print_error(
                'The first component must not be "control", "example" or "to".'
            )
        elif re.search("[^a-z0-9+_.-]", group):
            group = None
            print_error(
                "The group must not contain characters other than"
                " [a-z0-9+_.-]."
            )
        for component in components:
            if component in ["all", "ctl"]:
                group = None
                print_error(
                    'Sequences "all" and "ctl" must not be used as components.'
                )
            elif not component[0:1].isalnum():
                group = None
                print_error(
                    "Each component must start with a letter or a digit."
                )
            elif component.isdigit():
                group = None
                print_error(
                    "Each component must contain at least one non-digit"
                    " character."
                )

    if group in groups:
        print("")
        print("The newsgroup " + group + " already exists.")
        print(
            "These new settings (status and description) will override the"
            " current ones."
        )
        print("")

    if moderated is None:
        if str_input("Is " + group + " a moderated newsgroup? (y/n) ") == "y":
            moderated = True
            print("")
            print(
                'There is no need to add " (Moderated)" at the very end of the'
                " description."
            )
            print("It will be automatically added, if not already present.")
            print("")
        else:
            moderated = False

    while not description:
        print("")
        print(
            "The description should start with a capital and end in a period."
        )
        description = str_input("Description of " + group + ": ")
        if len(description) > 56:
            print_error("The description is too long.  You should shorten it.")
            if (
                str_input(
                    "Do you want to continue despite this recommendation?"
                    " (y/n) "
                )
                != "y"
            ):
                description = None
                continue

        moderated_count = description.count("(Moderated)")
        if moderated_count > 0:
            if not moderated:
                if description.endswith(" (Moderated)"):
                    description = None
                    print_error(
                        'The description must not end with " (Moderated)".'
                    )
                    continue
                else:
                    print_error(
                        'The description must not contain "(Moderated)".'
                    )
                    if (
                        str_input(
                            "Do you want to continue despite this"
                            " recommendation? (y/n) "
                        )
                        != "y"
                    ):
                        description = None
                        continue
            elif moderated_count > 1 or not description.endswith(
                " (Moderated)"
            ):
                print_error('The description must not contain "(Moderated)".')
                if (
                    str_input(
                        "Do you want to continue despite this recommendation?"
                        " (y/n) "
                    )
                    != "y"
                ):
                    description = None
                    continue

    if not message:
        print("")
        print("The current message which will be sent is:")
        print("")

        if moderated:
            message = config["NEWGROUP_MESSAGE_MODERATED"].replace(
                "$GROUP$", group
            )
        else:
            message = config["NEWGROUP_MESSAGE_UNMODERATED"].replace(
                "$GROUP$", group
            )

        print(message)
        print("")
        if str_input("Do you want to change it? (y/n) ") == "y":
            print("")
            print("Please enter the message you want to send.")
            print('End it with a line containing only "." (a dot).')
            print("")

            message = ""
            buffer = str_input("Message: ") + "\n"
            while buffer != ".\n":
                message += buffer.rstrip() + "\n"
                buffer = str_input("Message: ") + "\n"
            print("")

    print("")
    print("Here is the information about the newsgroup:")
    print("Name: " + group)

    if moderated:
        print("Status: moderated")
        if not description.endswith(" (Moderated)"):
            description += " (Moderated)"
    else:
        print("Status: unmoderated")
    print("Description: " + description)
    print("Message: ")
    print("")
    print(message)
    print("")

    if (
        str_input(
            "Do you want to generate a control article for "
            + group
            + "? (y/n) "
        )
        == "y"
    ):
        print("")
        file_newgroup = group + "-" + epoch_time(TIME)
        result = open(file_newgroup + ".txt", "w")
        result.write(
            "X-Signed-Headers:"
            " Subject,Control,Message-ID,Date,Injection-Date,From\n"
        )
        if moderated:
            result.write("Subject: cmsg newgroup " + group + " moderated\n")
            result.write("Control: newgroup " + group + " moderated\n")
        else:
            result.write("Subject: cmsg newgroup " + group + "\n")
            result.write("Control: newgroup " + group + "\n")
        message_id = (
            "<newgroup-"
            + group
            + "-"
            + epoch_time(TIME)
            + "@"
            + config["HOST"]
            + ">"
        )
        result.write("Message-ID: " + message_id + "\n")
        result.write("Date: " + pretty_time(TIME) + "\n")
        result.write("Injection-Date: " + pretty_time(TIME) + "\n")
        result.write(
            "From: " + config["NAME"] + " <" + config["MAIL"] + ">\n\n"
        )
        result.write("This is a MIME NetNews control message.\n")
        result.write("--signcontrol\n")
        result.write(
            "Content-Type: text/plain; charset=" + config["ENCODING"] + "\n\n"
        )
        result.write(message + "\n")
        result.write("\n\n--signcontrol\n")
        result.write(
            "Content-Type: application/news-groupinfo; charset="
            + config["ENCODING"]
            + "\n\n"
        )
        result.write("For your newsgroups file:\n")
        if len(group) < 8:
            result.write(group + "\t\t\t" + description + "\n")
        elif len(group) < 16:
            result.write(group + "\t\t" + description + "\n")
        else:
            result.write(group + "\t" + description + "\n")
        result.write("\n--signcontrol--\n")
        result.close()
        sign_message(
            config, file_newgroup, group, message_id, "newgroup", passphrase
        )
        os.remove(file_newgroup + ".txt")

    if (
        str_input("Do you want to update the current checkgroups file? (y/n) ")
        == "y"
    ):
        groups[group] = description
        write_checkgroups(groups, config["CHECKGROUPS_FILE"])


def generate_rmgroup(
    groups, config, group=None, message=None, passphrase=None
):
    """Remove a group.
    Arguments: groups (the dictionary representing the checkgroups)
               config (the dictionary of parameters from signcontrol.conf)
               group (if given, the name of the newsgroup)
               message (if given, the text to write in the control article)
               passphrase (if given, the passphrase of the private key)
    No return value
    """
    while not group:
        group = str_input("Name of the newsgroup to remove: ").lower()

    if group not in groups:
        print("")
        print("The newsgroup " + group + " does not exist.")
        print("Yet, you can send an rmgroup message for it if you want.")
        print("")

    if (
        str_input(
            "Do you want to generate a control article to *remove* "
            + group
            + "? (y/n) "
        )
        == "y"
    ):
        print("")

        if not message:
            print("The current message which will be sent is:")
            print("")

            message = config["RMGROUP_MESSAGE"].replace("$GROUP$", group)

            print(message)
            print("")
            if str_input("Do you want to change it? (y/n) ") == "y":
                print("")
                print("Please enter the message you want to send.")
                print('End it with a line containing only "." (a dot).')
                print("")

                message = ""
                buffer = str_input("Message: ") + "\n"
                while buffer != ".\n":
                    message += buffer.rstrip() + "\n"
                    buffer = str_input("Message: ") + "\n"
                print("")

        file_rmgroup = group + "-" + epoch_time(TIME)
        result = open(file_rmgroup + ".txt", "w")
        result.write(
            "X-Signed-Headers:"
            " Subject,Control,Message-ID,Date,Injection-Date,From\n"
        )
        result.write("Subject: cmsg rmgroup " + group + "\n")
        result.write("Control: rmgroup " + group + "\n")
        message_id = (
            "<rmgroup-"
            + group
            + "-"
            + epoch_time(TIME)
            + "@"
            + config["HOST"]
            + ">"
        )
        result.write("Message-ID: " + message_id + "\n")
        result.write("Date: " + pretty_time(TIME) + "\n")
        result.write("Injection-Date: " + pretty_time(TIME) + "\n")
        result.write(
            "From: " + config["NAME"] + " <" + config["MAIL"] + ">\n\n"
        )
        result.write(message + "\n")
        result.close()
        sign_message(
            config, file_rmgroup, group, message_id, "rmgroup", passphrase
        )
        os.remove(file_rmgroup + ".txt")

    if group in groups:
        if (
            str_input(
                "Do you want to update the current checkgroups file? (y/n) "
            )
            == "y"
        ):
            del groups[group]
            write_checkgroups(groups, config["CHECKGROUPS_FILE"])


def generate_checkgroups(config, passphrase=None, serial=None):
    """List the groups of the hierarchy.
    Arguments: config (the dictionary of parameters from signcontrol.conf)
               passphrase (if given, the passphrase of the private key)
               serial (if given, the serial value to use)
    No return value
    """
    while serial not in list(range(0, 100)):
        try:
            print(
                "If it is your first checkgroups for today, leave it blank"
                " (default is 1)."
            )
            print("Otherwise, increment this revision number by one.")
            serial = int(str_input("Revision to use (1-99): "))
            print("")
        except:
            serial = 1

    serial = "%02d" % serial
    file_checkgroups = "checkgroups-" + epoch_time(TIME)
    result = open(file_checkgroups + ".txt", "w")
    result.write(
        "X-Signed-Headers:"
        " Subject,Control,Message-ID,Date,Injection-Date,From\n"
    )
    result.write(
        "Subject: cmsg checkgroups "
        + config["CHECKGROUPS_SCOPE"]
        + " #"
        + serial_time(TIME)
        + serial
        + "\n"
    )
    result.write(
        "Control: checkgroups "
        + config["CHECKGROUPS_SCOPE"]
        + " #"
        + serial_time(TIME)
        + serial
        + "\n"
    )
    message_id = (
        "<checkgroups-" + epoch_time(TIME) + "@" + config["HOST"] + ">"
    )
    result.write("Message-ID: " + message_id + "\n")
    result.write("Date: " + pretty_time(TIME) + "\n")
    result.write("Injection-Date: " + pretty_time(TIME) + "\n")
    result.write("From: " + config["NAME"] + " <" + config["MAIL"] + ">\n\n")
    for line in open(config["CHECKGROUPS_FILE"], "r"):
        result.write(line.rstrip() + "\n")
    result.close()
    sign_message(
        config,
        file_checkgroups,
        config["ADMIN_GROUP"],
        message_id,
        "checkgroups",
        passphrase,
    )
    os.remove(file_checkgroups + ".txt")


def manage_keys(config):
    """Useful wrappers around the gpg program to manage PGP keys
    (generate, import, export, remove, and revoke).
    Argument: config (the dictionary of parameters from signcontrol.conf)
    No return value
    """
    choice = 0
    while choice != 8:
        choice = manage_menu()
        if choice == 1:
            print("You currently have the following secret keys installed:")
            print("")
            os.system(
                config["PROGRAM_GPG"]
                + " --list-secret-keys --with-fingerprint"
            )
            print(
                "Please note that the uid of your secret key and the value of"
            )
            print(
                "the ID parameter set in signcontrol.conf should be the same."
            )
        elif choice == 2:
            print("""
-----------------------------------------------------------------------
Please put the e-mail address from which you will send control articles
in the key ID (the real name field).  And leave the other fields blank,
for better compatibility with Usenet software.
Choose a 2048-bit RSA key which never expires.
You should also provide a passphrase, for security reasons.
There is no need to edit the key after it has been generated.

Please note that the key generation may not finish if it is launched
on a remote server, owing to a lack of enough entropy.  Use your own
computer instead and import the key on the remote one afterwards.
-----------------------------------------------------------------------
""")
            os.system(
                config["PROGRAM_GPG"] + " --gen-key --allow-freeform-uid"
            )
            print("""
After having generated these keys, you should export your PUBLIC key
and make it public (in the web site of your hierarchy, along with
a current checkgroups, and also announce it in news.admin.hierarchies).
You can also export your PRIVATE key for backup only.""")
        elif choice == 3:
            print("The key will be written to the file public-key.asc.")
            key_name = str_input(
                "Please enter the uid of the public key to export: "
            )
            os.system(
                config["PROGRAM_GPG"]
                + ' --armor --output public-key.asc --export "='
                + key_name
                + '"'
            )
        elif choice == 4:
            print("The key will be written to the file private-key.asc.")
            key_name = str_input(
                "Please enter the uid of the secret key to export: "
            )
            os.system(
                config["PROGRAM_GPG"]
                + ' --armor --output private-key.asc --export-secret-keys "='
                + key_name
                + '"'
            )
            if os.path.isfile("private-key.asc"):
                os.chmod("private-key.asc", 0o400)
                print("""
Be careful: it is a security risk to export your private key.
Please make sure that nobody has access to it.""")
        elif choice == 5:
            str_input(
                "Please put it in a file named secret-key.asc and press enter."
            )
            os.system(config["PROGRAM_GPG"] + " --import secret-key.asc")
            print("""
Make sure that both the secret and public keys have properly been imported.
Their uid should be put as the value of the ID parameter set in
signcontrol.conf.""")
        elif choice == 6:
            key_name = str_input(
                "Please enter the uid of the key to *remove*: "
            )
            os.system(
                config["PROGRAM_GPG"]
                + ' --delete-secret-and-public-key "='
                + key_name
                + '"'
            )
        elif choice == 7:
            key_name = str_input(
                "Please enter the uid of the secret key to revoke: "
            )
            os.system(
                config["PROGRAM_GPG"] + ' --gen-revoke "=' + key_name + '"'
            )
        print("")


if __name__ == "__main__":
    """The main function."""
    config = read_configuration(CONFIGURATION_FILE)
    if not os.path.isfile(config["PROGRAM_GPG"]):
        print(
            "You must install GnuPG <https://www.gnupg.org/> and edit this"
            " script to put"
        )
        print("the path to the gpg binary.")
        str_input("Please install it before using this script.")
        sys.exit(2)
    choice = 0
    while choice != 5:
        groups = read_checkgroups(config["CHECKGROUPS_FILE"])
        # Update time whenever we come back to the main menu.
        TIME = time.localtime()
        choice = choice_menu()
        if choice == 1:
            generate_newgroup(groups, config)
        elif choice == 2:
            generate_rmgroup(groups, config)
        elif choice == 3:
            generate_checkgroups(config)
        elif choice == 4:
            manage_keys(config)


# Embedded documentation.
POD = """
=encoding utf8

=head1 NAME

signcontrol.py - Generate PGP-signed control articles for Usenet hierarchies

=head1 SYNOPSIS

B<python signcontrol.py>

=head1 DESCRIPTION

B<signcontrol.py> is a Python script aimed at helping Usenet hierarchy
administrators in maintaining the canonical lists of newsgroups in the
hierarchies they administer.

This script is also useful to manage PGP keys: generation, import, export,
removal, and revokal.  It works on every platform on which Python and GnuPG
are available (Windows, Linux, etc.).

It also enforces best practices regarding the syntax of Usenet control
articles.

Getting started is as simple as:

=over 4

=item 1.

Downloading and installing L<Python|https://www.python.org/>.  However,
make sure to use S<Python 2.x> because B<signcontrol.py> is not compatible
yet with S<Python 3.x>.

=item 2.

Downloading and installing L<GnuPG|https://www.gnupg.org/>.

=item 3.

Downloading both the F<signcontrol.py> program and its F<signcontrol.conf>
configuration file.

=item 4.

Editing the F<signcontrol.conf> configuration file so that it properly fits
your installation.

=item 5.

Running C<python signcontrol.py>.

If you intend to generate several control articles during a single run of this
script, you can make use of B<gpg-agent> so as to type your passphrase only
once.  Running C<gpg-agent --daemon signcontrol.py> should work.

If you're running B<signcontrol.py> through a remote terminal, you may have
to execute C<chown user $(tty)> as I<root> before running B<signcontrol.py>
as I<user> to allow the input of a passphrase.  (B<gpg> will otherwise fail.)

=back

=head1 SUPPORT

To report an issue or ask a question, please use the L<issue tracker on
GitHub|https://github.com/Julien-Elie/usenet-signcontrol>.

Instructions written in French are also available at
L<https://www.trigofacile.com/divers/usenet/clefs/signcontrol.htm>.

=head1 SOURCE REPOSITORY

B<signcontrol.py> is maintained using Git.  You can
access the current source on the L<web interface of
GitHub|https://github.com/Julien-Elie/usenet-signcontrol> or by cloning the
repository at:

    https://github.com/Julien-Elie/usenet-signcontrol.git

When contributing modifications, either patches or Git pull requests are
welcome.

=head1 CONFIGURATION FILE

The following parameters can be modified in the F<signcontrol.conf>
configuration file:

=over 4

=item B<PROGRAM_GPG>

The path to the required GPG executable.  It is usually
C<C:\Progra~1\GNU\GnuPG\gpg.exe> or C</usr/bin/gpg>.

=item B<PGP2_COMPATIBILITY>

Whether compatibility with MIT S<PGP 2.6.2> (or equivalent) should be kept.
Though this is now fairly obsolete, a few news servers still haven't been
updated to be able to process newer and more secure signing algorithms.
Such servers do not recognize recent signing algorithms; however, current news
servers may refuse to process messages signed with the insecure MD5 algorithm.

Possible values are C<True>, C<False> or C<Only> (default is C<False>).

When set to C<True>, B<signcontrol.py> will generate two control articles: one
in a format compatible with MIT S<PGP 2.6.2> (or equivalent) and another with
a newer and more secure format.  Sending these two control articles will then
ensure a widest processing.

When set to C<False>, B<signcontrol.py> will only generate control articles in
a newer and more secure format.

When set to C<Only>, B<signcontrol.py> will only generate control articles in
a format compatible with MIT S<PGP 2.6.2> (or equivalent).

=item B<ID>

One of the user ID of the PGP key used to sign control articles.  The user ID
is the whole contents of a C<uid> line, as shown in a list of all keys from
the secret keyring.

Note that if you do not already have a PGP key, B<signcontrol.py> can generate
one for you.

=item B<MAIL>

The e-mail from which control articles are sent.

=item B<HOST>

The host which appears in the second part of the Message-ID of generated
control articles.  It is usually the name of a news server.

=item B<ADMIN_GROUP>

An existing newsgroup of the hierarchy (where checkgroups control articles
will be fed).  If an administrative newsgroup exists, put it.  Otherwise, any
other newsgroup of the hierarchy will be fine.

=item B<NAME>

The name which appears in the From header field.  You should only use
ASCII characters.  Otherwise, you have to MIME-encode it (for instance:
C<=?ISO-8859-15?Q?Julien_=C9LIE?=>).

=item B<CHECKGROUPS_SCOPE>

The scope of the hierarchy according to L<< S<Section 5.2.3> of S<RFC
5537>|https://datatracker.ietf.org/doc/html/rfc5537#section-5.2.3 >>.
For instance: C<fr> (for fr.*), C<de !de.alt> (for de.* excepting de.alt.*)
or C<de.alt> (for de.alt.*).

=item B<URL>

The URL where the public PGP key can be found.  If you do not have any, leave
C<https://ftp.isc.org/pub/pgpcontrol/README.html>.  If you want to add more
URLs (like the home page of the hierarchy), use a multi-line text where each
line, except for the first, begins with a tabulation.

=item B<NEWGROUP_MESSAGE_MODERATED>, B<NEWGROUP_MESSAGE_UNMODERATED>,
B<RMGROUP_MESSAGE>

The message which will be written in the corresponding control article.
All occurrences of C<$GROUP$> will be replaced by the name of the newsgroup.

=item B<PRIVATE_HIERARCHY>

Whether the hierarchy is public or private.  If it is private (that is to say
if it is intended to remain in a local server with private access and if it
is not fed to other Usenet news servers), the value should be C<True>, so that
checkgroups control articles are not crossposted to the news.admin.hierarchies
newsgroup.  Possible values are C<True> or C<False> (default is C<False>).

=item B<CHECKGROUPS_FILE>

The file which contains the current checkgroups.

=item B<ENCODING>

The encoding of control articles.  The default value is C<UTF-8>, which is the
charset that SHOULD be used for non-ASCII characters, per L<< S<Section 4.2>
of S<RFC 5537>|https://datatracker.ietf.org/doc/html/rfc5537#section-4.2 >>.

=back

=head1 USEFUL RESOURCES

Here are some resources that can be useful to be aware of:

=over 4

=item Usenet Hierarchy Administration FAQ:
L<https://www.eyrie.org/~eagle/faqs/usenet-hier.html>

=item Usenet hierarchy information:
L<http://usenet.trigofacile.com/hierarchies/>

=item Hosting service for hierarchy administrators:
L<http://www.news-admin.org/>

=back

=head1 LICENSE

The B<usenet-signcontrol> package as a whole is covered by the following
copyright statement and license:

Copyright (c) 2007-2009, 2011, 2014, 2023 Julien ÉLIE

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.



For any copyright range specified by files in this package as "YYYY-ZZZZ", the
range specifies every single year in that closed interval.

=head1 HISTORY

B<signcontrol.py> was written by Julien ÉLIE.

=head1 SEE ALSO

gpg(1), gpg-agent(1).

=cut
"""
