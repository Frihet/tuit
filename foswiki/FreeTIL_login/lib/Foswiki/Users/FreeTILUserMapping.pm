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
# As per the GPL, removal of this notice is prohibited.

package Foswiki::Users::FreeTILUserMapping;

use strict;
use base 'Foswiki::UserMapping'; #Foswiki::Users::TopicUserMapping';
use Foswiki::ListIterator ();
use vars qw($isLoadedMapping);

sub new {
  my ($class, $session) = @_;

  my $this = bless($class->SUPER::new($session), $class);

  $this->{authUser} = $session->{loginManager}->{_freetil_user};
  if ($session->{loginManager}->{_freetil_groups}) {
    @{$this->{eachGroupMember}} = @{$session->{loginManager}->{_freetil_groups}};
  } else {
    @{$this->{eachGroupMember}} = [];
  }
  return $this;
}

sub addUser {
  throw Exception("Please use the FreeTIL user administration tools, not the foswiki ones");
}

sub getLoginName {
  my ($this, $cUID) = @_;
  return $cUID;
}

sub getWikiName {
  my ($this, $cUID) = @_;
  return $cUID;
}

sub getEmails {
  return ();
}

sub userExists {
  return 1;
}

sub eachUser {
  my ($this) = @_;
  return new Foswiki::ListIterator(($this->{authUser}));
}

sub findUserByEmail {
  throw Exception("Not implemented");
}

sub findUserByWikiName {
  my ($this, $wikiName) = @_;
  return ($wikiName);
}

sub login2cUID {
  my ($this, $name, $dontcheck) = @_;
  return $name;
}

sub eachGroupMember {
  my ($this, $groupName, $seen) = @_;

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

  my @groups = $this->getListOfGroups();

  my $it = new Foswiki::ListIterator( \@groups );
  $it->{filter} = sub {
    $this->isInGroup($cUID, $_[0]);
  };

  return $it;
}


1;
