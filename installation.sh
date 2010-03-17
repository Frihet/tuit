# *****************
# * General setup *
# *****************

# Common packages

apt-get install git-core curl gettext postgresql-8.3
apt-get install python-psycopg2 gcc

# Set up locales

echo > /var/lib/locales/supported.d/local sv_SE.UTF-8 UTF-8
echo > /var/lib/locales/supported.d/local nb_NO.UTF-8 UTF-8
locale-gen

# **************************
# * CONFIGURING POSTGRESQL *
# **************************

# Set up postgres authentification
echo "local   all   all    md5" >> /etc/postgresql/8.3/main/pg_hba.conf
/etc/init.d/postgresql-8.3 restart

#
# Create a 'tuit' postgresql user and a 'tuit' postgresql database, memorize the chosen password.
#

# **********************
# * CONFIGURING APACHE *
# **********************

# Configure apache: 
# edit /etc/apache/sites-available/tuit
# (Assumes tuit lives in /srv/www/django/tuit)

DocumentRoot "/var/www/html"
RedirectMatch ^/$ /tuit

<Location "/tuit/">
    PythonPath "['/srv/www/django/'] + sys.path"
    SetHandler python-program
    PythonHandler django.core.handlers.modpython
    SetEnv DJANGO_SETTINGS_MODULE tuit.settings
    PythonDebug Off
</Location>

AliasMatch ^/static(.*) /src/www/django/tuit/static$1 

# Enable the changes we made

a2ensite tuit
a2enmod proxy_http
a2enmod proxy
a2enmod mod_python
a2enmod rewrite
/etc/init.d/apache2 restart


# ************************
# * INSTALLING FREECDMB: *
# ************************

apt-get install libmysqlclient15-dev php5-dev gcc make postgresql-server-dev-8.3 
apt-get install php-pear
apt-get install autoconf apache2-threaded-dev debian-builder
apt-get install graphviz

pecl install pdo
PHP_PDO_SHARED=1 pecl install pdo_pgsql
pear install Image_Graphviz

mkdir -p /srv/www/html
cd /srv/www/html
git clone ssh://scm.freecode.no/srv/git/public/freecmdb.git FreeCMDB
cd FreeCMDB
git clone ssh://scm.freecode.no/srv/git/public/fc-framework.git common

# Add the following lines to the [PHP] section of /etc/php5/apache2/php.ini:

extension=pdo.so
extension=pdo_pgsql.so
extension=pdo_mysql.so
extension=json.so

# Visit url http://SITE/FreeCMDB/ciProperty
# Set your language. Must be a complete locale string, e.g. nb_NO.utf8 for norwegian.


# FIXME: PLUGINS!!!!!!!!!!!!!

# *******************
# * INSTALLING TUIT *
# *******************

# Check out the tuit source code
mkdir -p /srv/www/django
cd /srv/www/django
git clone https://projects.freecode.no/git/tuit.git tuit
ln -s /srv/www/html/FreeCMDB/common/static /srv/www/django/tuit/static/common

cp /srv/www/django/tuit/settings.py.example /srv/www/django/tuit/settings.py 
# Edit  /srv/www/django/tuit/settings.py as appropriate,
# The following fileds should usually be customized:
DATABASE_NAME = 'tuit'
DATABASE_USER = 'tuit'
DATABASE_PASSWORD = 'XXXXXXXX'
LANGUAGE_CODE='no'
TIME_ZONE = 'Europe/Oslo'

cd tuit

# Create tuit tables
python manage.py syncdb

# Compile po files
python /var/lib/python-support/python2.5/django/bin/compile-messages.py

# Load default data
python manage.py loaddata ticket/fixtures/default_data.json 
python manage.py loaddata menu/fixtures/default_data.json 
python manage.py loaddata search/fixtures/default_data.json 

# Set up permissions
chgrp www-data -R /srv/www
chmod g+r -R /srv/www

# Create directory for storing attachments
mkdir /srv/www/tuit_attachments
chown www-data:www-data -R /srv/www/tuit_attachments

# Install the following crontab entry for user www-data:
# m h  dom mon dow   command
* * * * * cd /srv/www/django/tuit/; python mail.py

