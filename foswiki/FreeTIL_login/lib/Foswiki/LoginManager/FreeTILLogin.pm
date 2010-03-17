# Module of Foswiki - The Free and Open Source Wiki, http://foswiki.org/
#
# Copyright (C) 2010 Egil Möller, FreeCode AS <egil.moller@freecode.no>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version. For
# more details read LICENSE in the root of this distribution.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
package Foswiki::LoginManager::FreeTILLogin;
use base Foswiki::LoginManager::ApacheLogin;
use strict;
use warnings;
use Assert;
use Foswiki::LoginManager::ApacheLogin;
use Foswiki::Sandbox;
use WWW::Curl::Easy;
use JSON;

# @Foswiki::LoginManager::FreeTILLogin::ISA = qw( Foswiki::LoginManager::ApacheLogin );

sub new {
  my ($class, $session) = @_;

  my $this = bless( $class->SUPER::new($session), $class );
  $session->{loginManager} = $this;
  Foswiki::registerTagHandler( 'LOGOUT',    \&_LOGOUT );
  Foswiki::registerTagHandler( 'LOGOUTURL', \&_LOGOUTURL );

  return $this;
}


sub _LOGOUTURL {
    return '/tuit/account/logout';
}

sub _LOGOUT {
    my ( $session, $params, $topic, $web ) = @_;
    my $this = $session->{users}->{loginManager};

    return '' unless $session->inContext('authenticated');

    my $url = _LOGOUTURL(@_);
    if ($url) {
        my $text = $session->templates->expandTemplate('LOG_OUT');
        return CGI::a( { href => $url }, $text );
    }
    return '';
}

sub getUser {
    my $this = shift;

    my $session_id = $this->{session}->{request}->cookie('sessionid');
    my $server_host = $ENV{'SERVER_NAME'};
    my $browser_host = $ENV{'HTTP_HOST'};
    my $request_uri = $ENV{'REQUEST_URI'};
    my $server_port = $ENV{'SERVER_PORT'};
    my $port_part = ($server_port != 80) ? ":$server_port" : "";

    my $curl = new WWW::Curl::Easy;
    $curl->setopt(CURLOPT_HEADER, 0);
    $curl->setopt(CURLOPT_URL, "http://" . $server_host . $port_part . "/tuit/account/session/");
    $curl->setopt(CURLOPT_FOLLOWLOCATION, 1);
    $curl->setopt(CURLOPT_COOKIE, "sessionid=" . $session_id);
    $curl->setopt(CURLOPT_NOPROGRESS, 1);

    my $response_header;
    open (my $fileh, ">", \$response_header);
    $curl->setopt(CURLOPT_WRITEHEADER, \$fileh);

    my $response_body;
    open (my $fileb, ">", \$response_body);
    $curl->setopt(CURLOPT_FILE, \$fileb);

    # Starts the actual request
    my $retcode = $curl->perform;

    # Looking at the results...
    if ($retcode == 0) {
	    my $response_data = jsonToObj($response_body);

	    if (!$response_data->{'username'}) {
		$this->{session}->{response}
		  ->redirect( -url => "/tuit/account/login/");
                return;
	    }

	    $this->{_freetil_user} = $response_data->{username};
	    @{$this->{_freetil_groups}} = @{$response_data->{groups}};

	    return $response_data->{'username'};
    } else {
	Foswiki::LoginManager::_trace(
	    $this,
	    "Unable to fetch login data from FreeTIL: " .$curl->strerror($retcode)." ($retcode)\n");
	$this->{session}->{response}
	    ->redirect( -url => "/tuit/account/login/");

    }
}

1;
