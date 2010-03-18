#! /bin/bash
############################################################
#                    General setup                         #
############################################################
# Assumes tuit should live in /srv/www/django/tuit         #
# Assumes FreeCMDB should live in /srv/www/html            #
# Assumes you want a username admin with password freetil  #
############################################################

# Exit on any errors
set -e

# Print what we're doing
set -v

# Update package lists so we'll install latest version of everything
apt-get update

# Misc common packages
apt-get install -y git-core curl gettext postgresql-8.3 python-psycopg2 gcc pwgen apache2 libapache2-mod-python

# Set up locales
apt-get install -y language-pack-en language-pack-nb
dpkg-reconfigure locales

# **************************
# * CONFIGURING POSTGRESQL *
# **************************

# Set up postgres authentification
echo "local   all   all    md5" >> /etc/postgresql/8.3/main/pg_hba.conf
/etc/init.d/postgresql-8.3 restart

# Create a 'tuit' postgresql user and a 'tuit' postgresql database, memorize the chosen password.
TUIT_DB_PW="$(pwgen 20 1)"
su - postgres <<EOF
 createuser -S -D -R tuit
 createdb tuit
 echo "grant all on database tuit to tuit;" | psql
 echo "alter role tuit with password '${TUIT_DB_PW}';" | psql
EOF

# **********************
# * CONFIGURING APACHE *
# **********************

# Configure apache: 

cat > /etc/apache2/sites-available/tuit <<EOF
DocumentRoot "/srv/www/html"
RedirectMatch ^/$ /tuit

<Location "/tuit">
    PythonPath "['/srv/www/django/'] + sys.path"
    SetHandler python-program
    PythonHandler django.core.handlers.modpython
    SetEnv DJANGO_SETTINGS_MODULE tuit.settings
    PythonDebug Off
</Location>

AliasMatch ^/static(.*) /srv/www/django/tuit/static\$1
EOF

# Enable the changes we made

a2dissite default
a2ensite tuit
a2enmod proxy_http
a2enmod proxy
a2enmod mod_python
a2enmod rewrite


# ************************
# * INSTALLING FREECDMB: *
# ************************

apt-get install -y libmysqlclient15-dev php5-dev gcc make postgresql-server-dev-8.3 php-pear autoconf apache2-threaded-dev debian-builder graphviz libapache2-mod-php5 php5-curl

pecl install pdo
PHP_PDO_SHARED=1 pecl install pdo_pgsql
pear install Image_Graphviz
pecl install json

# Add the following lines to the [PHP] section of /etc/php5/apache2/php.ini:
patch /etc/php5/apache2/php.ini <<EOF
--- /etc/php5/apache2/php.ini.orig	2010-03-17 14:55:56.000000000 +0000
+++ /etc/php5/apache2/php.ini	2010-03-17 14:57:25.000000000 +0000
@@ -595,6 +595,12 @@
 ;;;;;;;;;;;;;;;;;;;;;;
 ; Dynamic Extensions ;
 ;;;;;;;;;;;;;;;;;;;;;;
+
+extension = pdo.so
+extension = pdo_pgsql.so
+extension = pdo_mysql.so
+extension = json.so
+
 ;
 ; If you wish to have an extension loaded automatically, use the following
 ; syntax:
EOF


