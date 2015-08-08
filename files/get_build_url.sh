#!/bin/bash

if [ $# -lt 2 ];
then
  #echo "  usage: '$0 <author> <project> <destination>'"
  echo "  usage: '$0 <author> <project>'"
  exit 1;
fi

author=$1
project=$2
#destination=$3

#echo "getting latest build number for ${author}/${project}"
ver=`curl -s -X GET https://circleci.com/api/v1/project/${author}/${project} | grep build_num | head -1 | awk -F: '{print\$2}' | sed -e 's/[ ,]//g'`
#echo "latest build number - ${ver}"
#echo "getting download url for build number - ${ver}"
url=`curl -s -X GET https://circleci.com/api/v1/project/${author}/${project}/${ver}/artifacts | grep bin | head -1 | grep url | awk -F: '{print\$2":"\$3}' | sed -e 's/[ ",]//g'`
#echo "downloading binary for build number - ${ver}"
echo "${url}"
#curl -s -L -X GET 'https://${url}' -o '${destination}'