# Configuring Tuit
# Visit http://SITE/tuit/admin/ticket/property/
# and set variables as appropriate. 
# All values are json data. So quote those strings!
# Some required properties to update:

attachment_directory	"/srv/www/tuit_attachments"

# Some suggested properties to update:
site_description
site_url
tracker_web
username_case_insensitive

# **********************
# * INSTALLING FOSWIKI *
# **********************

echo "deb http://fosiki.com/Foswiki_debian/ stable main contrib" >>/etc/apt/sources.list
echo "deb-src http://fosiki.com/Foswiki_debian/ stable main contrib" >>/etc/apt/sources.list

apt-get install foswiki

# FIXME: Anything else needed for foswiki? I didn't do these steps myself... :-/

# To install single sign on:
Apply patch from http://foswiki.org/Tasks/Item1805
Install the plugin tuit/foswiki/FreeTIL_login
In /etc/foswiki/LocalSite.cfg:
  $Foswiki::cfg{LoginManager} = 'Foswiki::LoginManager::FreeTILLogin';
  $Foswiki::cfg{Validation}{Method} = 'none';
  $Foswiki::cfg{UseClientSessions} = 0;
  $Foswiki::cfg{UserMappingManager} = 'Foswiki::Users::FreeTILUserMapping';

# FIXME: What about installing the templates?

# FXIME: What about WebLeftBar

# FXIME: What about initial content?

# ***************
# * DATE FORMAT *
# ***************

# The following places are were date display format is configured:
#
# Foswiki: file /etc/foswiki/LocalSite.cfg
# Perl date string format? Unfamiliar with it, I'm afraid...
# $Foswiki::cfg{DefaultDateFormat} = '$day.$mo.$year';
#
# FreeCMDB: url http://SITE/FreeCMDB/ciProperty
# Set the date and date and time columns. Standard php date string format
#
# TUIT: url http://SITE/tuit/admin/ticket/property/
# Set the date_format and datetimeformat columns. Standard Python date string format


# ******************************
# *  INSTALLING NTLM SUPPORT   *
# * (OPTIONAL, AD INTEGRATION) *
# ******************************

# First, install the following packages:
apt-get install python-ldap
apt-get install python-dns
apt-get install python-ply
apt-get install python-nose
apt-get install python-kerberos
apt-get install python-dnspython
apt-get install krb5-admin-server krb5-kdc krb5-config krb5-user krb5-clients krb5-rsh-server
apt-get install sasl2
apt-get install libsasl2
apt-get install gcc
apt-get install python-dev
apt-get install libkrb5-dev
apt-get install cyrus-sasl-gssapi
apt-get install cyrus-sasl2
apt-get install libsasl2
apt-get install libsasl2-modules-ldap
apt-get install libsasl2-2
apt-get install libsasl2-modules
apt-get install libsasl2-modules-gssapi-mit
apt-get install ntp-server
apt-get install ntp
apt-get install autoconf apache2-threaded-dev debian-builder

# Start ntp, it it's not already running
/etc/init.d/ntp start

# Build and install python-ad
cd /root
mkdir -p build/python-ad
cd build/python-ad
wget http://python-ad.googlecode.com/files/python-ad-0.9.tar.gz
tar -zxf python-ad-0.9.tar.gz
rm python-ad-0.9.tar.gz
cd python-ad-0.9
python setup.py build && python setup.py install

# build and install ntlm support for apache
cd /root
mkdir -p build/ntlm
cd build/ntlm
wget http://samba.org/ftp/unpacked/lorikeet/mod_auth_ntlm_winbind/{500mod_auth_ntlm_winbind.info,AUTHORS,Makefile.in,README,VERSION,configure.in,mod_auth_ntlm_winbind.c} 
mkdir debian
cd debian
wget http://samba.org/ftp/unpacked/lorikeet/mod_auth_ntlm_winbind/debian/{auth_ntlm_winbind.load,changelog,compat,control,copyright,rules}
cd ..
autoconf
./configure --with-apxs=/usr/bin/apxs2 --with-apache=/usr/sbin/apache2
make
make install
cp debian/auth_ntlm_winbind.load /etc/apache2/mods-available/
a2enmod auth_ntlm_winbind