mkdir -p /srv/www/html
cd /srv/www/html
git clone http://github.com/freecode/freecmdb.git FreeCMDB
cd FreeCMDB
git clone http://github.com/freecode/fc-framework.git common
cat > config.php <<EOF
<?php
define('FC_DSN_DEFAULT', 'pgsql:dbname=tuit;host=127.0.0.1;user=tuit;password=${TUIT_DB_PW}');
?>
EOF
su - postgres -c "psql tuit" < static/schema.sql
su - postgres -c "psql tuit" <<EOF
insert into ci_property (name, value) values ('chart.maxDepth', '');
insert into ci_property (name, value) values ('chart.maxItems', '');
insert into ci_property (name, value) values ('pager.itemsPerPage', '');
insert into ci_property (name, value) values ('core.baseURL', 'http://$(hostname -f)/');
insert into ci_property (name, value) values ('core.baseUrl', '/FreeCMDB/');
insert into ci_property (name, value) values ('plugin.drilldown.root', '0');
insert into ci_property (name, value) values ('core.dateTimeFormat', 'd.m.Y H:i');
insert into ci_property (name, value) values ('core.dateFormat', 'd.m.Y');
insert into ci_property (name, value) values ('core.locale', 'nb_NO.utf8');
insert into ci_property (name, value) values ('loginTuit.editGroup', '');
insert into ci_property (name, value) values ('loginTuit.adminGroup', '');
insert into ci_property (name, value) values ('loginTuit.viewGroup', '');
insert into ci_property (name, value) values ('plugin.tuit.DSN', 'pgsql:dbname=tuit;host=127.0.0.1;user=tuit;password=${TUIT_DB_PW}');
insert into ci_property (name, value) values ('plugin.tuit.closedId', '2');
insert into ci_property (name, value) values ('tuit.enabled', '1');
insert into ci_property (name, value) values ('plugin.breadcrumb.root_url', 'CMDB');
insert into ci_property (name, value) values ('plugin.breadcrumb.root_title', 'http://$(hostname -f)/FreeCMDB/plugins/drilldown/drilldown');
insert into ci_property (name, value) values ('plugin.breadcrumb.root', '<a href="/tuit">Hjem</a> &gt; <a href="/FreeCMDB/plugins/drilldown/drilldown">CMDB</a>');
insert into ci_property (name, value) values ('plugin.breadcrumb.admin_root', '<a href="/tuit">Hjem</a> &gt; <a href="/tuit/admin">Administrasjon</a> &gt; <a href="/FreeCMDB/admin">CMDB</a>');

insert into ci_event (event_name, class_name) values ('Sidebar', 'drilldownPlugin');
insert into ci_event (event_name, class_name) values ('Startup', 'loginTuitPlugin');
insert into ci_event (event_name, class_name) values ('CiControllerView', 'tuitPlugin');
insert into ci_event (event_name, class_name) values ('CiControllerRemove', 'tuitPlugin');
insert into ci_event (event_name, class_name) values ('CiControllerSaveAll', 'tuitPlugin');
insert into ci_event (event_name, class_name) values ('CiControllerUpdateField', 'tuitPlugin');
insert into ci_event (event_name, class_name) values ('CiControllerCopy', 'tuitPlugin');
insert into ci_event (event_name, class_name) values ('CiControllerRevert', 'tuitPlugin');
insert into ci_event (event_name, class_name) values ('CiListControllerView', 'tuitPlugin');
insert into ci_event (event_name, class_name) values ('Startup', 'drilldownPlugin');
insert into ci_event (event_name, class_name) values ('Startup', 'tuitPlugin');
insert into ci_event (event_name, class_name) values ('Shutdown', 'breadcrumbPlugin');

insert into ci_plugin (name, description, version, author) values ('drilldown', 'Plugin for structured navigation through the CMDB', '1.0', 'Axel Liljencrantz');
insert into ci_plugin (name, description, version, author) values ('loginTuit', 'Single signon via tuit', '1.0', 'Axel Liljencrantz');
insert into ci_plugin (name, description, version, author) values ('tuit', 'Integration for the Tuit ticket handling system', '1.0', 'Axel Liljencrantz, FreeCode AS');
insert into ci_plugin (name, description, version, author) values ('breadcrumb', 'Breadcrumbs', '0,01', 'Egil Möller');

insert into ci (id, ci_type_id) select 0, ci_type.id from ci_type where ci_type.name = 'Service';
insert into ci_column (ci_id, ci_column_type_id, value) select 0, ci_column_type.id, 'Root' from ci_column_type where ci_column_type.name = 'Name';

EOF

# *******************
# * INSTALLING TUIT *
# *******************

apt-get install -y python-django python-beautifulsoup

# Check out the tuit source code
mkdir -p /srv/www/django
cd /srv/www/django
git clone http://github.com/freecode/tuit.git tuit
mkdir -p /srv/www/django/tuit/attachments
chmod ugo+rwx /srv/www/django/tuit/attachments
cd tuit/static
rm common
ln -s ../../../html/FreeCMDB/common/static common
cd ..

rmdir json
git clone http://github.com/niligulmohar/python-symmetric-jsonrpc.git python-symmetric-jsonrpc
ln -s python-symmetric-jsonrpc/symmetricjsonrpc json

