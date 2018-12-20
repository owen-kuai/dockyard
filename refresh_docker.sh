#!/bin/bash
function check_os()
{
    uname | grep Linux || {
        $ECHO "$FAIL Only support Linux"
        return 0
    }
    cat /proc/version | grep 'Ubuntu' && {
        OS='ubuntu'
        INSTALL_PKG='apt install -y'
        DOCKER_SERVICE='/lib/systemd/system/docker.service'
    }
    cat /proc/version | grep -E 'Red|CentOS' && {
        OS='rhel'
        INSTALL_PKG='yum install -y'
        DOCKER_SERVICE='/usr/lib/systemd/system/docker.service'
    }
    [[ -z $OS ]] && {
        $ECHO "$FAIL Only support Ubuntu"
        return 0
    }
    $ECHO "$PASS\n"
    return 0
}

function enable_docker_insecure()
{
    typeset daemon='/etc/docker/daemon.json'
    typeset insecure="\"insecure-registries\":[\"0.0.0.0/0\"]"
    if [[ -f $daemon ]]; then
        grep 'insecure-registries' $daemon || {
            pre=$(cat $daemon | awk -F '{|}' '{print $2}')
            $ECHO "{${insecure},${pre}}" > /etc/docker/daemon.json
        }
    else
        $ECHO "{${insecure}}" > /etc/docker/daemon.json
    fi
    grep 'insecure-registries' $daemon || return 1
    systemctl daemon-reload
    systemctl restart docker.service
    return 0
}

function install_docker_into_ubuntu()
{
    apt-get update
    apt-get remove docker docker-engine docker-ce docker.io -y
    apt-get install -y apt-transport-https ca-certificates curl software-properties-common
    curl -fsSL https://download.daocloud.io/docker/linux/ubuntu/gpg | apt-key add -
    add-apt-repository \
        "deb [arch=$(dpkg --print-architecture)] https://download.daocloud.io/docker/linux/ubuntu $(lsb_release -cs) stable"
    apt-get update
    apt-get install -y -q docker-ce=17.09.1*
    service docker start
    return 0
}

function install_docker_into_rhel()
{
    yum remove -y docker \
                docker-common \
                docker-selinux \
                docker-engine-selinux \
                docker-engine \
                docker-ce \
    yum install -y yum-utils
    yum-config-manager --add-repo https://download.daocloud.io/docker/linux/centos/docker-ce.repo
    yum install -y -q --setopt=obsoletes=0 docker-ce-17.09.1.ce* docker-ce-selinux-17.09.1.ce*
    systemctl enable docker
    systemctl start docker
    return 0
}

function install_docker()
{
    if [[ $OS == 'ubuntu' ]]; then
        install_docker_into_ubuntu
        service docker restart
    elif [[ $OS == 'rhel' ]]; then
        install_docker_into_rhel
        systemctl restart docker
    else
        $ECHO "$FAIL Please install docker"
        return 1
    fi
    docker --version || {
        $ECHO "$FAIL Install docker failed"
        return 1
    }
    return 0
}

ECHO "\nCheck OS, Mem, CPU, Packages ... \n"
check_os || exit 1
install_docker || exit 1
enable_docker_insecure || exit 1
