import os

SCRIPT_DIR = os.getenv('SCRIPT_DIR', '.')

NGINX_IMAGE = 'nginx:stable-alpine'  # nginx镜像版本
DCS_CAPTAIN_IMAGE = 'daocloud.io/dc_pokeman/captain:2.5.4'  # 后端镜像版本
DCS_ADMIN_DASHBOARD_IMAGE = 'daocloud.io/dc_pokeman/daocloud-admin-dashboard:2.5.4'  # captain前端镜像版本

DCE_IMAGE_3_0 = "daocloud.io/dc_pokeman/dce_3_0_deploy:dce-3-0"  # 当部署到DCE上面时需要的镜像
DCE_IMAGE_2_10 = "daocloud.io/dc_pokeman/dce_deploy:dce-2-10"

DCS_REPO = os.path.join(SCRIPT_DIR, './dcs_repo')  # dcs_repo 路径
DOCKER_SOCK_PATH = '/var/run/docker.sock'  # docker.sock 路径
DOCKER_COMPOSE_SOURCE_TMPL = 'https://get.daocloud.io/docker/compose/releases/download/1.22.0/docker-compose-{}-{}'
DCE_REPO_SOURCE = 'https://qiniu-download-public.daocloud.io/DaoCloud_Services/dcs2.5-repo.tar.gz?attname='  # 下载docker离线安装包url
DCS_IMAGE_DIR = os.path.join(DCS_REPO, 'images')
DCS_CAPTAIN_IMAGE_DIR = os.path.join(DCS_IMAGE_DIR, 'captain-images')  # captain镜像文件夹
DCS_BUILDER_IMAGE_DIR = os.path.join(DCS_IMAGE_DIR, 'builder-images')  # 组件镜像文件夹
DCS_MIDDLEWARE_IMAGE_DIR = os.path.join(DCS_IMAGE_DIR, 'middleware-images')  # 中间件镜像文件夹

DOCKER_COMPOSE_BIN = os.path.join(DCS_REPO, 'docker-compose')
CAPTAIN_COMPOSE_CONF_PATH = os.path.join(DCS_REPO, 'captain.yaml')  # captain 启动模版
NGINX_COMPOSE_CONF_PATH = os.path.join(DCS_REPO, 'nginx.yaml')  # nginx 启动模版
MIDDLEWARE_COMPOSE_CONF_PATH = os.path.join(DCS_REPO, 'middleware.yaml')  # 中间件启动模版
NGINX_CONF_PATH = os.path.join(DCS_REPO, 'nginx.conf')  # nginx配置文件
DCE_REPO_TAR_PATH = os.path.join(DCS_REPO, 'repo.tar.gz')  # docker离线安装包压缩文件
REPO_PATH = os.path.join(DCS_REPO, 'repo')  # docker离线安装包文件夹
INSTALL_DOCKER_SCRIPT_PATH = os.path.join(DCS_REPO, 'refresh_docker.sh')  # docker在线安装脚本
INSTALL_DOCKER_OFFLINE_SCRIPT = os.path.join(DCS_REPO, 'docker_offline.sh')  # docker离线安装脚本

CAPTAIL_IMAGES = [
    'postgres:10',
    'redis:3.2.11-alpine',
    'rabbitmq:3-management-alpine',
    'nginx:stable-alpine',
]

NGINX_CONF_TMPL = '''

user  root;
worker_processes  1;

error_log  /var/log/nginx/error.log warn;
pid        /var/run/nginx.pid;


events {
    worker_connections  1024;
}


http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile        on;
    #tcp_nopush     on;

    keepalive_timeout  65;

    #gzip  on;

    server {

        listen       80;
        server_name  localhost;

        client_max_body_size 1000m;

        location / {
            root   /usr/share/nginx/html;
            # index  index.html index.htm;
            proxy_set_header Connection $http_connection;
            proxy_set_header Upgrade $http_upgrade;
            proxy_pass http://unix:%(docker_sock_path)s;
        }

    }

}


'''

