#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Script to help in managing Usenet hierarchies.  It generates control
# articles and handles PGP keys (generation and management).
#
# signcontrol.py -- v. 1.4.0 -- 2014/xx/xx (not yet released).
#
# Written and maintained by Julien ÉLIE.
#
# The source code is free to use, distribute, modify, and study.
# It is distributed under the MIT License.
#
# Feel free to use it.  I would be glad to know whether you find it useful for
# your hierarchy.  Any bug reports, bug fixes, and improvements are very much
# welcome.
#
# Contact:
#   <http://www.trigofacile.com/maths/contact/index.htm>.
# Issue tracker:
#   <https://github.com/Julien-Elie/usenet-signcontrol/issues>.
#
# Upstream web site:
#   <http://www.trigofacile.com/divers/usenet/clefs/signcontrol.htm>.
# Github repository:
#   <https://github.com/Julien-Elie/usenet-signcontrol>.
# Please also read:
#   <http://www.eyrie.org/~eagle/faqs/usenet-hier.html>.
#
# History:
#
# v. 1.4.0:  2014/xx/xx -- add the --no-tty flag to gpg when --passphrase is
#            also used.  Otherwise, an error occurs when running signcontrol
#            from cron.  Thanks to Matija Nalis for the bug report.
#
# v. 1.3.3:  2011/07/11 -- automatically generate an Injection-Date: header
#            field, and sign it.  It will prevent control articles from being
#            maliciously reinjected into Usenet, and replayed by news servers
#            compliant with RFC 5537 (that is to say without cutoff on the
#            Date: header field when an Injection-Date: header field exists).
#
# v. 1.3.2:  2009/12/23 -- use local time instead of UTC (thanks to Adam
#            H. Kerman for the suggestion).
#            Add flags to gpg when called:  --emit-version, --no-comments,
#            --no-escape-from-lines and --no-throw-keyids.  Otherwise, the
#            signature may not be valid (thanks to Robert Spier for the
#            bug report).
#
# v. 1.3.1:  2009/12/20 -- compliance with RFC 5322 (Internet Message Format):
#            use "-0000" instead of "+0000" to indicate a time zone at Universal
#            Time ("-0000" means that the time is generated on a system that
#            may be in a local time zone other than Universal Time); also remove
#            the Sender: header field.
#            When a line in the body of a control article started with "Sender",
#            a bug in signcontrol prevented the article from being properly
#            signed.
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
CONFIGURATION_FILE = 'signcontrol.conf'

import os
import re
import sys, traceback
import time
import shlex

# Current time.
TIME = time.localtime()


def treat_exceptions(type, valeur, trace):
    """Pretty print stack traces of this script, in case an error occurs."""
    print "-----------------------------------------------------------"
    print "\n".join(traceback.format_exception(type, valeur, trace))
    print "-----------------------------------------------------------"
    raw_input('An error has just occurred.')
    sys.exit(2)
sys.excepthook = treat_exceptions


def print_error(error):
    """Pretty print error messages."""
    print
    print '--> ' + error + ' <--'
    print


def pretty_time(localtime):
    """Return the Date: header field."""
    # As "%z" does not work on every platform with strftime(), we compute
    # the time zone offset.
    # You might want to use UTC with either "+0000" or "-0000", also changing
    # time.localtime() to time.gmtime() for the definition of TIME above.
    if localtime.tm_isdst > 0 and time.daylight:
        offsetMinutes = - int(time.altzone / 60)
    else:
        offsetMinutes = - int(time.timezone / 60)
    offset = "%+03d%02d" % (offsetMinutes / 60.0, offsetMinutes % 60)
    return time.strftime('%a, %d %b %Y %H:%M:%S ' + offset, localtime)


def serial_time(localtime):
    """Return a checkgroups serial number."""
    # Note that there is only one serial per day.
    return time.strftime('%Y%m%d', localtime)


def epoch_time(localtime):
    """Return the number of seconds since epoch."""
    return str(int(time.mktime(localtime)))


