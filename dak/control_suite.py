#!/usr/bin/env python

# Manipulate suite tags
# Copyright (C) 2000, 2001, 2002, 2003, 2004, 2005  James Troup <james@nocrew.org>
# $Id: heidi,v 1.19 2005-11-15 09:50:32 ajt Exp $

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

#######################################################################################

# 8to6Guy: "Wow, Bob, You look rough!"
# BTAF: "Mbblpmn..."
# BTAF <.oO>: "You moron! This is what you get for staying up all night drinking vodka and salad dressing!"
# BTAF <.oO>: "This coffee I.V. drip is barely even keeping me awake! I need something with more kick! But what?"
# BTAF: "OMIGOD! I OVERDOSED ON HEROIN"
# CoWorker#n: "Give him air!!"
# CoWorker#n+1: "We need a syringe full of adrenaline!"
# CoWorker#n+2: "Stab him in the heart!"
# BTAF: "*YES!*"
# CoWorker#n+3: "Bob's been overdosing quite a bit lately..."
# CoWorker#n+4: "Third time this week."

# -- http://www.angryflower.com/8to6.gif

#######################################################################################

# Adds or removes packages from a suite.  Takes the list of files
# either from stdin or as a command line argument.  Special action
# "set", will reset the suite (!) and add all packages from scratch.

#######################################################################################

import pg, sys
import apt_pkg
import utils, db_access, logging

#######################################################################################

Cnf = None
projectB = None
Logger = None

################################################################################

def usage (exit_code=0):
    print """Usage: heidi [OPTIONS] [FILE]
Display or alter the contents of a suite using FILE(s), or stdin.

  -a, --add=SUITE            add to SUITE
  -h, --help                 show this help and exit
  -l, --list=SUITE           list the contents of SUITE
  -r, --remove=SUITE         remove from SUITE
  -s, --set=SUITE            set SUITE"""

    sys.exit(exit_code)

#######################################################################################

def get_id (package, version, architecture):
    if architecture == "source":
        q = projectB.query("SELECT id FROM source WHERE source = '%s' AND version = '%s'" % (package, version))
    else:
        q = projectB.query("SELECT b.id FROM binaries b, architecture a WHERE b.package = '%s' AND b.version = '%s' AND (a.arch_string = '%s' OR a.arch_string = 'all') AND b.architecture = a.id" % (package, version, architecture))

    ql = q.getresult()
    if not ql:
        utils.warn("Couldn't find '%s~%s~%s'." % (package, version, architecture))
        return None
    if len(ql) > 1:
        utils.warn("Found more than one match for '%s~%s~%s'." % (package, version, architecture))
        return None
    id = ql[0][0]
    return id

#######################################################################################

def set_suite (file, suite_id):
    lines = file.readlines()

    projectB.query("BEGIN WORK")

    # Build up a dictionary of what is currently in the suite
    current = {}
    q = projectB.query("SELECT b.package, b.version, a.arch_string, ba.id FROM binaries b, bin_associations ba, architecture a WHERE ba.suite = %s AND ba.bin = b.id AND b.architecture = a.id" % (suite_id))
    ql = q.getresult()
    for i in ql:
        key = " ".join(i[:3])
        current[key] = i[3]
    q = projectB.query("SELECT s.source, s.version, sa.id FROM source s, src_associations sa WHERE sa.suite = %s AND sa.source = s.id" % (suite_id))
    ql = q.getresult()
    for i in ql:
        key = " ".join(i[:2]) + " source"
        current[key] = i[2]

    # Build up a dictionary of what should be in the suite
    desired = {}
    for line in lines:
        split_line = line.strip().split()
        if len(split_line) != 3:
            utils.warn("'%s' does not break into 'package version architecture'." % (line[:-1]))
            continue
        key = " ".join(split_line)
        desired[key] = ""

    # Check to see which packages need removed and remove them
    for key in current.keys():
        if not desired.has_key(key):
            (package, version, architecture) = key.split()
            id = current[key]
            if architecture == "source":
                q = projectB.query("DELETE FROM src_associations WHERE id = %s" % (id))
            else:
                q = projectB.query("DELETE FROM bin_associations WHERE id = %s" % (id))
            Logger.log(["removed",key,id])

    # Check to see which packages need added and add them
    for key in desired.keys():
        if not current.has_key(key):
            (package, version, architecture) = key.split()
            id = get_id (package, version, architecture)
            if not id:
                continue
            if architecture == "source":
                q = projectB.query("INSERT INTO src_associations (suite, source) VALUES (%s, %s)" % (suite_id, id))
            else:
                q = projectB.query("INSERT INTO bin_associations (suite, bin) VALUES (%s, %s)" % (suite_id, id))
            Logger.log(["added",key,id])

    projectB.query("COMMIT WORK")

#######################################################################################