cp settings.py.example settings.py 
patch settings.py <<EOF
--- settings.py.example	2010-03-18 11:55:35.000000000 +0100
+++ settings.py	2010-03-18 13:08:28.000000000 +0100
@@ -12,8 +12,8 @@
 DATABASE_ENGINE = 'postgresql_psycopg2'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'ado_mssql'.
 DATABASE_NAME = 'tuit'             # Or path to database file if using sqlite3.
 DATABASE_USER = 'tuit'             # Not used with sqlite3.
-DATABASE_PASSWORD = 'Sommer2009!'         # Not used with sqlite3.
-DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
+DATABASE_PASSWORD = '${TUIT_DB_PW}'         # Not used with sqlite3.
+DATABASE_HOST = 'localhost'             # Set to empty string for localhost. Not used with sqlite3.
 DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.
 
 # Local time zone for this installation. Choices can be found here:
@@ -62,10 +62,7 @@
     'django.middleware.common.CommonMiddleware',
     'django.contrib.sessions.middleware.SessionMiddleware',
 #    'django.middleware.locale.LocaleMiddleware',
-#    'django.contrib.auth.middleware.AuthenticationMiddleware',
-    'tuit.iwa.middleware.AuthenticationMiddleware',
-#    'django.contrib.auth.middleware.AuthenticationMiddleware',
-#    'django.contrib.auth.middleware.RemoteUserMiddleware',
+    'django.contrib.auth.middleware.AuthenticationMiddleware',
     'django.middleware.doc.XViewMiddleware',
 )
 
@@ -75,7 +72,7 @@
     # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
     # Always use forward slashes, even on Windows.
     # Don't forget to use absolute paths, not relative paths.
-    '/var/www/tuit/templates/',
+    '/srv/www/django/tuit/templates/',
 )
 
 INSTALLED_APPS = (
@@ -89,7 +86,12 @@
     'tuit.ticket',
     'tuit.account',
     'tuit.home',
-)
+    'tuit.trend',
+    'tuit.comment',
+    'tuit.status',
+    'tuit.query',
+    'tuit.tuitadmin',
+ )
 
 LOGIN_REDIRECT_URL='/tuit/search'
 
EOF

# Create tuit tables
python manage.py syncdb

patch settings.py <<EOF
--- settings.py.orig	2010-03-18 13:11:06.000000000 +0100
+++ settings.py	2010-03-18 13:11:21.000000000 +0100
@@ -79,7 +79,6 @@
     'django.contrib.auth',
     'django.contrib.contenttypes',
     'django.contrib.sessions',
-    'django.contrib.sites',
     "django.contrib.admin",
     'tuit.search',
     'tuit.menu',
EOF

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
crontab -u www-data - <<EOF
# m h  dom mon dow   command
* * * * * cd /srv/www/django/tuit/; python mail.py
EOF

su - postgres -c "psql tuit" <<EOF
insert into ticket_property (name, value) values ('issue_default_status', '1');
insert into ticket_property (name, value) values ('username_case_insensitive', 'true');
insert into ticket_property (name, value) values ('email_registration_confirmation', 'false');
insert into ticket_property (name, value) values ('tracker_web', '"http://$(hostname -f)/"');
insert into ticket_property (name, value) values ('pgp_roles', 'false');
insert into ticket_property (name, value) values ('pgp_enable', 'false');
insert into ticket_property (name, value) values ('mailgw_ignore_alternatives', 'false');
insert into ticket_property (name, value) values ('issue_closed_id', '[2]');
insert into ticket_property (name, value) values ('date_format', '"%d.%m.%Y"');
insert into ticket_property (name, value) values ('site_url', '"http://$(hostname -f)"');
insert into ticket_property (name, value) values ('site_location', '"/tuit"');
insert into ticket_property (name, value) values ('default_charset', '"latin-1"');
insert into ticket_property (name, value) values ('web_external_default_mail', '["requester","assigned_to","co_responsible"]');
insert into ticket_property (name, value) values ('web_internal_default_mail', '["assigned_to"]');
insert into ticket_property (name, value) values ('issue_default_impact', '3');
insert into ticket_property (name, value) values ('issue_default_urgency', '3');
insert into ticket_property (name, value) values ('datetime_format', '"%d.%m.%Y %H:%M"');
insert into ticket_property (name, value) values ('attachment_directory', '"/srv/www/django/tuit/attachments"');
insert into ticket_property (name, value) values ('issue_default_type', '1');
insert into ticket_property (name, value) values ('issue_default_category', '6');
insert into ticket_property (name, value) values ('web_create_default_mail', '["requester","assigned_to","co_responsible"]');
insert into ticket_property (name, value) values ('mail_create_mail', '["requester"]');
insert into ticket_property (name, value) values ('admin_email', '"root@$(hostname -f)"');
insert into ticket_property (name, value) values ('site_description', '"New FreeTIL site at $(hostname -f)"');
insert into ticket_property (name, value) values ('priority_class', '[null, "emergency","emergency","normal","normal","normal"]');
insert into ticket_property (name, value) values ('priority_matrix', '[[1, 1, 2, 3,3],[1,2,2,3,4],[2,2,3,4,5],[2,3,4,4,5],[3,4,5,5,5]]');
insert into ticket_property (name, value) values ('mail_update_mail', '["requester","assigned_to","co_responsible_list","last_updater"]');

