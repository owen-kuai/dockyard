import re
import subprocess
import os
import platform
import json
import time
from distutils.spawn import find_executable

import requests
import shutil
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

os.environ['SCRIPT_DIR'] = SCRIPT_DIR

from const_var import *


class Colored(object):
    # 显示格式: \033[显示方式;前景色;背景色m
    # 只写一个字段表示前景色,背景色默认
    RED = '\033[31m'  # 红色
    GREEN = '\033[32m'  # 绿色
    YELLOW = '\033[33m'  # 黄色
    BLUE = '\033[34m'  # 蓝色
    FUCHSIA = '\033[35m'  # 紫红色
    CYAN = '\033[36m'  # 青蓝色
    WHITE = '\033[37m'  # 白色

    #: no color
    RESET = '\033[0m'  # 终端默认颜色

    def color_str(self, color, s):
        return '{}{}{}'.format(
            getattr(self, color),
            s,
            self.RESET
        )

    def red(self, s):
        return self.color_str('RED', s)

    def green(self, s):
        return self.color_str('GREEN', s)

    def yellow(self, s):
        return self.color_str('YELLOW', s)

    def blue(self, s):
        return self.color_str('BLUE', s)

    def fuchsia(self, s):
        return self.color_str('FUCHSIA', s)

    def cyan(self, s):
        return self.color_str('CYAN', s)

    def white(self, s):
        return self.color_str('WHITE', s)


def yellow_print(message):
    color = Colored()
    message = color.yellow(message)
    print(message)


def red_print(message):
    color = Colored()
    message = color.red(message)
    print(message)


def cyan_print(message):
    color = Colored()
    message = color.cyan(message)
    print(message)


def i18n(en, zh=None):
    if not zh:
        return en
    lang = 'en'
    env = os.getenv('LANG') or os.getenv('LC_CTYPE') or os.getenv('LC_ALL') or ''
    if 'zh_cn' in env.lower():
        lang = 'zh'
    if lang == 'zh':
        return zh
    else:
        return en


_quiet = [False]
_all_yes = [False]


def set_quiet(q):
    _quiet[0] = q


def set_all_yes(a):
    _all_yes[0] = a


def raw_input(message):
    sys.stdout.write(message)
    sys.stdout.flush()
    return sys.stdin.readline().strip()


def expect(message, default=False):
    default_text = 'Y' if default else 'N'
    # yn = '[Y/n]' if default else '[y/N]'
    yn = '[Y/N]'
    # print(_all_yes[0])
    if _all_yes[0]:
        return True
    if _quiet[0]:
        print(message + ' %s (%s: %s):' % (yn, i18n('default', u"默认"), default_text), 'Y' if default else 'N')
        return default
    ch = raw_input(message + ' %s (%s: %s):' % (yn, i18n('default', u"默认"), default_text))
    if not ch:
        return default
    if ch.lower() in ('y', 'yes'):
        return True
    elif ch.lower() in ('n', 'no'):
        return False
    else:
        return default


def pause(prompt=None):
    prompt = prompt or i18n('Press any key to continue...', u'按任意键继续...')
    print(prompt, end='')
    if _quiet[0]:
        return
    sys.stdin.read(1)


def get_base_image_name(image_name):
    if ':' in image_name:
        image_name = image_name.rsplit(':', 1)[0]
    return os.path.basename(image_name)


def net_check():
    try:
        req = requests.get("http://www.baidu.com", timeout=2)
    except Exception as e:
        print("Unable to connect to the internet")
        return False
    return True


def disable_selinux_cmds():
    cmds = []
    if find_executable("setenforce"):
        cmds.append('setenforce 0')
    if os.path.exists('/etc/selinux/config'):
        cmds.append(
            "sed -i '/^SELINUX=/c\SELINUX=disabled' /etc/selinux/config")
    return cmds


