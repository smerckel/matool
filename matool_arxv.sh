#!/bin/bash

#
# Convenience script to download all files that are known to
# the matool server and specific to a glider into a single  
# tar gzipped file.
#
# Example:
# 
# $ matool_arxv.sh comet 10.200.66.34
#
# or, if the matool server runs on localhost, simply
#
# $ matool_arxv.sh comet
#
# lucas.merckelbach@hereon.de 16 Mar 2022.
#

if [ $# -eq 1 ]; then
    GLIDER=$1
    HOST=localhost
elif  [ $# -eq 2 ]; then
    GLIDER=$1
    HOST=$2
else
    echo
    echo "Usage: $0 glidername <matool_server_address>"
    echo
    exit 1
fi    
    
MATOOL="matool -s $HOST"

CWD=$PWD

# Gets all known files, but not the ones with * 
fns=`$MATOOL list $GLIDER | grep "at rev" | grep -v "\*"| tr -s " " | gawk -F " " '{print $2}'`

#Create a temp dir such as /tmp/xxxx/comet
tmpdir=`mktemp -d`
mkdir $tmpdir/$GLIDER

for fn in $fns; do
    $MATOOL show current $fn $GLIDER > $tmpdir/$GLIDER/$fn
done
TARFILE="${GLIDER}_mima.tgz"
cd $tmpdir
tar cvzf $TARFILE $GLIDER/*

mv $TARFILE $CWD
# clean up tempdirectory mess
rm -rf $tmpdir

echo "Created archived mima files as $TARFILE"
