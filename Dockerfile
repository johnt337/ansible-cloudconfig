FROM golang:1.4-wheezy

ADD https://get.docker.com/builds/Linux/x86_64/docker-1.6.2 /usr/bin/docker
# if you wish to use a local binary so you only download it once use something like:
# ADD linux/docker-1.6.2 /usr/bin/docker

# includes dev tools which can be removed at some point...
RUN \
  chmod +x /usr/bin/docker && \
  mkdir -m 700 /root/.ssh && \
  echo "Host github.com\n  StrictHostKeyChecking no" > /root/.ssh/config && \
  echo "[trusted]\ngroups = dialout" > /root/.hgrc && \
  go get github.com/johnt337/gopack && \
  cp /go/bin/gopack /usr/bin/gopack && \
  go get github.com/onsi/ginkgo && \
  go get github.com/onsi/ginkgo/ginkgo && \
  cp /go/bin/ginkgo /usr/bin/ginkgo && \
  go get github.com/onsi/gomega && \
  go get -u github.com/golang/lint/golint && \
  cp /go/bin/golint /usr/bin/golint && \
  go get golang.org/x/tools/cmd/cover && \
  mkdir /cloudconfig && \
  apt-get update && \
  apt-get install -y vim-tiny python-pip python-pip python-dev build-essential libyaml-dev && \
  /usr/bin/pip install --upgrade pip && \
  /usr/bin/pip install --upgrade virtualenv && \
  /usr/bin/pip install pyyaml
  
WORKDIR /workspace/ansible-cloudconfig