def disable_firewall_cmds():
    cmds = []
    if find_executable("ufw"):
        cmds.append('ufw disable')
    else:
        service_name = 'firewalld'
        systemctl_path = find_executable("systemctl")
        if not systemctl_path:
            return cmds

        if 0 == subprocess.call([systemctl_path, 'cat', service_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                shell=True):
            cmds.extend(['systemctl disable %s' % service_name,
                         'systemctl stop %s' % service_name])
    return cmds


def prepare_enviremont():
    cmds = []
    cmds.extend(disable_selinux_cmds())
    cmds.extend(disable_firewall_cmds())

    for cmd in cmds:
        yellow_print('>>>{}'.format(cmd))
        subprocess.call(cmd, shell=True)


def check_docker_version():
    yellow_print('docker  --version')
    docker_version = subprocess.check_output(['docker', '--version']).decode('utf-8')
    result = re.search(r'version (\d+\.\d+)', docker_version)
    version = result.group(1)
    if float(version) < float('17.05'):
        return False
    return True


def ensure_repo():
    if not os.path.exists(REPO_PATH):
        red_print(i18n("Missing folder repo", '缺少安装环境所需的配置文件夹repo'))
        raise Exception('缺少安装环境所需的配置文件夹repo')


def download_repo(url, localFile):
    cyan_print('%s\n --->>>\n  %s' % (url, localFile))
    startTime = time.time()
    with requests.get(url, stream=True) as r:
        contentLength = int(r.headers['content-length'])
        line = 'content-length: %dB/ %.2fKB/ %.2fMB'
        line = line % (contentLength, contentLength / 1024, contentLength / 1024 / 1024)
        cyan_print(line)
        downSize = 0
        with open(localFile, 'wb') as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)
                downSize += len(chunk)
                line = '%d KB/s - %.2f MB, total %.2f MB'
                line = line % (
                    downSize / 1024 / (time.time() - startTime), downSize / 1024 / 1024, contentLength / 1024 / 1024)
                cyan_print(line)
                if downSize >= contentLength:
                    break
        timeCost = time.time() - startTime
        line = 'time: %.2f s, average speed: %.2f KB/s'
        line = line % (timeCost, downSize / 1024 / timeCost)
        print(line)


def download_all_images():
    # 获取DCS各个版本镜像名称
    yellow_print(
        'docker run --rm  --entrypoint cat {} /captain/templates/module_version.json'.format(DCS_CAPTAIN_IMAGE))
    data = subprocess.check_output(
        ['docker', 'run', '--rm', '--entrypoint', 'cat', DCS_CAPTAIN_IMAGE, '/captain/templates/module_version.json'])
    module_images = json.loads(data.decode('utf-8'))

    module_dict = {}
    for name, image in module_images.items():
        module_dict['builder_' + name] = image

    for image_name in CAPTAIL_IMAGES:
        module_dict['middleware_' + get_base_image_name(image_name)] = image_name
    module_dict['admin_captain'] = DCS_CAPTAIN_IMAGE
    module_dict['admin_dashboard'] = DCS_ADMIN_DASHBOARD_IMAGE
    module_dict['builder_nginx'] = NGINX_IMAGE
    module_dict['builder_dce_2_10'] = DCE_IMAGE_2_10
    module_dict['builder_dce_3_0'] = DCE_IMAGE_3_0

    image_hash_map = {}

    # 开始下载镜像
    for module_name, image_name in module_dict.items():
        image_id = None
        for i in range(3):
            try:
                yellow_print('docker pull {}'.format(image_name))
                subprocess.check_call(['docker', 'pull', image_name])
                yellow_print('docker inspect {}'.format(image_name))
                image_data = subprocess.check_output(['docker', 'inspect', image_name])
                image_configs = json.loads(image_data.decode('utf-8'))
                image_id = image_configs[0]['Id']
            except Exception as e:
                time.sleep(2)
                continue
            else:
                break
        else:
            red_print('docker pull {} failed !'.format(image_name))
            raise Exception('docker pull {} failed !'.format(image_name))

        if not image_id:
            red_print('pull image {} faild'.format(module_name))
            raise Exception('pull image {} faild'.format(module_name))
        if ':' in image_id:
            _, image_hash = image_id.split(':', 1)
        else:
            image_hash = image_id
        prefix, _ = module_name.split('_', 1)
        image_hash_map[prefix + '_' + image_hash] = image_name

    os.makedirs(DCS_IMAGE_DIR, exist_ok=True)
    os.makedirs(DCS_CAPTAIN_IMAGE_DIR, exist_ok=True)
    os.makedirs(DCS_MIDDLEWARE_IMAGE_DIR, exist_ok=True)
    os.makedirs(DCS_BUILDER_IMAGE_DIR, exist_ok=True)

    # 打包镜像到tar包
    for image_hash, image_name in image_hash_map.items():
        if image_hash.startswith('admin'):
            image_dir = DCS_CAPTAIN_IMAGE_DIR
        elif image_hash.startswith('middleware'):
            image_dir = DCS_MIDDLEWARE_IMAGE_DIR
        else:
            image_dir = DCS_BUILDER_IMAGE_DIR
        image_filename = os.path.join(image_dir, '{}_{}.tar'.format(get_base_image_name(image_name), image_hash))
        yellow_print('saving image [{}] to file [{}]...'.format(image_name, image_filename))
        subprocess.check_call(['docker', 'save', '-o', image_filename, image_name])


