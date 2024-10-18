# usenet-signcontrol

> Copyright (c) 2007-2009, 2011, 2014, 2023, 2024 Julien ÉLIE

This software is distributed under the MIT license.  Please see the
[License](#license) section below for more information.

## Description

**signcontrol.py** is a Python script aimed at helping Usenet hierarchy
administrators in maintaining the canonical lists of newsgroups in the
hierarchies they administer.

This script is also useful to manage PGP keys: generation, import, export,
removal, and revokal.  It works on every platform on which Python and GnuPG
are available (Windows, Linux, etc.).

It also enforces best practices regarding the syntax of Usenet control
articles.

Getting started is as simple as:

1. Downloading and installing [Python](https://www.python.org/).
2. Downloading and installing [GnuPG](https://www.gnupg.org/).
3. Downloading both the `signcontrol.py` program and its `signcontrol.conf`
configuration file.
4. Editing the `signcontrol.conf` configuration file so that it properly fits
your installation.
5. Running `python signcontrol.py`.

If you intend to generate several control articles during a single run of this
script, you can make use of **gpg-agent** so as to type your passphrase only
once.  Running `gpg-agent --daemon signcontrol.py` should work.

If you're running **signcontrol.py** through a remote terminal, you may have
to execute `chown user $(tty)` as _root_ before running **signcontrol.py**
as _user_ to allow the input of a passphrase.  (**gpg** will otherwise fail
because the passphrase cannot be typed.)

Alternately, instead of the above `chown` command, you can enable loopback
pinentry mode with the following instructions added to `~/.gnupg/gpg.conf`
of the user running this script, creating the configuration file if it doesn't
already exist:

```

use-agent
pinentry-mode loopback

```

And also the following instructions added to `~/.gnupg/gpg-agent.conf`,
creating the file if it doesn't already exist:

```

allow-loopback-pinentry

```

Then restart the GnuPG agent with `echo RELOADAGENT | gpg-connect-agent`
and you will be able to interactively type your passphrase or provide it when
running from cron.

For optimal results, in case you'll use non-ASCII characters in control
messages and descriptions, please use UTF-8 for the encoding of your terminal
input and the checkgroups file.

If you run your own news server, you can send the generated control articles
through it (with INN, the command `inews -P -h < article.sig` can for
instance be used).  Otherwise, you'll have to find a news server and negotiate
with his newsmaster how you can inject your control articles.

## Support

To report an issue or ask a question, please use the [issue tracker on
GitHub](https://github.com/Julien-Elie/usenet-signcontrol/issues).

Instructions written in French are also available at
[https://www.trigofacile.com/divers/usenet/clefs/signcontrol.htm](https://www.trigofacile.com/divers/usenet/clefs/signcontrol.htm).

## Source Repository

**signcontrol.py** is maintained using Git.  You can
access the current source on the [web interface of
GitHub](https://github.com/Julien-Elie/usenet-signcontrol) or by cloning the
repository at:

https://github.com/Julien-Elie/usenet-signcontrol.git

When contributing modifications, either patches or Git pull requests are
welcome.

## Configuration File

The following parameters can be modified in the `signcontrol.conf`
configuration file:

- **PROGRAM\_GPG**

The path to the required GPG executable.  It is usually
`C:\Progra~1\GNU\GnuPG\gpg.exe` or `/usr/bin/gpg`.

- **PGP2\_COMPATIBILITY**

Whether compatibility with MIT PGP 2.6.2 (or equivalent) should be kept.
Though this is now fairly obsolete, a few news servers still haven't been
updated to be able to process newer and more secure signing algorithms.
Such servers do not recognize recent signing algorithms; however, current news
servers may refuse to process messages signed with the insecure MD5 algorithm.

Possible values are `True`, `False` or `Only` (default is `False`).

When set to `True`, **signcontrol.py** will generate two control articles: one
in a format compatible with MIT PGP 2.6.2 (or equivalent) and another with
a newer and more secure format.  Sending these two control articles will then
ensure a widest processing.

When set to `False`, **signcontrol.py** will only generate control articles in
a newer and more secure format.

When set to `Only`, **signcontrol.py** will only generate control articles in
a format compatible with MIT PGP 2.6.2 (or equivalent).

- **ID**

One of the user ID of the PGP key used to sign control articles.  The user ID
is the whole contents of a `uid` line, as shown in a list of all keys from
the secret keyring.

Note that if you do not already have a PGP key, **signcontrol.py** can generate
one for you.

- **MAIL**

The e-mail from which control articles are sent.

- **HOST**

The host which appears in the second part of the Message-ID of generated
control articles.  It is usually the name of a news server.

- **ADMIN\_GROUP**

An existing newsgroup of the hierarchy (where checkgroups control articles
will be fed).  If an administrative newsgroup exists, put it.  Otherwise, any
other newsgroup of the hierarchy will be fine.

- **NAME**

The name which appears in the From header field.  You should only use
ASCII characters.  Otherwise, you have to MIME-encode it (for instance:
`=?ISO-8859-15?Q?Julien_=C9LIE?=`).

- **CHECKGROUPS\_SCOPE**

The scope of the hierarchy according to [Section 5.2.3 of RFC 5537](https://datatracker.ietf.org/doc/html/rfc5537#section-5.2.3).
For instance: `fr` (for fr.\*), `de !de.alt` (for de.\* excepting de.alt.\*)
or `de.alt` (for de.alt.\*).

- **URL**

The URL where the public PGP key can be found.  If you do not have any,
leave `https://downloads.isc.org/pub/pgpcontrol/README.html`.  If you want to
mention several URLs (like the home page of the hierarchy), use a multi-line
text where each line, except for the first, begins with a tabulation.

- **NEWGROUP\_MESSAGE\_MODERATED**, **NEWGROUP\_MESSAGE\_UNMODERATED**,
**RMGROUP\_MESSAGE**

The message which will be written in the corresponding control article.
All occurrences of `$GROUP$` will be replaced by the name of the newsgroup.

- **PRIVATE\_HIERARCHY**

Whether the hierarchy is public or private.  If it is private (that is to say
if it is intended to remain in a local server with private access and if it
is not fed to other Usenet news servers), the value should be `True`, so that
checkgroups control articles are not crossposted to the news.admin.hierarchies
newsgroup.  Possible values are `True` or `False` (default is `False`).

- **CHECKGROUPS\_FILE**

The file which contains the current checkgroups.  Make sure it is correctly
encoded in UTF-8 (if of course it contains non-ASCII characters).

- **ENCODING**

The encoding of control articles.  The default value is `UTF-8`, which is the
charset that SHOULD be used for non-ASCII characters, per [Section 4.2
of RFC 5537](https://datatracker.ietf.org/doc/html/rfc5537#section-4.2).
Make sure your terminal is configured for UTF-8 input too!

## Using As a Library

You may also want to call the functions provided by **signcontrol.py** from
your own Python scripts.  Here is an example for adding or removing a bunch of
newsgroups, reading the list from a file (one newsgroup per line).  Naturally,
the example should be adapted to fit your needs.

```python

#!/usr/bin/python3

import signcontrol

conf = signcontrol.read_configuration(signcontrol.CONFIGURATION_FILE)
checkgroups = signcontrol.read_checkgroups(conf["CHECKGROUPS_FILE"])

# If the file only provides newsgroup names, moderation statuses
# and descriptions will be interactively asked for.
for group in open("list-of-groups-to-add"):
    signcontrol.generate_newgroup(checkgroups, conf, group.rstrip())

# If the file also contains the moderation status and the description
# of each newsgroup, these data will directly be used.
for group in open("list-of-groups-to-add"):
    (name, status, descr) = group.split(' ', 2)
    signcontrol.generate_newgroup(
        checkgroups, conf, name, status, descr.rstrip()
    )

# An example of mass removal.
for group in open("list-of-groups-to-remove"):
    signcontrol.generate_rmgroup(checkgroups, conf, group.rstrip())

```

An optional sixth argument to `generate_newgroup` and an optional fourth
argument to `generate_rmgroup` can be used to specify a different message
than the default one for the body of generated control articles.

## Useful Resources

Here are some resources that can be useful to be aware of:

- Discussions about Usenet hierarchy administration in general take place
in the `news.admin.hierarchies` newsgroup; do not hesitate to participate in
this newsgroup!



- Usenet Hierarchy Administration FAQ:
[https://www.eyrie.org/~eagle/faqs/usenet-hier.html](https://www.eyrie.org/~eagle/faqs/usenet-hier.html)



- Usenet hierarchy information:
[http://usenet.trigofacile.com/hierarchies/](http://usenet.trigofacile.com/hierarchies/)



- Hosting service for hierarchy administrators:
[http://www.news-admin.org/](http://www.news-admin.org/)

## License

For any copyright range specified by files in this package as "YYYY-ZZZZ", the
range specifies every single year in that closed interval.

The **usenet-signcontrol** package as a whole is covered by the following
copyright statement and license:

> Copyright (c) 2007-2009, 2011, 2014, 2023, 2024 Julien ÉLIE
>
> Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