NGINX_COMPOSE_CONF_TMPL = '''version: '3'
services:
  nginx:
    restart: always
    image: nginx:stable-alpine
    volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
    - {}:{}
    ports:
    - 12375:80
'''

CAPTAIN_COMPOSE_CONF_TMPL = '''version: '3'
services:
  captain:
    restart: always
    image: {}
    volumes:
    - /var/lib/dcs:/var/lib/dcs
    ports:
    - 2333:2333
    environment:
    - SQLITE_PATH=/var/lib/dcs
    - INSTALL_TYPE=COMPOSE
  dashboard:
    restart: always
    image: {}
    environment:
    - BASE_URL=http://{}:2333
    - INSTALL_TYPE=COMPOSE
    ports:
    - 30080:80

'''

MIDDLEWARE_COMPOSE_CONF_TMPL = '''version: '2'
services:
  postgres:
    image: postgres:10
    restart: always
    network_mode: host
    command: ["-c", "max_connections=2000"]
    volumes:
    - "/var/lib/dcs/postgres-data:/var/lib/postgresql/data"
    environment:
    - POSTGRES_PASSWORD=dangerous
  rabbitmq:
    image: rabbitmq:3-management-alpine
    restart: always
    network_mode: host
    volumes:
    - "/var/lib/dcs/rabbitmq-data:/var/lib/rabbitmq"
  redis:
    image: redis:3.2.11-alpine
    restart: always
    network_mode: host

'''

banner = """

                                 ,                              
                             `:;;;                              
                           ,;;;;;;                              
                        `;;;;;;;;;   `                          
                      .;;;;;;;;;;;   ;;        `;:,,            
                    .;;;;;;;;;;;;;   ;;;:                       
                   ;;;;;;;;;;;;;;;   ;;;;;                      
                 ,;;;;;;;;;;;;;;;;   ;;;;;;,                    
                ;;;;;;;;;;;;;;;;;;   ;;;;;;;;                   
               ;;;;;;;;;;;;;;;;;;;   ;;;;;;;;;                  
              ;;;;;;;;;;;;;;;;;;;;   ;;;;;;;;;;                 
             ;;;;;;;;;;;;;;;;;;;;;   ;;;;;;;;;;;                
             ;;;;;;;;;;;;;;;;;;;;;   ;;;;;;;;;;;;               
            ``````````````````````   `````````````              
                              ``..,::;;;;;;;;;;;:,,..`          
           ``````....``````         ```....``                   
                       ```````                                  

               DaoCloud Services Captain Module

              START SAILING, FOREVER AND ALWAYS

"""

reinstall_docker_script = """
#!/bin/bash
function check_os()
{
    uname | grep Linux || {
        echo "FAIL Only support Linux"
        return 0
    }
    cat /proc/version | grep 'Ubuntu' && {
        OS='ubuntu'
    }
    cat /proc/version | grep -E 'Red|CentOS' && {
        OS='rhel'
    }
    [[ -z $OS ]] && {
        echo "FAIL!  Only support Ubuntu"
        return 0
    }
    return 0
}

function enable_docker_insecure()
{
    typeset daemon='/etc/docker/daemon.json'
    typeset insecure="\\\"insecure-registries\\\":[\\\"0.0.0.0/0\\\"]"
    if [[ -f $daemon ]]; then
        grep 'insecure-registries' $daemon || {
            pre=$(cat $daemon | awk -F '{|}' '{print $2}')
            echo -e "{${insecure},${pre}}" > /etc/docker/daemon.json
        }
    else
        echo -e "{${insecure}}" > /etc/docker/daemon.json
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
    add-apt-repository "deb [arch=$(dpkg --print-architecture)] https://download.daocloud.io/docker/linux/ubuntu $(lsb_release -cs) stable"
    apt-get update
    apt-get install -y -q docker-ce=17.09.1*
    service docker start
    return 0
}

function install_docker_into_rhel()
{
    yum remove  docker \
                docker-common \
                docker-selinux \
                docker-engine-selinux \
                docker-engine \
                docker-ce -y
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
        echo "FAILED!  Please install docker"
        return 1
    fi
    docker --version || {
        echo "FAILED!  Install docker failed"
        return 1
    }
    return 0
}

echo "\nCheck OS, Mem, CPU, Packages ... \n"
check_os || exit 1
install_docker || exit 1
enable_docker_insecure || exit 1
"""