def install_captain(DCS_CAPTAIN_IMAGE, DCS_ADMIN_DASHBOARD_IMAGE):
    # 获取本机ip
    external_host = raw_input(i18n('enter external IP or hostname : ', '请输入本服务器外网可访问的IP或主机名 : '))

    if not external_host:
        red_print(i18n('empty external IP or hostname', '无效的IP地址'))
        raise Exception('empty external IP or hostname')

    # 检测IP
    subprocess.check_call(['ping', '-c2', external_host])

    # 渲染captain启动yaml模版
    docker_compose_conf = CAPTAIN_COMPOSE_CONF_TMPL.format(
        DCS_CAPTAIN_IMAGE,
        DCS_ADMIN_DASHBOARD_IMAGE,
        external_host,
    )
    # 保存captain启动yaml模版
    open(CAPTAIN_COMPOSE_CONF_PATH, 'w').write(docker_compose_conf)
    # 启动captain
    for i in range(3):
        try:
            subprocess.check_call([DOCKER_COMPOSE_BIN, '-f', CAPTAIN_COMPOSE_CONF_PATH, 'up', '-d'])
        except Exception as e:
            yellow_print('docker-compose captain failed ! {} '.format(e.args))
            time.sleep(2)
            continue
        else:
            break
    else:
        red_print('docker-compose captain failed !')
        raise Exception('docker-compose captain failed !')

    return external_host