def read_configuration(file):
    """Parse the configuration file."""
    TOKENS = ['PROGRAM_GPG', 'ID', 'MAIL', 'HOST', 'ADMIN_GROUP', 'NAME',
              'CHECKGROUPS_SCOPE', 'URL',
              'NEWGROUP_MESSAGE_MODERATED', 'NEWGROUP_MESSAGE_UNMODERATED',
              'RMGROUP_MESSAGE', 'PRIVATE_HIERARCHY', 'CHECKGROUPS_FILE',
              'ENCODING']
    
    if not os.path.isfile(file):
        print 'The configuration file is absent.'
        raw_input('Please install it before using this script.')
        sys.exit(2)
    
    config_file = shlex.shlex(open(file, 'r'), posix=True)
    config = dict()
    parameter = None
    while True:
        token = config_file.get_token()
        if not token:
            break
        if token[0] in '"\'':
            token = token[1:-1]
        if token in TOKENS:
            parameter = token
        elif token != '=' and parameter:
            if parameter == 'PRIVATE_HIERARCHY':
                if token == 'True':
                    config[parameter] = True
                else:
                    config[parameter] = False
            else:
                config[parameter] = token
            parameter = None
    for token in TOKENS:
        if not config.has_key(token):
            print 'You must update the configuration file.'
            print 'The parameter ' + token + ' is missing.'
            raw_input('Please download a new configuration file and parameter it before using this script.')
            sys.exit(2)
    return config


def read_checkgroups(path):
    """Open a checkgroups file and return a dictionary {group: description}."""
    # Usually for the first use of the script.
    if not os.path.isfile(path):
        print 'No checkgroups file found.'
        print 'Creating an empty checkgroups file...'
        write_checkgroups(dict(), path)
    
    groups = dict()
    
    for line in file(path):
        line2 = line.strip()
        while line2.find('\t\t') != -1:
            line2 = line2.replace('\t\t', '\t')
        try:
            group, description = line2.split('\t')
            groups[group] = description
        except:
            print_error('The current checkgroups is badly formed.')
            print 'The offending line is:'
            print line
            print
            raw_input('Please correct it before using this script.')
            sys.exit(2)
    
    return groups


def write_checkgroups(groups, path):
    """Write the current checkgroups file."""
    keys = groups.keys()
    keys.sort()
    checkgroups_file = file(path, 'wb')
    for key in keys:
        if len(key) < 8:
            checkgroups_file.write(key + '\t\t\t' + groups[key] + '\n')
        elif len(key) < 16:
            checkgroups_file.write(key + '\t\t' + groups[key] + '\n')
        else:
            checkgroups_file.write(key + '\t' + groups[key] + '\n')
    checkgroups_file.close()
    print 'Checkgroups file written.'
    print


def choice_menu():
    """Initial menu."""
    while True:
        print
        print 'What do you want to do?'
        print '-----------------------'
        print '1. Generate a newgroup control article (create or change a newsgroup)'
        print '2. Generate a rmgroup control article (remove a newsgroup)'
        print '3. Generate a checkgroups control article (list of newsgroups)'
        print '4. Manage my PGP keys (generate/import/export/remove/revoke)'
        print '5. Quit'
        print
        try:
            choice = int(raw_input('Your choice (1-5): '))
            if int(choice) not in range(1,6):
                raise ValueError()
            print
            return choice
        except:
            print_error('Please enter a number between 1 and 5.')


def manage_menu():
    """Second menu for the management of PGP keys."""
    while True:
        print
        print 'What do you want to do?'
        print '-----------------------'
        print '1. See the current installed keys'
        print '2. Generate a new pair of secret/public keys'
        print '3. Export a public key'
        print '4. Export a secret key'
        print '5. Import a secret key'
        print '6. Remove a pair of secret/public keys'
        print '7. Revoke a secret key'
        print '8. Quit'
        print
        try:
            choice = int(raw_input('Your choice (1-8): '))
            if int(choice) not in range(1,9):
                raise ValueError()
            print
            return choice
        except:
            print_error('Please enter a number between 1 and 8.')


