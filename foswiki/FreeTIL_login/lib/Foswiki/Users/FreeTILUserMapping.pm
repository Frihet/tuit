# Module of Foswiki - The Free and Open Source Wiki, http://foswiki.org/
#
# Copyright (C) 2006-2009 Michael Daum http://michaeldaumconsulting.com
# Portions Copyright (C) 2006 Spanlink Communications
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
# As per the GPL, removal of this notice is prohibited.

package Foswiki::Users::FreeTILUserMapping;

use strict;
use base 'Foswiki::UserMapping'; #Foswiki::Users::TopicUserMapping';
use Foswiki::ListIterator ();
use vars qw($isLoadedMapping);

sub new {
  my ($class, $session) = @_;

  my $this = bless($class->SUPER::new($session), $class);

  $this->{authUser} = $session->{loginManager}->{_freetil_user}; #$session->{loginManager}->{_cgisession}->param('FREETIL_USER');
  @{$this->{eachGroupMember}} = @{$session->{loginManager}->{_freetil_groups}}; #split(/,/, $session->{loginManager}->{_cgisession}->param('FREETIL_GROUPS'));
  return $this;
}

sub addUser {
  throw Exception("Please use the FreeTIL user administration tools, not the foswiki ones");
}

sub getLoginName {
  my ($this, $cUID) = @_;
  print "\n\n";
  print $cUID;
  die(1);
  return $cUID;
}

sub getWikiName {
  my ($this, $cUID) = @_;
  print "\n\n";
  print $cUID;
  die(1);
  return $cUID;
}

sub getEmails {
  return ();
}

sub userExists {
  return 1;
}

sub eachUser {
  return new Foswiki::ListIterator(());
}

sub findUserByEmail {
  throw Exception("Not implemented");
}

sub findUserByWikiName {
  my ($this, $wikiName) = @_;
  print "\n\n";
  print $wikiName;
  die(1);
  return ($wikiName);
}

sub login2cUID {
  my ($this, $name, $dontcheck) = @_;
  print "\n\n";
  print $name;
  die(1);
  return $name;
}

sub eachGroupMember {
  my ($this, $groupName, $seen) = @_;

  # print "\n\n";
  # print "GROUP: ", $groupName, "\n";
  # print "GROUPS: ", join(", ", @{$this->{eachGroupMember}}), "\n";
  # print "\n\n";

  if (grep { "$_" eq "$groupName" } @{$this->{eachGroupMember}}) {
    return new Foswiki::ListIterator([$this->{authUser}]);
  }
  return new Foswiki::ListIterator([]);
}

sub isGroup {
    my ($this, $groupName) = @_;
    return grep { "$_" eq "$groupName" } @{$this->{eachGroupMember}};
}

sub eachGroup {
    my ($this) = @_;
    return new Foswiki::ListIterator(@{$this->{eachGroupMember}});
}




sub eachMembership {
  my ($this, $cUID) = @_;

  print "\n\n";
  print "GROUPS: ", $this->{loginManager}->{_cgisession}->param('FREETIL_GROUPS');
  print "\n\n";
  die(1);

  my @groups = $this->getListOfGroups();

  my $it = new Foswiki::ListIterator( \@groups );
  $it->{filter} = sub {
    $this->isInGroup($cUID, $_[0]);
  };

  return $it;
}


1;
