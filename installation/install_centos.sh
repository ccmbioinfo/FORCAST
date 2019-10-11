yum update -y
yum install -y vim
yum install -y httpd

cd /etc/yum.repos.d/
echo -e '[mongodb-org-3.2]\nname=MongoDB Repository\nbaseurl=https://repo.mongodb.org/yum/redhat/$releasever/mongodb-org/3.2/x86_64/\ngpgcheck=1\nenabled=1\ngpgkey=https://www.mongodb.org/static/pgp/server-3.2.asc' >mongodb-org-3.2.repo
yum -y install mongodb-org


yum install -y https://centos7.iuscommunity.org/ius-release.rpm
yum update -y
yum install -y python36u python36u-libs python36u-devel python36u-pip


cd ~
yum install -y wget
wget https://download-ib01.fedoraproject.org/pub/epel/7/x86_64/Packages/b/bwa-0.7.12-1.el7.x86_64.rpm
rpm -Uvh bwa-0.7.12-1.el7.x86_64.rpm

wget https://bootstrap.pypa.io/get-pip.py
python get-pip.py
pip install -r requirements.txt
python3.6 -m pip install -r requirements_v3.txt