def process_file (file, suite, action):

    suite_id = db_access.get_suite_id(suite)

    if action == "set":
        set_suite (file, suite_id)
        return

    lines = file.readlines()

    projectB.query("BEGIN WORK")

    for line in lines:
        split_line = line.strip().split()
        if len(split_line) != 3:
            utils.warn("'%s' does not break into 'package version architecture'." % (line[:-1]))
            continue

        (package, version, architecture) = split_line

        id = get_id(package, version, architecture)
        if not id:
            continue

        if architecture == "source":
            # Find the existing assoications ID, if any
            q = projectB.query("SELECT id FROM src_associations WHERE suite = %s and source = %s" % (suite_id, id))
            ql = q.getresult()
            if not ql:
                assoication_id = None
            else:
                assoication_id = ql[0][0]
            # Take action
            if action == "add":
                if assoication_id:
                    utils.warn("'%s~%s~%s' already exists in suite %s." % (package, version, architecture, suite))
                    continue
                else:
                    q = projectB.query("INSERT INTO src_associations (suite, source) VALUES (%s, %s)" % (suite_id, id))
            elif action == "remove":
                if assoication_id == None:
                    utils.warn("'%s~%s~%s' doesn't exist in suite %s." % (package, version, architecture, suite))
                    continue
                else:
                    q = projectB.query("DELETE FROM src_associations WHERE id = %s" % (assoication_id))
        else:
            # Find the existing assoications ID, if any
            q = projectB.query("SELECT id FROM bin_associations WHERE suite = %s and bin = %s" % (suite_id, id))
            ql = q.getresult()
            if not ql:
                assoication_id = None
            else:
                assoication_id = ql[0][0]
            # Take action
            if action == "add":
                if assoication_id:
                    utils.warn("'%s~%s~%s' already exists in suite %s." % (package, version, architecture, suite))
                    continue
                else:
                    q = projectB.query("INSERT INTO bin_associations (suite, bin) VALUES (%s, %s)" % (suite_id, id))
            elif action == "remove":
                if assoication_id == None:
                    utils.warn("'%s~%s~%s' doesn't exist in suite %s." % (package, version, architecture, suite))
                    continue
                else:
                    q = projectB.query("DELETE FROM bin_associations WHERE id = %s" % (assoication_id))

    projectB.query("COMMIT WORK")

#######################################################################################

def get_list (suite):
    suite_id = db_access.get_suite_id(suite)
    # List binaries
    q = projectB.query("SELECT b.package, b.version, a.arch_string FROM binaries b, bin_associations ba, architecture a WHERE ba.suite = %s AND ba.bin = b.id AND b.architecture = a.id" % (suite_id))
    ql = q.getresult()
    for i in ql:
        print " ".join(i)

    # List source
    q = projectB.query("SELECT s.source, s.version FROM source s, src_associations sa WHERE sa.suite = %s AND sa.source = s.id" % (suite_id))
    ql = q.getresult()
    for i in ql:
        print " ".join(i) + " source"

#######################################################################################

def main ():
    global Cnf, projectB, Logger

    Cnf = utils.get_conf()

    Arguments = [('a',"add","Heidi::Options::Add", "HasArg"),
                 ('h',"help","Heidi::Options::Help"),
                 ('l',"list","Heidi::Options::List","HasArg"),
                 ('r',"remove", "Heidi::Options::Remove", "HasArg"),
                 ('s',"set", "Heidi::Options::Set", "HasArg")]

    for i in ["add", "help", "list", "remove", "set", "version" ]:
	if not Cnf.has_key("Heidi::Options::%s" % (i)):
	    Cnf["Heidi::Options::%s" % (i)] = ""

    file_list = apt_pkg.ParseCommandLine(Cnf,Arguments,sys.argv)
    Options = Cnf.SubTree("Heidi::Options")

    if Options["Help"]:
	usage()

    projectB = pg.connect(Cnf["DB::Name"], Cnf["DB::Host"],int(Cnf["DB::Port"]))

    db_access.init(Cnf, projectB)

    action = None

    for i in ("add", "list", "remove", "set"):
        if Cnf["Heidi::Options::%s" % (i)] != "":
            suite = Cnf["Heidi::Options::%s" % (i)]
            if db_access.get_suite_id(suite) == -1:
                utils.fubar("Unknown suite '%s'." %(suite))
            else:
                if action:
                    utils.fubar("Can only perform one action at a time.")
                action = i

    # Need an action...
    if action == None:
        utils.fubar("No action specified.")

    # Safety/Sanity check
    if action == "set" and suite != "testing":
        utils.fubar("Will not reset a suite other than testing.")

    if action == "list":
        get_list(suite)
    else:
        Logger = logging.Logger(Cnf, "heidi")
        if file_list:
            for file in file_list:
                process_file(utils.open_file(file), suite, action)
        else:
            process_file(sys.stdin, suite, action)
        Logger.close()

#######################################################################################

if __name__ == '__main__':
    main()