delete from django_site;
delete from auth_user_groups;
delete from auth_group;
delete from auth_user;

insert into django_site(id,name,domain) values (1, '$(hostname)','$(hostname -f)');
insert into auth_group (name) values('AdminGroup');
insert into auth_user (username, password, first_name, last_name, email, is_staff, is_active, is_superuser, last_login, date_joined) values('admin', 'sha1\$77ba2\$faa623130e3bdb5f94ad02196f099488ab7828c4', '', '', '', true, true, true, '2010-03-17', '2010-03-17');
insert into auth_user_groups (user_id, group_id) select auth_user.id, auth_group.id from auth_user, auth_group where auth_user.username = 'admin' and auth_group.name = 'AdminGroup'; 

EOF

su postgres <<EOF
for table in \$(echo "select c.relname FROM pg_catalog.pg_class c;" | psql tuit | grep -v "pg_" | grep -v "sql_" | grep "^ "); do
  echo "grant all on table \$table to tuit;"
done | psql tuit
EOF

# **********************
# * INSTALLING FOSWIKI *
# **********************

cat >>/etc/apt/sources.list <<EOF
deb http://fosiki.com/Foswiki_debian/ stable main contrib
deb-src http://fosiki.com/Foswiki_debian/ stable main contrib
EOF
apt-get update -y
apt-get install -y --force-yes foswiki libwww-curl-perl libjson-perl foswiki-treeplugin < /dev/null