def sign_message(config, file_message, group, message_id, type, passphrase=None):
    """Sign a control article."""
    signatureWritten = False

    if passphrase:
        os.system(config['PROGRAM_GPG'] + ' --emit-version --no-comments --no-escape-from-lines --no-throw-keyids --pgp2 -a -b -u "'+ config['ID'] + '" --no-tty --passphrase "' + passphrase + '" -o ' + file_message + '.pgp ' + file_message + '.txt')
    else:
        os.system(config['PROGRAM_GPG'] + ' --emit-version --no-comments --no-escape-from-lines --no-throw-keyids --pgp2 -a -b -u "'+ config['ID'] + '" -o ' + file_message + '.pgp ' + file_message + '.txt')
    
    result = file(file_message + '.sig', 'wb')
    for line in file(file_message + '.txt', 'rb'):
        if signatureWritten:
            result.write(line)
            continue

        if not line.startswith('X-Signed-Headers'):
            # From: is the last signed header field.
            if not line.startswith('From'):
                result.write(line)
            else:
                # Rewrite the From: line exactly as we already wrote it.
                result.write('From: ' + config['NAME'] + ' <' + config['MAIL'] + '>\n')
                result.write('Approved: ' + config['MAIL'] + '\n')
                if type == 'checkgroups' and not config['PRIVATE_HIERARCHY']:
                    result.write('Newsgroups: ' + group + ',news.admin.hierarchies\n')
                    result.write('Followup-To: ' + group + '\n')
                else:
                    result.write('Newsgroups: ' + group + '\n')
                result.write('Path: not-for-mail\n')
                result.write('X-Info: ' + config['URL'] + '\n')
                result.write('\tftp://ftp.isc.org/pub/pgpcontrol/README.html\n')
                result.write('MIME-Version: 1.0\n')
                if type == 'newgroup':
                    result.write('Content-Type: multipart/mixed; boundary="signcontrol"\n')
                elif type == 'checkgroups':
                    result.write('Content-Type: application/news-checkgroups; charset=' + config['ENCODING'] + '\n')
                else: # if type == 'rmgroup':
                    result.write('Content-Type: text/plain; charset=' + config['ENCODING'] + '\n')
                result.write('Content-Transfer-Encoding: 8bit\n')
                for line2 in file(file_message + '.pgp', 'r'):
                    if line2.startswith('-'):
                        continue
                    if line2.startswith('Version:'):
                        version = line2.replace('Version: ', '')
                        version = version.replace(' ', '_')
                        result.write('X-PGP-Sig: ' + version.rstrip() + ' Subject,Control,Message-ID,Date,Injection-Date,From\n')
                    elif len(line2) > 2:
                        result.write('\t' + line2.rstrip() + '\n')
                signatureWritten = True

    result.close()

    os.remove(file_message + '.pgp')
    os.remove(file_message + '.txt')
    print
    print 'Do not worry if the program complains about detached signatures or MD5.'
    print 'You can now post the file ' + file_message + '.sig using rnews or a similar tool.'
    print
    #print 'Or you can also try to send it with IHAVE.  If it fails, it means that the article'
    #print 'has not been sent.  You will then have to manually use rnews or a similar program.'
    #if raw_input('Do you want to try? (y/n) ') == 'y':
    #    import nntplib
    #    news_server = nntplib.NNTP(HOST, PORT, USER, PASSWORD)
    #    news_server.ihave(message_id, file_message + '.sig')
    #    news_server.quit()
    #    print 'The control article has just been sent!'