def prepare_environment(mode="preparation"):
    # 创建默认存储中间文件的文件夹
    os.makedirs(DCS_REPO, exist_ok=True)

    # 准备在线安装docker的脚本文件
    open(INSTALL_DOCKER_SCRIPT_PATH, 'w').write(reinstall_docker_script)
    subprocess.check_call(['chmod', '777', INSTALL_DOCKER_SCRIPT_PATH])

    # 准备离线安装docker的脚本文件
    open(INSTALL_DOCKER_OFFLINE_SCRIPT, 'w').write(install_docker_offline)
    subprocess.check_call(['chmod', '777', INSTALL_DOCKER_OFFLINE_SCRIPT])

    # 准备配置ngix容器的配置文件
    nginx_conf = NGINX_CONF_TMPL % {'docker_sock_path': DOCKER_SOCK_PATH}
    open(NGINX_CONF_PATH, 'w').write(nginx_conf)

    # 检查是否存在docker-compose文件
    if not os.path.isfile(DOCKER_COMPOSE_BIN):
        print('Downloading docker-compose binary...')
        docker_compose_url = DOCKER_COMPOSE_SOURCE_TMPL.format(platform.system(), platform.machine())
        resp = requests.get(docker_compose_url)
        if not resp.ok:
            red_print('download docker compose binary failed')
            raise Exception('download docker compose binary failed')
        open(DOCKER_COMPOSE_BIN, 'wb').write(resp.content)
        subprocess.check_call(['chmod', '777', DOCKER_COMPOSE_BIN])

    # 开始安装基础环境
    if not net_check():
        # 不联网的情况下， 需要保证repo文件夹的存在.
        ensure_repo()

    if mode == "update-dcs":
        # 用于在线升级dcs版本，该指令要求联网环境
        if not net_check():
            red_print('This operation requires a network connection, please check the network connection.')
            raise Exception('This operation requires a network connection, please check the network connection.')
        dcs_version = None
        while True:
            dcs_version = raw_input(i18n('enter DCS VERSION : ', '请输入新的DCS版本号: '))
            if '.' in dcs_version:
                version = ''.join(dcs_version.split('.'))
                if int(version) < int('250'):
                    red_print(i18n('Does not support versions below 2.5.0', '版本号不应低于2.5.0'))
                    continue
            else:
                red_print(i18n('Input does not meet the requirements!', '输入不符合要求'))
                continue
            break
        if not dcs_version:
            red_print(i18n('can not get dcs_version', '获取dcs版本号失败！'))
            raise Exception('can not get dcs_version')
        # 修改captain部署的yaml版本
        dcs_captain_image = 'daocloud.io/dc_pokeman/captain:{}'.format(dcs_version)
        dcs_admin_image = 'daocloud.io/dc_pokeman/daocloud-admin-dashboard:{}'.format(dcs_version)
        captain_ip = install_captain(dcs_captain_image, dcs_admin_image)

        return captain_ip

    elif mode == 'preparation':
        # 检查网络连接
        if not net_check():
            red_print(i18n('This operation requires a network connection, please check the network connection.',
                           '改操作需要联网环境，请检查网络连接！'))
            raise Exception('This operation requires a network connection, please check the network connection.')
        download_repo(DCE_REPO_SOURCE, DCE_REPO_TAR_PATH)
        # 解压下载的tar包到指定文件夹
        subprocess.check_call(['tar', '-zxvf', DCE_REPO_TAR_PATH, '-C', DCS_REPO])

        try:
            # 检查是否安装docker
            subprocess.check_call(['docker', 'version'])
        except Exception as e:
            # 未安装docker 执行在线安装docker脚本安装docker
            subprocess.check_call(['bash', INSTALL_DOCKER_SCRIPT_PATH])
        try:
            # 再次检查是否安装docker成功
            subprocess.check_call(['docker', 'version'])
        except Exception as e:
            # 提示脚本安装失败，请手动安装docker
            red_print(i18n('please install docker in this host', '安装docker失败请手动安装docker'))
            raise Exception('please install docker in this host')
        # 检查镜像缓存文件是否存在
        if os.path.isdir(DCS_IMAGE_DIR):
            force_download = expect(i18n('image dir found , do you want to download image again?',
                                         '镜像缓存文件夹被发现，是否需要全部下载一遍？'), default=True)

            if force_download:
                # 强制重新下载镜像文件
                try:
                    # 删除原有镜像文件
                    shutil.rmtree(DCS_IMAGE_DIR)
                except:
                    red_print(i18n('can not remove image folder [{}]'.format(DCS_IMAGE_DIR), '无法移动repo文件夹'))
                    raise
        # 检查镜像文件夹是否删除成功
        if not os.path.isdir(DCS_IMAGE_DIR):
            # 开始下载镜像
            download_all_images()

        return True

    elif mode in ['install-builder', 'install-captain']:
        # 关闭环境防火墙
        prepare_enviremont()
        install_docker = False
        # 检查是否安装docker
        try:
            subprocess.check_call(['docker', 'version'])
        except Exception as e:
            install_docker = True
        else:
            # 检查docker版本
            if not check_docker_version():
                install_docker = True
        if install_docker:
            # 1.联网环境下：
            if net_check():
                # 执行在线脚本安装docker
                subprocess.check_call(['bash', INSTALL_DOCKER_SCRIPT_PATH])
            else:
                sys_info = platform.platform(aliased=True)
                if 'Linux' not in sys_info:
                    red_print(i18n('only support install docker offline on a Linux system ', '脚本目前只支持linux系统！'))
                    raise Exception('only support install docker offline on a Linux system ')
                # 执行离线脚本安装docker
                subprocess.check_call(['/bin/bash', INSTALL_DOCKER_OFFLINE_SCRIPT], cwd=DCS_REPO)

        try:
            subprocess.check_call(['docker', 'version'])
        except Exception as e:
            red_print(i18n('install docker faild！', '安装docker失败！'))
            raise Exception('install docker faild！')

        # 依据安装模式加载对应镜像
        if mode == 'install-captain':
            captain_ip = install_captain(DCS_CAPTAIN_IMAGE, DCS_ADMIN_DASHBOARD_IMAGE)
            return captain_ip

        if mode == "install-builder":

            nginx_compose_conf = NGINX_COMPOSE_CONF_TMPL.format(
                DOCKER_SOCK_PATH,
                DOCKER_SOCK_PATH,
            )

            open(NGINX_COMPOSE_CONF_PATH, 'w').write(nginx_compose_conf)
            # 启动nginx代理docker
            for i in range(3):
                try:
                    subprocess.check_call([DOCKER_COMPOSE_BIN, '-f', NGINX_COMPOSE_CONF_PATH, 'up', '-d'])
                except Exception as e:
                    yellow_print(
                        i18n('docker-compose builder failed !{} '.format(e.args), 'docker-compsoe 执行builder-yaml失败！'))
                    time.sleep(2)
                    continue
                else:
                    break
            else:
                red_print('docker-compose nginx-yaml failed !')
                raise Exception('docker-compose nginx-yaml failed !')

            return "12375"

    elif mode == 'install-middleware':
        # 关闭环境防火墙
        prepare_enviremont()
        # 检查离线镜像包
        if os.path.isdir(DCS_MIDDLEWARE_IMAGE_DIR):
            dcs_image_filenames = os.listdir(DCS_MIDDLEWARE_IMAGE_DIR)
            for filename in dcs_image_filenames:
                dcs_image_filename = os.path.join(DCS_MIDDLEWARE_IMAGE_DIR, filename)
                if os.path.isfile(dcs_image_filename):
                    subprocess.check_call(['docker', 'load', '-i', dcs_image_filename])
        else:
            # 断网情况下需保证image文件夹存在
            if not net_check():
                red_print('please ensure that the image offline folder exists.{}'.format(DCS_MIDDLEWARE_IMAGE_DIR))
                raise Exception('please ensure that the image offline folder exists.', DCS_MIDDLEWARE_IMAGE_DIR)

        # 检测主机是否安装docker
        try:
            subprocess.check_call(['docker', 'version'])
        except Exception as e:
            if net_check():
                # 执行在线脚本安装docker
                subprocess.check_call(['bash', INSTALL_DOCKER_SCRIPT_PATH])
            else:
                sys_info = platform.platform(aliased=True)
                if 'Linux' not in sys_info:
                    red_print('only support install docker offline on a Linux system ')
                    raise Exception('only support install docker offline on a Linux system ')
                # 执行离线脚本安装docker
                subprocess.check_call(['/bin/bash', INSTALL_DOCKER_OFFLINE_SCRIPT])

        # 确认Docker是否已被安装
        try:
            subprocess.check_call(['docker', 'version'])
        except Exception as e:
            red_print('please install docker!')
            raise Exception('please install docker!')

        # 启动中间件服务
        if not os.path.isfile(MIDDLEWARE_COMPOSE_CONF_PATH):
            open(MIDDLEWARE_COMPOSE_CONF_PATH, 'w').write(MIDDLEWARE_COMPOSE_CONF_TMPL)
        for i in range(3):
            try:
                subprocess.check_call([DOCKER_COMPOSE_BIN, '-f', MIDDLEWARE_COMPOSE_CONF_PATH, 'up', '-d'])
            except Exception as e:
                time.sleep(2)
                continue
            else:
                break
        else:
            red_print('docker-compose middleware failed !')
            raise Exception('docker-compose middleware failed !')

        return True