install_docker_offline = """
#!/bin/bash
function check_os()
{
    uname | grep Linux || {
        echo "FAIL Only support Linux"
        return 0
    }
    cat /proc/version | grep 'Ubuntu' && {
        OS='ubuntu'
    }
    cat /proc/version | grep -E 'Red|CentOS' && {
        OS='rhel'
    }
    [[ -z $OS ]] && {
        echo "FAIL!  Only support Ubuntu"
        return 0
    }
    echo "$PASS\n"
    return 0
}

function remove_docker_from_ubuntu()
{   
    echo " \n * remove Docker from ubuntu... \n"
    apt-get remove docker docker-engine docker-ce docker.io -y
    return 0
}

function remove_docker_from_rhel()
{
    echo " \n * remove Docker from centos... \n"
    yum remove  docker \
                docker-common \
                docker-selinux \
                docker-engine-selinux \
                docker-engine \
                docker-ce -y
    return 0
}

function remove_docker()
{
    if [[ $OS == 'ubuntu' ]]; then
        remove_docker_form_ubuntu
    elif [[ $OS == 'rhel' ]]; then
        remove_docker_from_rhel
    fi
    return 0
}

function install_docker_into_rhel(){
    echo " \n * install Docker into centos... \n"
    tar -zxvf docker-17.09.1-centos-7.3.1611.tar.gz
    cd docker-17.09.1-centos-7.3.1611
    echo "installing docker"
    cd docker
    rpm -ivh *.rpm --nodeps --force
    service docker start
}

function install_docker_into_ubuntu(){
    echo " \n * install Docker into ubuntu-16.04... \n"
    tar -zxvf docker-17.09.1-ubuntu-16.04.tar.gz
    cd docker-17.09.1-ubuntu-16.04
    echo " * Installing Docker..."
    mkdir -p /var/lib/apt/docker
    cp -r docker/* /var/lib/apt/docker
    chown -R _apt /var/lib/apt/docker
    mkdir -p /etc/apt/sources.list.d
    echo deb file:///var/lib/apt docker/ > /etc/apt/sources.list.d/docker-offline.list
    mv /etc/apt/sources.list /etc/apt/sources.list.back
    touch /etc/apt/sources.list
    apt-get update
    apt-get install -y --allow-unauthenticated docker-ce=17.09.1*
    mv /etc/apt/sources.list.back /etc/apt/sources.list
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
        echo "FAILED!  Please install docker"
        return 1
    fi
    docker --version || {
        echo "FAILED!  Install docker failed"
        return 1
    }
    return 0
}

function enable_docker_insecure()
{
    typeset daemon='/etc/docker/daemon.json'
    typeset insecure="\\\"insecure-registries\\\":[\\\"0.0.0.0/0\\\"]"
    if [[ -f $daemon ]]; then
        grep 'insecure-registries' $daemon || {
            pre=$(cat $daemon | awk -F '{|}' '{print $2}')
            echo -e "{${insecure},${pre}}" > /etc/docker/daemon.json
        }
    else
        echo -e "{${insecure}}" > /etc/docker/daemon.json
    fi
    grep 'insecure-registries' $daemon || return 1
    systemctl daemon-reload
    systemctl restart docker.service
    return 0
}

echo "\nCheck OS, Remove docker-17.03 , Install docker-17.09 ... \n"
cd repo/
check_os || exit 1
remove_docker || exit 1
install_docker || exit 1
enable_docker_insecure || exit 1
"""