def generate_newgroup(groups, config, group=None, moderated=None, description=None, message=None, passphrase=None):
    """Create a new group."""
    while not group:
        group = raw_input('Name of the newsgroup to create: ').lower()
        components = group.split('.')
        if len(components) < 2:
            group = None
            print_error('The group must have at least two components.')
        elif not components[0][0:1].isalpha():
            group = None
            print_error('The first component must start with a letter.')
        elif components[0] in ['control', 'example', 'to']:
            group = None
            print_error('The first component must not be "control", "example" or "to".')
        elif re.search('[^a-z0-9+_.-]', group):
            group = None
            print_error('The group must not contain characters other than [a-z0-9+_.-].')
        for component in components:
            if component in ['all', 'ctl']:
                group = None
                print_error('Sequences "all" and "ctl" must not be used as components.')
            elif not component[0:1].isalnum():
                group = None
                print_error('Each component must start with a letter or a digit.')
            elif component.isdigit():
                group = None
                print_error('Each component must contain at least one non-digit character.')
    
    if groups.has_key(group):
        print
        print 'The newsgroup ' + group + ' already exists.'
        print 'These new settings (status and description) will override the current ones.'
        print
    
    if moderated == None:
        if raw_input('Is ' + group + ' a moderated newsgroup? (y/n) ' ) == 'y':
            moderated = True
            print
            print 'There is no need to add " (Moderated)" at the very end of the description.'
            print 'It will be automatically added, if not already present.'
            print
        else:
            moderated = False
    
    while not description:
        print
        print 'The description should start with a capital and end in a period.'
        description = raw_input("Description of " + group + ": ")
        if len(description) > 56:
            print_error('The description is too long.  You should shorten it.')
            if raw_input('Do you want to continue despite this recommendation? (y/n) ') != 'y':
                description = None
                continue

        moderated_count = description.count('(Moderated)')
        if moderated_count > 0:
            if not moderated:
                if description.endswith(' (Moderated)'):
                    description = None
                    print_error('The description must not end with " (Moderated)".')
                    continue
                else:
                    print_error('The description must not contain "(Moderated)".')
                    if raw_input('Do you want to continue despite this recommendation? (y/n) ') != 'y':
                        description = None
                        continue
            elif moderated_count > 1 or not description.endswith(' (Moderated)'):
                print_error('The description must not contain "(Moderated)".')
                if raw_input('Do you want to continue despite this recommendation? (y/n) ') != 'y':
                    description = None
                    continue

    if not message:
        print
        print 'The current message which will be sent is:'
        print

        if moderated:
            message = config['NEWGROUP_MESSAGE_MODERATED'].replace('$GROUP$', group)
        else:
            message = config['NEWGROUP_MESSAGE_UNMODERATED'].replace('$GROUP$', group)

        print message
        print
        if raw_input('Do you want to change it? (y/n) ') == 'y':
            print
            print 'Please enter the message you want to send.'
            print 'End it with a line containing only "." (a dot).'
            print

            message = ''
            buffer = raw_input('Message: ') + '\n'
            while buffer != '.\n':
                message += buffer.rstrip() + '\n'
                buffer = raw_input('Message: ') + '\n'
            print

    print
    print 'Here is the information about the newsgroup:'
    print 'Name: ' + group

    if moderated:
        print 'Status: moderated'
        if not description.endswith(' (Moderated)'):
            description += ' (Moderated)'
    else:
        print 'Status: unmoderated'
    print 'Description: ' + description
    print 'Message: '
    print
    print message
    print
    
    if raw_input('Do you want to generate a control article for ' + group + '? (y/n) ') == 'y':
        print
        file_newgroup = group + '-' + epoch_time(TIME)
        result = file(file_newgroup + '.txt', 'wb')
        result.write('X-Signed-Headers: Subject,Control,Message-ID,Date,Injection-Date,From\n')
        if moderated:
            result.write('Subject: cmsg newgroup ' + group + ' moderated\n')
            result.write('Control: newgroup ' + group + ' moderated\n')
        else:
            result.write('Subject: cmsg newgroup ' + group + '\n')
            result.write('Control: newgroup ' + group + '\n')
        message_id = '<newgroup-' + group + '-' + epoch_time(TIME) + '@' + config['HOST'] + '>'
        result.write('Message-ID: ' + message_id + '\n')
        result.write('Date: ' + pretty_time(TIME) + '\n')
        result.write('Injection-Date: ' + pretty_time(TIME) + '\n')
        result.write('From: ' + config['NAME'] + ' <' + config['MAIL'] + '>\n\n')
        result.write('This is a MIME NetNews control message.\n')
        result.write('--signcontrol\n')
        result.write('Content-Type: text/plain; charset=' + config['ENCODING'] + '\n\n')
        result.write(message + '\n')
        result.write('\n\n--signcontrol\n')
        result.write('Content-Type: application/news-groupinfo; charset=' + config['ENCODING'] + '\n\n')
        result.write('For your newsgroups file:\n')
        if len(group) < 8:
            result.write(group + '\t\t\t' + description + '\n')
        elif len(group) < 16:
            result.write(group + '\t\t' + description + '\n')
        else:
            result.write(group + '\t' + description + '\n')
        result.write('\n--signcontrol--\n')
        result.close()
        sign_message(config, file_newgroup, group, message_id, 'newgroup', passphrase)
    
    if raw_input('Do you want to update the current checkgroups file? (y/n) ') == 'y':
        groups[group] = description
        write_checkgroups(groups, config['CHECKGROUPS_FILE'])