if __name__ == '__main__':
    yellow_print(i18n('please select install mode!', '请选择一个安装模式!'))
    yellow_print(
        i18n('[ preparation ] prepare installing-environment for a offline machine', '[ preparation ] 为一台离线计算机准备离线环境'))
    yellow_print(
        i18n('[ install-captain ] start installing-captain for this machine', '[ install-captain ] 安装captain到这台计算机'))
    yellow_print(
        i18n('[ install-builder ] Start to configure the installation environment for this machine',
             '[ install-builder ] 开始配置DCS组件的合格安装环境'))
    yellow_print(
        i18n('[ install-middleware ] Start installing middleware  for this machine',
             '[ install-middleware ] 开始安装中间件到本机'))
    yellow_print(
        i18n('[ update-dcs ] update dcs version',
             '[ update-dcs ] 更新dcs版本'))

    yellow_print(i18n('[ quit ] quit installer', '[ quit ] 退出本程序'))

    while True:

        mode = raw_input(i18n('enter mode here : ', '请输入你的安装模式 : '))
        mode = mode.strip().lower()

        if mode in ['install-captain', 'update-dcs']:

            external_host = prepare_environment(mode=mode)

            yellow_print(i18n(
                'DCS Captain installed! Now, Open your browser and visit http://{}:30080'.format(external_host),
                'DCS Captain 安装完成! 请使用浏览器打开 http://{}:30080'.format(external_host)
            ))
            cyan_print(banner)
            break

        elif mode == 'install-builder':

            port = prepare_environment(mode=mode)

            yellow_print(i18n(
                'CONGRATULATION! THE DOCKER REMOTE API PORT IS {}'.format(port),
                '恭喜你！ ，docker远程API端口已开启，端口号是{}'.format(port)
            ))
            cyan_print(banner)
            break
        elif mode == 'install-middleware':

            result = prepare_environment(mode=mode)
            if result == 'DOWN':
                yellow_print(i18n(
                    'CONGRATULATION! THE MIDDLEWARE IS RUNNING!', '恭喜你！ ，中间件安装完毕'
                ))
            else:
                yellow_print(i18n('installation faild!', '安装失败！'))
            cyan_print(banner)
            break

        elif mode == 'preparation':

            prepare_environment(mode=mode)

            yellow_print(i18n(
                'DCS Captain offline resource Packed! Now, Copy dcs_installer with folder [{}] to target system!'.format(
                    DCS_REPO),
                'DCS Captain 离线资源已经打包! 现在请把dcs_installer带着[{}]文件夹一起拷贝到需要安装DCS的机子'.format(DCS_REPO)
            ))
            cyan_print(banner)
            break

        elif mode == 'quit':

            sys.exit(2)

        else:

            yellow_print(i18n(
                'install mode only can be one of "install-captain","install-builder", '
                '"install-middlerware" "preparation" , "install-midleware"and "quit"',
                '安装模式只能是install-captain、install-builder、install-middleware、preparation以及quit中的一个'))
