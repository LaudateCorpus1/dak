#!/usr/bin/env python

# Dump variables from a .katie file to stdout
# Copyright (C) 2001, 2002, 2004  James Troup <james@nocrew.org>
# $Id: ashley,v 1.11 2004-11-27 16:05:12 troup Exp $

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

################################################################################

# <elmo> ooooooooooooooohhhhhhhhhhhhhhhhhhhhhhhhh            dddddddddeeeeeeeaaaaaaaarrrrrrrrrrr
# <elmo> iiiiiiiiiiiii          tttttttttthhhhhhhhiiiiiiiiiiiinnnnnnnnnkkkkkkkkkkkkk              iiiiiiiiiiiiii       mmmmmmmmmmeeeeeeeesssssssssssssssseeeeeeeddd           uuuupppppppppppp       ttttttttthhhhhhhheeeeeeee          xxxxxxxssssssseeeeeeeeettttttttttttt             aaaaaaaarrrrrrrggggggsssssssss
#
# ['xset r rate 30 250' bad, mmkay]

################################################################################

import sys
import katie, utils
import apt_pkg


################################################################################

def usage(exit_code=0):
    print """Usage: ashley FILE...
Dumps the info in .katie FILE(s).

  -h, --help                show this help and exit."""
    sys.exit(exit_code)

################################################################################

def main():
    Cnf = utils.get_conf()
    Arguments = [('h',"help","Ashley::Options::Help")]
    for i in [ "help" ]:
	if not Cnf.has_key("Ashley::Options::%s" % (i)):
	    Cnf["Ashley::Options::%s" % (i)] = ""

    apt_pkg.ParseCommandLine(Cnf, Arguments, sys.argv)

    Options = Cnf.SubTree("Ashley::Options")
    if Options["Help"]:
	usage()

    k = katie.Katie(Cnf)
    for arg in sys.argv[1:]:
        arg = utils.validate_changes_file_arg(arg,require_changes=-1)
        k.pkg.changes_file = arg
        print "%s:" % (arg)
	k.init_vars()
        k.update_vars()

        changes = k.pkg.changes
        print " Changes:"
        # Mandatory changes fields
        for i in [ "source", "version", "maintainer", "urgency", "changedby822",
                   "changedby2047", "changedbyname", "maintainer822",
                   "maintainer2047", "maintainername", "maintaineremail",
                   "fingerprint", "changes" ]:
            print "  %s: %s" % (i.capitalize(), changes[i])
            del changes[i]
        # Mandatory changes lists
        for i in [ "distribution", "architecture", "closes" ]:
            print "  %s: %s" % (i.capitalize(), " ".join(changes[i].keys()))
            del changes[i]
        # Optional changes fields
        for i in [ "changed-by", "filecontents", "format" ]:
            if changes.has_key(i):
                print "  %s: %s" % (i.capitalize(), changes[i])
                del changes[i]
        print
        if changes:
            utils.warn("changes still has following unrecognised keys: %s" % (changes.keys()))

        dsc = k.pkg.dsc
        print " Dsc:"
        for i in [ "source", "version", "maintainer", "fingerprint", "uploaders",
                   "bts changelog" ]:
            if dsc.has_key(i):
                print "  %s: %s" % (i.capitalize(), dsc[i])
                del dsc[i]
        print
        if dsc:
            utils.warn("dsc still has following unrecognised keys: %s" % (dsc.keys()))

        files = k.pkg.files
        print " Files:"
        for file in files.keys():
            print "  %s:" % (file)
            for i in [ "package", "version", "architecture", "type", "size",
                       "md5sum", "component", "location id", "source package",
                       "source version", "maintainer", "dbtype", "files id",
                       "new", "section", "priority", "pool name" ]:
                if files[file].has_key(i):
                    print "   %s: %s" % (i.capitalize(), files[file][i])
                    del files[file][i]
            if files[file]:
                utils.warn("files[%s] still has following unrecognised keys: %s" % (file, files[file].keys()))
        print

        dsc_files = k.pkg.dsc_files
        print " Dsc Files:"
        for file in dsc_files.keys():
            print "  %s:" % (file)
            # Mandatory fields
            for i in [ "size", "md5sum" ]:
                print "   %s: %s" % (i.capitalize(), dsc_files[file][i])
                del dsc_files[file][i]
            # Optional fields
            for i in [ "files id" ]:
                if dsc_files[file].has_key(i):
                    print "   %s: %s" % (i.capitalize(), dsc_files[file][i])
                    del dsc_files[file][i]
            if dsc_files[file]:
                utils.warn("dsc_files[%s] still has following unrecognised keys: %s" % (file, dsc_files[file].keys()))

################################################################################

if __name__ == '__main__':
    main()

