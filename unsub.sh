#!/bin/bash

function getpage()
{
    echo "Getting page $1"
    gh api -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" "/user/subscriptions?per_page=100&page=$1" > /tmp/$$.gh
}

function ignoreit()
{
    echo "Ignoring $1"
    gh api --method PUT -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" \
       /repos/$1/subscription \
       -F subscribed=false \
       -F ignored=true > /tmp/$$.unsub
    subed=`jq -r ".subscribed" /tmp/$$.unsub`
    if [ "$subed" != "false" ]; then
	echo "Failed to unsub $1"
	cat /tmp/$$.unsub
    fi
}

#owner=CloudComputingTeamProject
#owner=cmu15213f21
#owner=15-411-f20
#owner=cmu15213f21
#owner=15-411-f21
#owner=cbogart
owner=CloudComputingCourse
page=0
while [ 1 == 1 ]; do
    getpage $page
    lines=`cat /tmp/$$.gh | wc -m`
    if [ $lines -lt 100 ]; then
	break
    fi
    # some results, fetch all cloud computing
    jq -r ".[].html_url" /tmp/$$.gh >> /tmp/$$.allsubs
    jq -r ".[].html_url" /tmp/$$.gh | grep $owner > /tmp/$$.cc
    lines=`cat /tmp/$$.cc | wc -l`
    if [ $lines -gt 0 ]; then
	for line in `sed -e 's%https://github.com/%%' /tmp/$$.cc`; do
	    ignoreit $line
	done
    fi    
    page=$((page + 1))
    sleep 1
done
/bin/rm -f /tmp/$$.cc /tmp/$$.gh /tmp/$$.unsub
subnum=`cat /tmp/$$.allsubs | sort -u | wc -l`
echo "Done: all subs ($subnum) in /tmp/$$.allsubs"