def generate_rmgroup(groups, config, group=None, message=None, passphrase=None):
    """Remove a group."""
    while not group:
        group = raw_input('Name of the newsgroup to remove: ' ).lower()
    
    if not groups.has_key(group):
        print
        print 'The newsgroup ' + group + ' does not exist.'
        print 'Yet, you can send a rmgroup message for it if you want.'
        print
    
    if raw_input('Do you want to generate a control article to *remove* ' + group + '? (y/n) ') == 'y':
        print

        if not message:
            print 'The current message which will be sent is:'
            print

            message = config['RMGROUP_MESSAGE'].replace('$GROUP$', group)

            print message
            print
            if raw_input('Do you want to change it? (y/n) ') == 'y':
                print
                print 'Please enter the message you want to send.'
                print 'End it with a line containing only "." (a dot).'
                print

                message = ''
                buffer = raw_input('Message: ') + '\n'
                while buffer != '.\n':
                    message += buffer.rstrip() + '\n'
                    buffer = raw_input('Message: ') + '\n'
                print

        file_rmgroup = group + '-' + epoch_time(TIME)
        result = file(file_rmgroup + '.txt', 'wb')
        result.write('X-Signed-Headers: Subject,Control,Message-ID,Date,Injection-Date,From\n')
        result.write('Subject: cmsg rmgroup ' + group + '\n')
        result.write('Control: rmgroup ' + group + '\n')
        message_id = '<rmgroup-' + group + '-' + epoch_time(TIME) + '@' + config['HOST'] + '>'
        result.write('Message-ID: ' + message_id + '\n')
        result.write('Date: ' + pretty_time(TIME) + '\n')
        result.write('Injection-Date: ' + pretty_time(TIME) + '\n')
        result.write('From: ' + config['NAME'] + ' <' + config['MAIL'] + '>\n\n')
        result.write(message + '\n')
        result.close()
        sign_message(config, file_rmgroup, group, message_id, 'rmgroup', passphrase)
    
    if groups.has_key(group):
        if raw_input('Do you want to update the current checkgroups file? (y/n) ') == 'y':
            del groups[group]
            write_checkgroups(groups, config['CHECKGROUPS_FILE'])


def generate_checkgroups(config, passphrase=None, serial=None):
    """List the groups of the hierarchy."""
    while serial not in range(0,100):
        try:
            print 'If it is your first checkgroups for today, leave it blank (default is 1).'
            print 'Otherwise, increment this revision number by one.'
            serial = int(raw_input('Revision to use (1-99): '))
            print
        except:
            serial = 1

    serial = '%02d' % serial
    file_checkgroups = 'checkgroups-' + epoch_time(TIME)
    result = file(file_checkgroups + '.txt', 'wb')
    result.write('X-Signed-Headers: Subject,Control,Message-ID,Date,Injection-Date,From\n')
    result.write('Subject: cmsg checkgroups ' + config['CHECKGROUPS_SCOPE'] + ' #' + serial_time(TIME) + serial + '\n')
    result.write('Control: checkgroups ' + config['CHECKGROUPS_SCOPE'] + ' #' + serial_time(TIME) + serial + '\n')
    message_id = '<checkgroups-' + epoch_time(TIME) + '@' + config['HOST'] + '>'
    result.write('Message-ID: ' + message_id + '\n')
    result.write('Date: ' + pretty_time(TIME) + '\n')
    result.write('Injection-Date: ' + pretty_time(TIME) + '\n')
    result.write('From: ' + config['NAME'] + ' <' + config['MAIL'] + '>\n\n')
    for line in file(config['CHECKGROUPS_FILE'], 'r'):
        result.write(line.rstrip() + '\n')
    result.close()
    sign_message(config, file_checkgroups, config['ADMIN_GROUP'], message_id, 'checkgroups', passphrase)