#Apply patch from http://foswiki.org/Tasks/Item1805
patch /var/lib/foswiki/lib/Foswiki/UI.pm <<EOF
index 90ff428..751dc17 100644
--- a/core/lib/Foswiki/UI.pm
+++ b/core/lib/Foswiki/UI.pm
@@ -521,6 +521,9 @@ See Foswiki::Validation for more information.
 sub checkValidationKey {
     my (\$session) = @_;
 
+    # If validation is disabled, do nothing
+    return if ( \$Foswiki::cfg{Validation}{Method} eq 'none' );
+
     # Check the nonce before we do anything else
     my \$nonce = \$session->{request}->param('validation_key');
     \$session->{request}->delete('validation_key');
EOF

# Install FreeTIL single sign on:
ln -s /srv/www/django/tuit/foswiki/FreeTIL_login/lib/Foswiki/LoginManager/FreeTILLogin.pm /var/lib/foswiki/lib/Foswiki/LoginManager/FreeTILLogin.pm
ln -s /srv/www/django/tuit/foswiki/FreeTIL_login/lib/Foswiki/Users/FreeTILUserMapping.pm /var/lib/foswiki/lib/Foswiki/Users/FreeTILUserMapping.pm

patch /etc/foswiki/LocalSite.cfg <<EOF
--- /etc/foswiki/LocalSite.cfg.orig	2010-03-17 19:04:50.000000000 +0000
+++ /etc/foswiki/LocalSite.cfg	2010-03-17 19:07:56.000000000 +0000
@@ -2,19 +2,22 @@
 \$Foswiki::cfg{Site}{Lang} = 'en';
 \$Foswiki::cfg{LocalesDir} = '/var/lib/foswiki/locale';
 \$Foswiki::cfg{ScriptUrlPath} = '/foswiki/bin';
-\$Foswiki::cfg{DefaultUrlHost} = 'http://localhost/';
-\$Foswiki::cfg{PermittedRedirectHostUrls} = 'http://localhost;http://127.0.0.1';
+\$Foswiki::cfg{DefaultUrlHost} = 'http://$(hostname -f)/';
+\$Foswiki::cfg{PermittedRedirectHostUrls} = 'http://$(hostname -f)';
 \$Foswiki::cfg{Site}{FullLang} = 'en-us';
 \$Foswiki::cfg{PubUrlPath} = '/foswiki/pub';
 \$Foswiki::cfg{PubDir} = '/var/lib/foswiki/pub';
 \$Foswiki::cfg{TemplateDir} = '/var/lib/foswiki/templates';
 \$Foswiki::cfg{Site}{CharSet} = 'iso-8859-15';
-\$Foswiki::cfg{LoginManager} = 'Foswiki::LoginManager::TemplateLogin';
+\$Foswiki::cfg{LoginManager} = 'Foswiki::LoginManager::FreeTILLogin';
+\$Foswiki::cfg{UserMappingManager} = 'Foswiki::Users::FreeTILUserMapping';
+\$Foswiki::cfg{Validation}{Method} = 'none';
+\$Foswiki::cfg{UseClientSessions} = 0;
 \$Foswiki::cfg{Plugins}{WysiwygPlugin}{Enabled} = 1;
 \$Foswiki::cfg{RCS}{WorkAreaDir} = '/var/lib/foswiki/working/work_area';
 \$Foswiki::cfg{TempfileDir} = '/var/lib/foswiki/working/tmp';
 \$Foswiki::cfg{WorkingDir} = '/var/lib/foswiki/working';
 \$Foswiki::cfg{SafeEnvPath} = '/usr/bin:/bin';
-\$Foswiki::cfg{Register}{EnableNewUserRegistration} = 1;
+\$Foswiki::cfg{Register}{EnableNewUserRegistration} = 0;
 \$Foswiki::cfg{EnableEmail} = 0; 
 \$Foswiki::cfg{WebMasterEmail} = 'webmaster@localhost';
@@ -25,6 +28,12 @@
 \$Foswiki::cfg{LogDir} = '/var/log/foswiki';
 \$Foswiki::cfg{ConfigurationLogName} = '\$Foswiki::cfg{LogDir}/configurationlog.txt';
 \$Foswiki::cfg{DebugFileName} = '\$Foswiki::cfg{LogDir}/debug.txt';
 \$Foswiki::cfg{WarningFileName} = '\$Foswiki::cfg{LogDir}/warn%DATE%.txt';
 \$Foswiki::cfg{LogFileName} = '\$Foswiki::cfg{LogDir}/log%DATE%.txt';
+
+\$Foswiki::cfg{TemplateDir} = '/srv/www/django/tuit/foswiki/templates';
+\$Foswiki::cfg{TemplatePath} = '/srv/www/django/tuit/foswiki/templates/\$web/\$name.\$skin.tmpl, /srv/www/django/tuit/foswiki/templates/\$name.\$skin.tmpl, \$web.\$skinSkin\$nameTemplate, System.\$skinSkin\$nameTemplate, /var/lib/foswiki/templates/\$web/\$name.tmpl, /srv/www/django/tuit/foswiki/templates/\$name.tmpl, \$web.\$nameTemplate, System.\$nameTemplate';
+\$Foswiki::cfg{Plugins}{TreePlugin}{Enabled} = 1;
+\$Foswiki::cfg{Plugins}{TreePlugin}{Module} = 'Foswiki::Plugins::TreePlugin';
+
 1;
EOF

# Install translations
rsync -a /srv/www/django/tuit/foswiki/locale/ /var/lib/foswiki/locale/

# Install some initial content in the System web (e.g. WebLeft bar for
# the left menu, WebsPreferences for the admin UI)
rsync -a /srv/www/django/tuit/foswiki/pages/ /var/lib/foswiki/data/
rsync -a /var/lib/foswiki/data/_default/ /var/lib/foswiki/data/KB
rsync -a /var/lib/foswiki/data/_default/ /var/lib/foswiki/data/IKB

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




/etc/init.d/apache2 restart

if [ "$INSTALL_NTLM" ]; then
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
fi
