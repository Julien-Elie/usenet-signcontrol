#!/bin/sh
#
# Generate a README.md file in a Markdown syntax suitable to be displayed
# in the Github web interface.  It extracts the POD documentation from
# signcontrol.py, and performs a few style changes.

(
    pod2markdown ../signcontrol.py \
        | sed -e 's/# NAME/# usenet-signcontrol/' \
            -e '2 i \
\
> Copyright (c) 2007-2009, 2011, 2014, 2023 Julien ÉLIE\
\
This software is distributed under the MIT license.  Please see the\
[License](#license) section below for more information.' \
            -e '3,8d' \
            -e 's/# DESCRIPTION/## Description/' \
            -e 's/# SUPPORT/## Support/' \
            -e 's/# SOURCE REPOSITORY/## Source Repository/' \
            -e 's/# CONFIGURATION FILE/## Configuration File/' \
            -e 's/# USING AS A LIBRARY/## Using As a Library/' \
            -e 's/# USEFUL RESOURCES/## Useful Resources/' \
            -e 's/# LICENSE/## License/' \
            -e 's/    //' \
            -e 's/^Copyright (c)/> Copyright (c)/' \
            -e 's/^Permission is/> Permission is/' \
            -e 's/^The above copyright/> The above copyright/' \
            -e 's/^THE SOFTWARE/> THE SOFTWARE/' \
            -e '/# HISTORY/,+7d' \
        | awk '/> (Permission|The|THE)/ { prev = ">" } \
            { if (NR > 1) print prev } { prev = $0 }'
) >../README.md