def manage_keys(config):
    """Manage PGP keys."""
    choice = 0
    while choice != 8:
        choice = manage_menu()
        if choice == 1:
            print 'You currently have the following secret keys installed:'
            print
            os.system(config['PROGRAM_GPG'] + ' --list-secret-keys')
            print 'The uid of your secret key should be the same as the ID variable'
            print 'which is set in this script.'
        elif choice == 2:
            print
            print '-----------------------------------------------------------------------'
            print 'Please put the e-mail address from which you will send control articles'
            print 'in the key ID (the real name field).  And leave the other fields blank,'
            print 'for better compatibility with Usenet software.'
            print 'Choose a 2048-bit RSA key which never expires.'
            print 'You should also provide a passphrase, for security reasons.'
            print 'There is no need to edit the key after it has been generated.'
            print
            print 'Please note that the key generation may not finish if it is launched'
            print 'on a remote server.  Use your own computer instead and import the key'
            print 'on the remote one afterwards.'
            print '-----------------------------------------------------------------------'
            print
            os.system(config['PROGRAM_GPG'] + ' --gen-key --pgp2 --allow-freeform-uid')
            print
            print 'After having generated these keys, you should export your PUBLIC key'
            print 'and make it public (in the web site of your hierarchy, along with'
            print 'a current checkgroups, and also announce it in news.admin.hierarchies).'
            print 'You can also export your PRIVATE key for backup only.'
        elif choice == 3:
            print 'The key will be written to the file public-key.asc.'
            key_name = raw_input('Please enter the uid of the public key to export: ')
            os.system(config['PROGRAM_GPG'] + ' --armor --output public-key.asc --export ' + key_name)
        elif choice == 4:
            print 'The key will be written to the file private-key.asc.'
            key_name = raw_input('Please enter the uid of the secret key to export: ')
            os.system(config['PROGRAM_GPG'] + ' --armor --output private-key.asc --export-secret-keys ' + key_name)
            os.chmod('private-key.asc', 0400)
            print
            print 'Be careful:  it is a security risk to export your private key.'
            print 'Please make sure that nobody has access to it.'
        elif choice == 5:
            raw_input('Please put it in a file named secret-key.asc and press enter.')
            os.system(config['PROGRAM_GPG'] + ' --import secret-key.asc')
            print
            print 'Make sure that both the secret and public keys have just been imported.'
            print 'Their uid should be put as the ID variable set in this script.'
        elif choice == 6:
            key_name = raw_input('Please enter the uid of the key to *remove*: ')
            os.system(config['PROGRAM_GPG'] + ' --delete-secret-and-public-key ' + key_name)
        elif choice == 7:
            key_name = raw_input('Please enter the uid of the secret key to revoke: ')
            os.system(config['PROGRAM_GPG'] + ' --gen-revoke ' + key_name)
        print


if __name__ == "__main__":
    """The main function."""
    config = read_configuration(CONFIGURATION_FILE)
    if not os.path.isfile(config['PROGRAM_GPG']):
        print 'You must install GnuPG <http://www.gnupg.org/> and edit this script to put'
        print 'the path to the gpg binary.'
        raw_input('Please install it before using this script.')
        sys.exit(2)
    choice = 0
    while choice != 5:
        groups = read_checkgroups(config['CHECKGROUPS_FILE'])
        choice = choice_menu()
        if choice == 1:
            generate_newgroup(groups, config)
        elif choice == 2:
            generate_rmgroup(groups, config)
        elif choice == 3:
            generate_checkgroups(config)
        elif choice == 4:
            manage_keys(config)
