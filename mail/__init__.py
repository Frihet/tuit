# -*- coding: utf-8 -*-
#
# Copyright (c) 2001 Bizar Software Pty Ltd (http://www.bizarsoftware.com.au/)
# This module is free software, and you may redistribute it and/or modify
# under the same terms as Python, so long as this copyright message and
# disclaimer are retained in their original form.
#
# IN NO EVENT SHALL BIZAR SOFTWARE PTY LTD BE LIABLE TO ANY PARTY FOR
# DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING
# OUT OF THE USE OF THIS CODE, EVEN IF THE AUTHOR HAS BEEN ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# BIZAR SOFTWARE PTY LTD SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING,
# BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE.  THE CODE PROVIDED HEREUNDER IS ON AN "AS IS"
# BASIS, AND THERE IS NO OBLIGATION WHATSOEVER TO PROVIDE MAINTENANCE,
# SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
#

"""An e-mail gateway for Roundup. Modified for TUIT.

Incoming messages are examined for multiple parts:
 . In a multipart/mixed message or part, each subpart is extracted and
   examined. The text/plain subparts are assembled to form the textual
   body of the message, to be stored in the file associated with a "msg"
   class node. Any parts of other types are each stored in separate files
   and given "file" class nodes that are linked to the "msg" node.
 . In a multipart/alternative message or part, we look for a text/plain
   subpart and ignore the other parts.

Summary
-------
The "summary" property on message nodes is taken from the first non-quoting
section in the message body. The message body is divided into sections by
blank lines. Sections where the second and all subsequent lines begin with
a ">" or "|" character are considered "quoting sections". The first line of
the first non-quoting section becomes the summary of the message.

Addresses
---------
All of the addresses in the To: and Cc: headers of the incoming message are
looked up among the user nodes, and the corresponding users are placed in
the "recipients" property on the new "msg" node. The address in the From:
header similarly determines the "author" property of the new "msg"
node. The default handling for addresses that don't have corresponding
users is to create new users with no passwords and a username equal to the
address. (The web interface does not permit logins for users with no
passwords.) If we prefer to reject mail from outside sources, we can simply
register an auditor on the "user" class that prevents the creation of user
nodes with no passwords.

Actions
-------
The subject line of the incoming message is examined to determine whether
the message is an attempt to create a new item or to discuss an existing
item. A designator enclosed in square brackets is sought as the first thing
on the subject line (after skipping any "Fwd:" or "Re:" prefixes).

If an item designator (class name and id number) is found there, the newly
created "msg" node is added to the "messages" property for that item, and
any new "file" nodes are added to the "files" property for the item.

If just an item class name is found there, we attempt to create a new item
of that class with its "messages" property initialized to contain the new
"msg" node and its "files" property initialized to contain any new "file"
nodes.

Triggers
--------
Both cases may trigger detectors (in the first case we are calling the
set() method to add the message to the item's spool; in the second case we
are calling the create() method to create a new node). If an auditor raises
an exception, the original message is bounced back to the sender with the
explanatory message given in the exception.

$Id: mailgw.py,v 1.196 2008-07-23 03:04:44 richard Exp $
"""
__docformat__ = 'restructuredtext'

import string, re, os, mimetools, cStringIO, smtplib, socket, binascii, quopri
import time, random, sys, logging
import traceback, rfc822
import cgi
import os 

from email.Header import decode_header
from tuit.ticket.models import *
from tuit.util import email_valid, properties, generate_password
import tuit.scrubber

import email.mime.image
import email.mime.audio
import email.mime.text
import email.mime.message
import email.mime.base
from email import Encoders
import BeautifulSoup

do_send_email=True

def unaliasCharset(charset):
    if charset:
        return charset.lower().replace("windows-", 'cp')
        #return charset_table.get(charset.lower(), charset)
    return None


#from roundup import configuration, hyperdb, date, password, rfc2822, exceptions
#from roundup.mailer import Mailer, MessageSendError
#from roundup.i18n import _

#LOG_FILENAME = '/tmp/tuit.out'
#logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG,)

try:
    import pyme, pyme.core, pyme.gpgme
except ImportError:
    pyme = None

SENDMAILDEBUG = os.environ.get('SENDMAILDEBUG', '')

class MailGWError(ValueError):
    pass

class MailUsageError(ValueError):
    pass

class MailUsageHelp(Exception):
    """ We need to send the help message to the user. """
    pass

class Unauthorized(Exception):
    """ Access denied """
    pass

class IgnoreMessage(Exception):
    """ A general class of message that we should ignore. """
    pass
class IgnoreBulk(IgnoreMessage):
        """ This is email from a mailing list or from a vacation program. """
        pass
class IgnoreLoop(IgnoreMessage):
        """ We've seen this message before... """
        pass

def scrub_html_email(text, cid_mapping={}):

    from BeautifulSoup import BeautifulSoup

    soup = BeautifulSoup(text)

    for tag in soup.findAll(True):
        attrs = dict(tag.attrs)
        if 'src' in attrs:
            src = attrs['src']
            if src[:4]=='cid:':
                tag['src'] = cid_mapping[src[4:]]

    mapped = soup.renderContents()

    scrubber = tuit.scrubber.Scrubber(autolink=False)

    # The scrubber removes complete html documents out of the box? Weird...
    scrubber.disallowed_tags_save_content.add('html')
    scrubber.disallowed_tags_save_content.add('body')
    scrubber.disallowed_tags_save_content.add('xml')
    scrubber.disallowed_tags_save_content.add('doctype')
    scrubber.allowed_attributes.add('color')
    scrubbed = scrubber.scrub(mapped)
    
    return scrubbed

def get_source_list(text):

    from BeautifulSoup import BeautifulSoup

    soup = BeautifulSoup(text)
    sources=[]

    for tag in soup.findAll(True):
        attrs = dict(tag.attrs)
        if 'src' in attrs:
            sources.append(attrs['src'])

    return sources

def remap_sources(text, remap):
#    print 'REMAP'
#    print text
#    print remap

    from BeautifulSoup import BeautifulSoup

    soup = BeautifulSoup(text)

    for tag in soup.findAll(True):
        attrs = dict(tag.attrs)
        if 'src' in attrs:
            src = attrs['src']
            if src in remap:
                tag['src'] = remap[src]

        if 'alt' in attrs:
            del(tag['alt'])



    res = soup.renderContents()
    

#    print res
    return res.replace('/>','>')


def extract_message_id(subject):
    import re
    ids = re.findall(r'#(\d+)\]',subject)
    if not len(ids):
        return None

    try:
        return int(ids[0])
    except:
        return None

def initialiseSecurity(security):
    ''' Create some Permissions and Roles on the security object

        This function is directly invoked by security.Security.__init__()
        as a part of the Security object instantiation.
    '''
    p = security.addPermission(name="Email Access",
        description="User may use the email interface")
    security.addPermissionToRole('Admin', p)

def getparam(str, param):
    ''' From the rfc822 "header" string, extract "param" if it appears.
    '''
    if ';' not in str:
        return None
    str = str[str.index(';'):]
    while str[:1] == ';':
        str = str[1:]
        if ';' in str:
            # XXX Should parse quotes!
            end = str.index(';')
        else:
            end = len(str)
        f = str[:end]
        if '=' in f:
            i = f.index('=')
            if f[:i].strip().lower() == param:
                return rfc822.unquote(f[i+1:].strip())
    return None

def gpgh_key_getall(key, attr):
    ''' return list of given attribute for all uids in
        a key
    '''
    u = key.uids
    while u:
        yield getattr(u, attr)
        u = u.next

def gpgh_sigs(sig):
    ''' more pythonic iteration over GPG signatures '''
    while sig:
        yield sig
        sig = sig.next


def iter_roles(roles):
    ''' handle the text processing of turning the roles list
        into something python can use more easily
    '''
    for role in [x.lower().strip() for x in roles.split(',')]:
        yield role

def user_has_role(db, userid, role_list):
    ''' see if the given user has any roles that appear
        in the role_list
    '''
    for role in iter_roles(db.user.get(userid, 'roles')):
        if role in iter_roles(role_list):
            return True
    return False


def check_pgp_sigs(sig, gpgctx, author):
    ''' Theoretically a PGP message can have several signatures. GPGME
        returns status on all signatures in a linked list. Walk that
        linked list looking for the author's signature
    '''
    for sig in gpgh_sigs(sig):
        key = gpgctx.get_key(sig.fpr, False)
        # we really only care about the signature of the user who
        # submitted the email
        if key and (author in gpgh_key_getall(key, 'email')):
            if sig.summary & pyme.gpgme.GPGME_SIGSUM_VALID:
                return True
            else:
                # try to narrow down the actual problem to give a more useful
                # message in our bounce
                if sig.summary & pyme.gpgme.GPGME_SIGSUM_KEY_MISSING:
                    raise MailUsageError, \
                        _("Message signed with unknown key: %s") % sig.fpr
                elif sig.summary & pyme.gpgme.GPGME_SIGSUM_KEY_EXPIRED:
                    raise MailUsageError, \
                        _("Message signed with an expired key: %s") % sig.fpr
                elif sig.summary & pyme.gpgme.GPGME_SIGSUM_KEY_REVOKED:
                    raise MailUsageError, \
                        _("Message signed with a revoked key: %s") % sig.fpr
                else:
                    raise MailUsageError, \
                        _("Invalid PGP signature detected.")

    # we couldn't find a key belonging to the author of the email
    raise MailUsageError, _("Message signed with unknown key: %s") % sig.fpr



class Mailer:

    @staticmethod
    def send_email(subject, recipient, body_text, body_html, attachments=[]):
      if not do_send_email:
          return
      try:
          
        config = SmtpConfiguration.objects.all()
        if len(config) != 1:
            raise "Could not find exactly one SMTP configuration object"
        config=config[0]
        imapConfig = ImapConfiguration.objects.all()
        if len(imapConfig) == 0:
            raise "Could not find an IMAP configuration object"
        imapConfig=imapConfig[0]
            
        sender = imapConfig.email
        host = config.host
        port = config.port or 25
        username=config.username
        password=config.password
        use_ssl=config.use_ssl
        use_tls=config.use_tls

        # Create the message
        msg = email.mime.multipart.MIMEMultipart('related')
        msg['Subject'] = subject
        msg['From'] = "%s <%s>" % (properties['site_description'],sender)
        msg['To'] = recipient.email
    

        remap = {}

        # Try to make sure that inline images in the message are
        # preserved. To do this, we replace URLs that lead to an
        # attachment with cid:s for that attachment.
        #
        # For some reason, this code doesn't work with Evolution, but
        # after banging my head against whe wall for half a day, I
        # gave up. It is confirmed to work in Thunderbird, Gmail and
        # Outlook web mail.

        attachments_html = []

        # Obtain a list of all links present in the document
        sources = set(get_source_list(body_html))

        for att in attachments:
            mime = att.mime.split('/',1)
            if mime[0] == 'image':
                part = email.mime.image.MIMEImage(att.data, mime[1])
            elif mime[0] == 'audio':                
                part = email.mime.audio.MIMEAudio(att.data, mime[1])
            elif mime[0] == 'text':                
                part = email.mime.text.MIMEText(att.data, mime[1], _charset='UTF-8')
            elif mime[0] == 'message':                
                part = email.mime.message.MIMEMessage(att.data, mime[1])
            else:
                part = email.mime.base.MIMEBase(mime[0], mime[1])
                part.set_payload(att.data)
                Encoders.encode_base64(part)

            # Do we have any links to this attachment? If so, make it
            # an inline attachment, give it a content id, etc.
            if not att.url_internal in sources:
                part.add_header('Content-Disposition', 'attachment', filename=att.name)
            else:
                import time
                #Cids should be globally unique. concatenate
                #attachment id, host name and current time. Should be
                #unique.
                cid = "%d:%f:%s" % (att.id, time.time(), properties['site_url'] )
                part.add_header('Content-Disposition', 'inline', filename=att.name)
                part.add_header('Content-ID', '<%s>' % cid)
                remap[att.url_internal] = 'cid:%s' % cid

            # We attach these _after_ attaching the actual text, seems
            # for some reason to display nicer in some crappy email
            # clients that way...
            attachments_html.append(part)

        # Do the actual url to cid rewriting
        body_html = remap_sources(body_html, remap)

        submsg = email.mime.multipart.MIMEMultipart("alternative")
        if not type(body_html) is str:
            body_html=body_html.encode('utf-8')
        if not type(body_text) is str:
            body_text=body_text.encode('utf-8')
        part1 = email.mime.text.MIMEText(body_text, 'plain', _charset='UTF-8')
        part2 = email.mime.text.MIMEText(body_html, 'html', _charset='UTF-8')
        submsg.attach(part1)
        submsg.attach(part2)
        msg.attach(submsg)

        for i in attachments_html:
            msg.attach(i)

        # Send it
        if use_ssl:
            s = smtplib.SMTP_SSL(host, port)
        else:
            s = smtplib.SMTP(host, port)

        s.helo()

        if use_tls:
            s.starttls()

        if username:
            s.login(username, password)
        
        s.sendmail("", recipient.email, # Empty sender as per http://marc.merlins.org/netrants/autoresponders.txt
                   msg.as_string())
        s.quit()
        logging.getLogger('mail').info('Sent email with subject %s to %s' % (subject, recipient))
      except:
          traceback.print_exc()
          raise
        

    @staticmethod
    def bounce_email():
        pass

    
class Attachment:
    def __init__(self, name, mime_type, body, id):
        self.name=name
        self.body=body
        self.mime_type=mime_type
        self.id=id

class Message(mimetools.Message):
    ''' subclass mimetools.Message so we can retrieve the parts of the
        message...
    '''
    def getpart(self):
        ''' Get a single part of a multipart message and return it as a new
            Message instance.
        '''
        boundary = self.getparam('boundary')
        mid, end = '--'+boundary, '--'+boundary+'--'
        s = cStringIO.StringIO()
        while 1:
            line = self.fp.readline()
            if not line:
                break
            if line.strip() in (mid, end):
                # according to rfc 1431 the preceding line ending is part of
                # the boundary so we need to strip that
                length = s.tell()
                s.seek(-2, 1)
                lineending = s.read(2)
                if lineending == '\r\n':
                    s.truncate(length - 2)
                elif lineending[1] in ('\r', '\n'):
                    s.truncate(length - 1)
                else:
                    raise ValueError('Unknown line ending in message.')
                break
            s.write(line)
        if not s.getvalue().strip():
            return None
        s.seek(0)
        return Message(s)

    def getparts(self):
        """Get all parts of this multipart message."""
        # skip over the intro to the first boundary
        self.fp.seek(0)
        self.getpart()

        # accumulate the other parts
        parts = []
        while 1:
            part = self.getpart()
            if part is None:
                break
            parts.append(part)
        return parts

    @property
    def subject(self):
        return self.getheader('subject') or ""

    def from_address(self, header = 'from'):
        f = self.getheader(header) or None
        if not f:
            return None
        if email_valid(f):
            return f
        m=re.search(r'(.*[^ ])? *<([^\s<>]+@[a-z0-9_.]+)>', f)
        if m:
            return m.groups()[1]

    @property
    def from_name(self):
        f = self.getheader('from') or None
        if not f:
            return None
        if email_valid(f):
            return f
        m=re.search(r'(.*[^ ]) *<([^\s<>]+@[a-z0-9_.]+)>', f)
        if m:
            return m.groups()[0]

    @property
    def from_full(self):
        return self.getheader('from') or None

#    @property
#    def to_address(self):
#        return self.getheader('to') or None

    @property
    def message_id(self):
        return self.getheader('message-id') or None

    @property
    def cc(self):
        return self.getheader('cc') or None
   
    @property
    def bcc(self):
        return self.getheader('bcc') or None

    @property
    def content_id(self):
        return self.getheader('Content-ID').strip(' \n\r\t').lstrip('<').rstrip('>')

    @property
    def is_text(self):
        t = self.getheader('content-type')
        if not t: 
            return False
        t=t.split(';')
        if not len(t):
            return False
        for i in t:
            if i.lower()=='text/plain':
                return True
        return False

    @property
    def is_html(self):
        t = self.getheader('content-type')
        if not t: 
            return False
        t=t.split(';')
        if not len(t):
            return False
        for i in t:
            if i.lower()=='text/html':
                return True
        return False

    @property
    def is_multipart(self):
        t = self.getheader('content-type')
        if not t: 
            return False
        t=t.split(';')
        if not len(t):
            return False
        return t[0].lower()=='text/html'

    @property 
    def body(self):
        return self.getbody()

    def getheader(self, name, default=None):
        hdr = mimetools.Message.getheader(self, name, default)
        if not hdr:
            return ''
        if hdr:
            hdr = hdr.replace('\n','') # Inserted by rfc822.readheaders
        # historically this method has returned utf-8 encoded string
        l = []
        for part, encoding in decode_header(hdr):
            if encoding:
                part = part.decode(encoding)
            l.append(part)
        return ''.join([s.encode('utf-8') for s in l])

    def getaddrlist(self, name):
        # overload to decode the name part of the address
        l = []
        for (name, addr) in mimetools.Message.getaddrlist(self, name):
            p = []
            for part, encoding in decode_header(name):
                if encoding:
                    part = part.decode(encoding)
                p.append(part)
            name = ''.join([s.encode('utf-8') for s in p])
            l.append((name, addr))
        return l

    def getname(self):
        """Find an appropriate name for this message."""
        if self.gettype() == 'message/rfc822':
            # handle message/rfc822 specially - the name should be
            # the subject of the actual e-mail embedded here
            self.fp.seek(0)
            name = Message(self.fp).getheader('subject')
        else:
            # try name on Content-Type
            name = self.getparam('name')
            if not name:
                disp = self.getheader('content-disposition', None)
                if disp:
                    name = getparam(disp, 'filename')

        if name:
            return name.strip()

    def getbody_raw(self):
        """Get the decoded message body."""
        self.rewindbody()
        encoding = self.getencoding()
        data = None
        if encoding == 'base64':
            # BUG: is base64 really used for text encoding or
            # are we inserting zip files here.
            data = binascii.a2b_base64(self.fp.read())
        elif encoding == 'quoted-printable':
            # the quopri module wants to work with files
            decoded = cStringIO.StringIO()
            quopri.decode(self.fp, decoded)
            data = decoded.getvalue()
        elif encoding == 'uuencoded':
            data = binascii.a2b_uu(self.fp.read())
        else:
            # take it as text
            data = self.fp.read()

        return data

    def getbody(self):
        data = self.getbody_raw()
        # Encode message to unicode
        charset = unaliasCharset(self.getparam("charset"))
        if charset:
            # Do conversion only if charset specified - handle
            # badly-specified charsets
            edata = unicode(data, charset, 'replace')#.encode('utf-8')
            # Convert from dos eol to unix
            edata = edata.replace('\r\n', '\n')
        else:
            # Assume default charset 
            edata = unicode(data, properties['default_charset'])#.encode('utf-8')

        return edata

    # General multipart handling:
    #   Take the first text/plain part, anything else is considered an
    #   attachment.
    # multipart/mixed:
    #   Multiple "unrelated" parts.
    # multipart/Alternative (rfc 1521):
    #   Like multipart/mixed, except that we'd only want one of the
    #   alternatives. Generally a top-level part from MUAs sending HTML
    #   mail - there will be a text/plain version.
    # multipart/signed (rfc 1847):
    #   The control information is carried in the second of the two
    #   required body parts.
    #   ACTION: Default, so if content is text/plain we get it.
    # multipart/encrypted (rfc 1847):
    #   The control information is carried in the first of the two
    #   required body parts.
    #   ACTION: Not handleable as the content is encrypted.
    # multipart/related (rfc 1872, 2112, 2387):
    #   The Multipart/Related content-type addresses the MIME
    #   representation of compound objects, usually HTML mail with embedded
    #   images. Usually appears as an alternative.
    #   ACTION: Default, if we must.
    # multipart/report (rfc 1892):
    #   e.g. mail system delivery status reports.
    #   ACTION: Default. Could be ignored or used for Delivery Notification
    #   flagging.
    # multipart/form-data:
    #   For web forms only.

    def extract_content(self, parent_type=None, ignore_alternatives = False):
        """Extract the body and the attachments recursively.

           If the content is hidden inside a multipart/alternative part,
           we use the *last* text/plain part of the *first*
           multipart/alternative in the whole message.
        """
        content_type = self.gettype()
        content = None
        content_out_type = None
        attachments = []

        if content_type == 'text/plain':
            content = self.getbody()
            content_out_type = content_type
        elif content_type == 'text/html':
            content = self.getbody()
            content_out_type = content_type
        elif content_type[:10] == 'multipart/':
            content_found = bool (content)
            ig = ignore_alternatives and not content_found
            for part in self.getparts():
                new_content, new_attach, new_content_out_type = part.extract_content(content_type,
                    not content and ig)

                # If we haven't found a text/plain part yet, take this one,
                # otherwise make it an attachment.
                if not content:
                    content = new_content
                    content_out_type = new_content_out_type
                    cpart   = part
                elif new_content:
                    if content_found or content_type != 'multipart/alternative':
                        attachments.append(part.text_as_attachment())
                    else:
                        # if we have found a text/plain in the current
                        # multipart/alternative and find another one, we
                        # use the first as an attachment (if configured)
                        # and use the second one because rfc 2046, sec.
                        # 5.1.4. specifies that later parts are better
                        # (thanks to Philipp Gortan for pointing this
                        # out)

                        # If we've previously found a text version and
                        # now we've found an alternative html version
                        # of the same document, drop the plain version
                        # like a bad habit.
                        if not (new_content_out_type == 'text/html' and content_out_type == 'text/plain' and content_type == 'multipart/alternative'):
                            attachments.append(cpart.text_as_attachment())
                        content = new_content
                        content_out_type = new_content_out_type
                        cpart   = part

                attachments.extend(new_attach)
            if ig and content_type == 'multipart/alternative' and content:
                attachments = []
        elif (parent_type == 'multipart/signed' and
              content_type == 'application/pgp-signature'):
            # ignore it so it won't be saved as an attachment
            pass
        else:
            attachments.append(self.as_attachment())
        return content, attachments, content_out_type

    def text_as_attachment(self):
        """Return first text/plain part as Message"""
        if not self.gettype().startswith ('multipart/'):
            return self.as_attachment()
        for part in self.getparts():
            content_type = part.gettype()
            if content_type == 'text/plain':
                return part.as_attachment()
            elif content_type.startswith ('multipart/'):
                p = part.text_as_attachment()
                if p:
                    return p
        return None

    def as_attachment(self):
        """Return this message as an attachment."""
        return Attachment(self.getname(), self.gettype(), self.getbody_raw(), self.content_id)

    def pgp_signed(self):
        ''' RFC 3156 requires OpenPGP MIME mail to have the protocol parameter
        '''
        return self.gettype() == 'multipart/signed' \
            and self.typeheader.find('protocol="application/pgp-signature"') != -1

    def pgp_encrypted(self):
        ''' RFC 3156 requires OpenPGP MIME mail to have the protocol parameter
        '''
        return self.gettype() == 'multipart/encrypted' \
            and self.typeheader.find('protocol="application/pgp-encrypted"') != -1

    def decrypt(self, author):
        ''' decrypt an OpenPGP MIME message
            This message must be signed as well as encrypted using the "combined"
            method. The decrypted contents are returned as a new message.
        '''
        (hdr, msg) = self.getparts()
        # According to the RFC 3156 encrypted mail must have exactly two parts.
        # The first part contains the control information. Let's verify that
        # the message meets the RFC before we try to decrypt it.
        if hdr.getbody() != 'Version: 1' or hdr.gettype() != 'application/pgp-encrypted':
            raise MailUsageError, \
                _("Unknown multipart/encrypted version.")

        context = pyme.core.Context()
        ciphertext = pyme.core.Data(msg.getbody())
        plaintext = pyme.core.Data()

        result = context.op_decrypt_verify(ciphertext, plaintext)

        if result:
            raise MailUsageError, _("Unable to decrypt your message.")

        # we've decrypted it but that just means they used our public
        # key to send it to us. now check the signatures to see if it
        # was signed by someone we trust
        result = context.op_verify_result()
        check_pgp_sigs(result.signatures, context, author)

        plaintext.seek(0,0)
        # pyme.core.Data implements a seek method with a different signature
        # than roundup can handle. So we'll put the data in a container that
        # the Message class can work with.
        c = cStringIO.StringIO()
        c.write(plaintext.read())
        c.seek(0)
        return Message(c)

    def verify_signature(self, author):
        ''' verify the signature of an OpenPGP MIME message
            This only handles detached signatures. Old style
            PGP mail (i.e. '-----BEGIN PGP SIGNED MESSAGE----')
            is archaic and not supported :)
        '''
        # we don't check the micalg parameter...gpgme seems to
        # figure things out on its own
        (msg, sig) = self.getparts()

        if sig.gettype() != 'application/pgp-signature':
            raise MailUsageError, \
                _("No PGP signature found in message.")

        context = pyme.core.Context()
        # msg.getbody() is skipping over some headers that are
        # required to be present for verification to succeed so
        # we'll do this by hand
        msg.fp.seek(0)
        # according to rfc 3156 the data "MUST first be converted
        # to its content-type specific canonical form. For
        # text/plain this means conversion to an appropriate
        # character set and conversion of line endings to the
        # canonical <CR><LF> sequence."
        # TODO: what about character set conversion?
        canonical_msg = re.sub('(?<!\r)\n', '\r\n', msg.fp.read())
        msg_data = pyme.core.Data(canonical_msg)
        sig_data = pyme.core.Data(sig.getbody())

        context.op_verify(sig_data, msg_data, None)

        # check all signatures for validity
        result = context.op_verify_result()
        check_pgp_sigs(result.signatures, context, author)

class MailGW:

    def __init__(self, instance, arguments=()):
#        self.instance = instance
#        self.arguments = arguments
#        self.default_class = None
#        for option, value in self.arguments:
#            if option == '-c':
#                self.default_class = value.strip()

#        self.mailer = Mailer(instance.config)
        self.logger = logging.getLogger('mail')

        # should we trap exceptions (normal usage) or pass them through
        # (for testing)
        self.trapExceptions = 1

    def do_work(self):
        from tuit.ticket.models import ImapConfiguration
        imapConfigs = ImapConfiguration.objects.all()
        for imapConfig in imapConfigs:
            self.do_imap(imapConfig.host, imapConfig.username, imapConfig.password, imapConfig.mailbox, imapConfig.use_ssl)

    def do_pipe(self):
        """ Read a message from standard input and pass it to the mail handler.

            Read into an internal structure that we can seek on (in case
            there's an error).

            XXX: we may want to read this into a temporary file instead...
        """
        s = cStringIO.StringIO()
        s.write(sys.stdin.read())
        s.seek(0)
        self.main(s)
        return 0

    def do_mailbox(self, filename):
        """ Read a series of messages from the specified unix mailbox file and
            pass each to the mail handler.
        """
        # open the spool file and lock it
        import fcntl
        # FCNTL is deprecated in py2.3 and fcntl takes over all the symbols
        if hasattr(fcntl, 'LOCK_EX'):
            FCNTL = fcntl
        else:
            import FCNTL
        f = open(filename, 'r+')
        fcntl.flock(f.fileno(), FCNTL.LOCK_EX)

        # handle and clear the mailbox
        try:
            from mailbox import UnixMailbox
            mailbox = UnixMailbox(f, factory=Message)
            # grab one message
            message = mailbox.next()
            while message:
                # handle this message
                self.handle_Message(message)
                message = mailbox.next()
            # nuke the file contents
            os.ftruncate(f.fileno(), 0)
        except:
            import traceback
            traceback.print_exc()
            return 1
        fcntl.flock(f.fileno(), FCNTL.LOCK_UN)
        return 0

    def do_imap(self, host, user='', password='', mailbox='', ssl=0):
        ''' Do an IMAP connection
        '''
        import getpass, imaplib, socket
#        try:
#            if not user:
#                user = raw_input('User: ')
#            if not password:
#                password = getpass.getpass()
#        except (KeyboardInterrupt, EOFError):
            # Ctrl C or D maybe also Ctrl Z under Windows.
 #           print "\nAborted by user."
 #           return 1
        # open a connection to the server and retrieve all messages
        try:
            if ssl:
                server = imaplib.IMAP4_SSL(host)
            else:
                server = imaplib.IMAP4(host)
        except (imaplib.IMAP4.error, socket.error, socket.sslerror):
            import traceback as tb
            msg = tb.format_exc()
            self.logger.error('IMAP server error on host %s: %s'% (host,msg))
            return 1

        try:
            server.login(user, password)
        except imaplib.IMAP4.error, e:
            self.logger.exception('IMAP login failure')
            return 1
        except socket.sslerror, e:
            self.logger.exception('SSL error while performing login')
            return 1
#        self.logger.debug('Login done')

        try:
            
            if not mailbox:
                (typ, data) = server.select()
            else:
                (typ, data) = server.select(mailbox=mailbox)
            if typ != 'OK':
                self.logger.error('Failed to get mailbox %r: %s'%(mailbox,
                    data))
                return 1
            try:
                numMessages = int(data[0])
            except ValueError, value:
                self.logger.error('Invalid message count from mailbox %r'%
                    data[0])
                return 1

            for i in range(1, min(2,numMessages+1)):
                (typ, data) = server.fetch(str(i), '(RFC822)')
                s = cStringIO.StringIO(data[0][1])
                s.seek(0)
                
                m = Message(s)

                if m.from_address('from') != m.from_address('return-path') and not (m.from_address('return-path') == None) :
                    logging.getLogger('mail/loop').error('Possible mail loop: from address (%s) != return path (%s)' % (m.from_address('from'), m.from_address('return-path')))                
                    message_status = 'mail_loop'
                else:
                    try:
                        message_status = self.process_message(m)
                    except:
                        try:
                            self.logger.error(traceback.format_exc())
                        except:
                            pass
                        print traceback.format_exc()
                        message_status='unknown_error'
                if message_status is None:
                    message_status='error_bad_status'

                # copy the message and mark it as deleted.
                print "Processed message, got status", message_status
                box_name = message_status
                # Don't check return status - if we failed, either it
                # means the directory existed, or the next operation
                # will fail and we'll handle that.
                (typ, data) = server.create('Inbox.' + box_name)

                (copy_type, copy_data) = server.copy(str(i), 'Inbox.' + box_name)
                if copy_type == 'OK':
                    server.store(str(i), '+FLAGS', r'(\Deleted)')
                else:
                    try:
                        self.logger.error('failed to copy message to %s-folder' % box_name)
                    except:
                        pass
                    print 'failed to copy message to %s-folder' % box_name

            server.close()
            if numMessages > 0:
                self.logger.info('Processed %d message(s)' % numMessages)
        finally:
            try:
#                server.expunge()
                pass
            except:
                pass
            server.logout()

        return 0

    def create_issue(self, message):
        subject = message.subject
        (content, attachments, content_type) = message.extract_content()
        if subject == "":
            subject = _("Unnamed issue")
        elif len(subject) > 250:
            if content_type == 'text/html':
                content = cgi.escape(subject).decode('utf-8') + "<br>" + content
            else:
                content = subject + "\n" + content
            
            #~ This try/except block is needed because sometimes cutof can be made in the middle of unicode char, 
            #~ and that will in return raise unexpected end of data error
            try: 
                subject = subject[0:250].decode('utf-8')
            except:
                subject = subject[0:249].decode('utf-8')
        else:
            subject = subject.decode('utf-8')

        impact = properties['issue_default_impact']
        urgency = properties['issue_default_urgency']
        email = message.from_address()
        if email == None:
            email = 'Unknown'
        u = User.objects.filter(email=email.lower())
        if len(u) == 0:
            if (True):
                first_name = message.from_name
                last_name = ''
                if first_name == None:
                    first_name = 'Unknown'
                if ' ' in first_name:
                    first_name, last_name = first_name.split(' ', 1)
                u = [User.objects.create_user(email.replace('@', '_').replace('.', '_'), email, '')]
                u[0].first_name = first_name
                u[0].last_name = last_name
                u[0].set_password(generate_password())
                u[0].save()
            else:
                self.logger.error('Unknown user: %s'% message.from_address())
                return 'unmatched_user'
        
        user=u[0]
        
        i = Issue()
        i.creator = user
        
        type = IssueType.objects.get(id=properties['issue_default_type'])
        category = properties['issue_default_category']
        status = properties['issue_default_status']


        data = dict(current_status_string=str(status),
                    assigned_to_string=None,
                    requester_string=user.username,
                    subject = subject,
                    description='...',
                    impact_string = str(impact),
                    urgency_string = str(urgency),
                    category_string=str(category),
                    ci_string="",
                    )

        i.creator=user
        i.type = type

        events = i.apply_post(data)

        i.create_description='[]'
        err = i.validate()
        if len(err):
            self.logger.error('Validation error while saving new issue: %s' % err)
            return 'save_error'
        try:
            i.save()
            events.extend(i.apply_post(data))

            attachment_mapping = {}
            for (idx,attachment) in enumerate(attachments):
                if not attachment.name:
                    attachment.name = "unnamed"

                try:
                    ia = IssueAttachment.create(i, None, attachment.body, attachment.name, attachment.mime_type, idx)
                    attachment_mapping[attachment.id] = ia.url_internal
                except:
                    logging.getLogger('mail').error('Could not save attachment %s of issue %d' % (attachment.name, i.id))
            
            if content_type == 'text/html':
                i.description = scrub_html_email(content, attachment_mapping)
            else:
                i.description = ("<pre>" + cgi.escape(content) + "</pre>")
                
            e=EmailTemplate.objects.filter(name='mail_create')
            if len(e) > 0:
                e=e[0]
                events.extend(e.send(properties['mail_create_mail'], issue=i, update=None))

            i.description_data={'update_type':'email','events':events}
            Event.fire(['mail_create'], i)

            i.save()
#            print 'created issue ', i.id
        except:
            import traceback as tb
            msg = tb.format_exc()
            self.logger.error('Unknown error while saving new issue: %s' % msg)
            return 'save_error'

        self.logger.info('Created issue with id %d' % i.id)
        return 'new_issue'


    def process_message(self, message):
        (content, attachments, content_type) = message.extract_content()
        #print 'Processing message', message.subject
        id = extract_message_id(message.subject)

        if id is None:
            return self.create_issue(message)

        try:
            i = Issue.objects.get(id=id)
        except:
            self.logger.error("Recived email with subject %s, extracted issue id %d, but no such issue could be found. Treating the message as a new issue.")
            return self.create_issue(message)
        user = None
        contact = None
        try:
            u = User.objects.filter(email=message.from_address())
            if len(u) == 0:
                contact = make_contact(message.from_full)
            else:
                user=u[0]
        except Exception, e:
            self.logger.error("Recived email from %s, but user is unknown" % message.from_address())
            return 'unmatched_user'

        iu = IssueUpdate(issue=i,
                         internal=False,
                         comment = '...',
                         user = user,
                         contact = contact)

        iu.description_data={}
        iu.save();

        attachment_mapping = {}

        for (idx,attachment) in enumerate(attachments):
            if not attachment.name:
                attachment.name = "unnamed"
            try:
                ia = IssueAttachment.create(i, iu, attachment.body, attachment.name, attachment.mime_type, idx)
                attachment_mapping[attachment.id] = ia.url_internal
            except:
                logging.getLogger('mail').error('Could not save attachment %s of issue update %d.\n%s' % (attachment.name, iu.id, traceback.format_exc()))

#name
            #body 
            #mime_type

        if content_type == 'text/html':
            comment = scrub_html_email(content, attachment_mapping)
        else:
            comment = ("<pre>" + cgi.escape(content) + "</pre>")

        iu.comment = comment

        events=[]
        e=EmailTemplate.objects.filter(name='mail_update')
        if len(e) > 0:
            e=e[0]
            events.extend(e.send(properties['mail_update_mail'], issue=i, update=iu))
#        print 'Emails sent'

        iu.description_data={'type':'email','events':events}
#        print 'Description updated'

        Event.fire(['mail_update','update'], i, iu)

#        print 'events fired'

        i.save()
        iu.save()

        return 'ok'

    def do_apop(self, server, user='', password='', ssl=False):
        ''' Do authentication POP
        '''
        self._do_pop(server, user, password, True, ssl)

    def do_pop(self, server, user='', password='', ssl=False):
        ''' Do plain POP
        '''
        self._do_pop(server, user, password, False, ssl)

    def _do_pop(self, server, user, password, apop, ssl):
        '''Read a series of messages from the specified POP server.
        '''
        import getpass, poplib, socket
        try:
            if not user:
                user = raw_input('User: ')
            if not password:
                password = getpass.getpass()
        except (KeyboardInterrupt, EOFError):
            # Ctrl C or D maybe also Ctrl Z under Windows.
            print "\nAborted by user."
            return 1

        # open a connection to the server and retrieve all messages
        try:
            if ssl:
                klass = poplib.POP3_SSL
            else:
                klass = poplib.POP3
            server = klass(server)
        except socket.error:
            self.logger.exception('POP server error')
            return 1
        if apop:
            server.apop(user, password)
        else:
            server.user(user)
            server.pass_(password)
        numMessages = len(server.list()[1])
        for i in range(1, numMessages+1):
            # retr: returns
            # [ pop response e.g. '+OK 459 octets',
            #   [ array of message lines ],
            #   number of octets ]
            lines = server.retr(i)[1]
            s = cStringIO.StringIO('\n'.join(lines))
            s.seek(0)
            self.handle_Message(Message(s))
            # delete the message
            server.dele(i)

        # quit the server to commit changes.
        server.quit()
        return 0

    def main(self, fp):
        ''' fp - the file from which to read the Message.
        '''
        return self.handle_Message(Message(fp))

    def handle_Message(self, message):
        """Handle an RFC822 Message

        Handle the Message object by calling handle_message() and then cope
        with any errors raised by handle_message.
        This method's job is to make that call and handle any
        errors in a sane manner. It should be replaced if you wish to
        handle errors in a different manner.
        """
        # in some rare cases, a particularly stuffed-up e-mail will make
        # its way into here... try to handle it gracefully

        sendto = message.getaddrlist('resent-from')
        if not sendto:
            sendto = message.getaddrlist('from')
        if not sendto:
            # very bad-looking message - we don't even know who sent it
            msg = ['Badly formed message from mail gateway. Headers:']
            msg.extend(message.headers)
            msg = '\n'.join(map(str, msg))
            self.logger.error(msg)
            return

        msg = 'Handling message'
        if message.getheader('message-id'):
            msg += ' (Message-id=%r)'%message.getheader('message-id')
        self.logger.info(msg)

        # try normal message-handling
        if not self.trapExceptions:
            return self.handle_message(message)

        # no, we want to trap exceptions
        try:
            return self.handle_message(message)
        except MailUsageHelp:
            # bounce the message back to the sender with the usage message
            fulldoc = '\n'.join(string.split(__doc__, '\n')[2:])
            m = ['']
            m.append('\n\nMail Gateway Help\n=================')
            m.append(fulldoc)
            self.mailer.bounce_message(message, [sendto[0][1]], m,
                subject="Mail Gateway Help")
        except MailUsageError, value:
            # bounce the message back to the sender with the usage message
            fulldoc = '\n'.join(string.split(__doc__, '\n')[2:])
            m = ['']
            m.append(str(value))
            m.append('\n\nMail Gateway Help\n=================')
            m.append(fulldoc)
            self.mailer.bounce_message(message, [sendto[0][1]], m)
        except Unauthorized, value:
            # just inform the user that he is not authorized
            m = ['']
            m.append(str(value))
            self.mailer.bounce_message(message, [sendto[0][1]], m)
        except IgnoreMessage:
            # do not take any action
            # this exception is thrown when email should be ignored
            msg = 'IgnoreMessage raised'
            if message.getheader('message-id'):
                msg += ' (Message-id=%r)'%message.getheader('message-id')
            self.logger.info(msg)
            return
        except:
            msg = 'Exception handling message'
            if message.getheader('message-id'):
                msg += ' (Message-id=%r)'%message.getheader('message-id')
            self.logger.exception(msg)

            # bounce the message back to the sender with the error message
            # let the admin know that something very bad is happening
            m = ['']
            m.append('An unexpected error occurred during the processing')
            m.append('of your message. The tracker administrator is being')
            m.append('notified.\n')
            self.mailer.bounce_message(message, [sendto[0][1]], m)

            m.append('----------------')
            m.append(traceback.format_exc())
            self.mailer.bounce_message(message, [self.instance.config.ADMIN_EMAIL], m)

    def handle_message(self, message):
        ''' message - a Message instance

        Parse the message as per the module docstring.
        '''
        # get database handle for handling one email
        self.db = self.instance.open ('admin')
        try:
            return self._handle_message (message)
        finally:
            self.db.close()

    def _handle_message(self, message):
        ''' message - a Message instance

        Parse the message as per the module docstring.

        The implementation expects an opened database and a try/finally
        that closes the database.
        '''
        # detect loops
        if message.getheader('x-roundup-loop', ''):
            raise IgnoreLoop

        # handle the subject line
        subject = message.getheader('subject', '')
        if not subject:
            raise MailUsageError, _("""
Emails to Roundup trackers must include a Subject: line!
""")

        # detect Precedence: Bulk, or Microsoft Outlook autoreplies
        if (message.getheader('precedence', '') == 'bulk'
                or subject.lower().find("autoreply") > 0):
            raise IgnoreBulk

        if subject.strip().lower() == 'help':
            raise MailUsageHelp

        # config is used many times in this method.
        # make local variable for easier access
        config = self.instance.config

        # determine the sender's address
        from_list = message.getaddrlist('resent-from')
        if not from_list:
            from_list = message.getaddrlist('from')

        # XXX Don't enable. This doesn't work yet.
#  "[^A-z.]tracker\+(?P<classname>[^\d\s]+)(?P<nodeid>\d+)\@some.dom.ain[^A-z.]"
        # handle delivery to addresses like:tracker+issue25@some.dom.ain
        # use the embedded issue number as our issue
#        issue_re = config['MAILGW_ISSUE_ADDRESS_RE']
#        if issue_re:
#            for header in ['to', 'cc', 'bcc']:
#                addresses = message.getheader(header, '')
#            if addresses:
#              # FIXME, this only finds the first match in the addresses.
#                issue = re.search(issue_re, addresses, 'i')
#                if issue:
#                    classname = issue.group('classname')
#                    nodeid = issue.group('nodeid')
#                    break

        # Matches subjects like:
        # Re: "[issue1234] title of issue [status=resolved]"

        # Alias since we need a reference to the original subject for
        # later use in error messages
        tmpsubject = subject

        sd_open, sd_close = config['MAILGW_SUBJECT_SUFFIX_DELIMITERS']
        delim_open = re.escape(sd_open)
        if delim_open in '[(': delim_open = '\\' + delim_open
        delim_close = re.escape(sd_close)
        if delim_close in '[(': delim_close = '\\' + delim_close

        matches = dict.fromkeys(['refwd', 'quote', 'classname',
                                 'nodeid', 'title', 'args',
                                 'argswhole'])

        # Look for Re: et. al. Used later on for MAILGW_SUBJECT_CONTENT_MATCH
        re_re = r"(?P<refwd>%s)\s*" % config["MAILGW_REFWD_RE"].pattern
        m = re.match(re_re, tmpsubject, re.IGNORECASE|re.VERBOSE|re.UNICODE)
        if m:
            m = m.groupdict()
            if m['refwd']:
                matches.update(m)
                tmpsubject = tmpsubject[len(m['refwd']):] # Consume Re:

        # Look for Leading "
        m = re.match(r'(?P<quote>\s*")', tmpsubject,
                     re.IGNORECASE)
        if m:
            matches.update(m.groupdict())
            tmpsubject = tmpsubject[len(matches['quote']):] # Consume quote

        has_prefix = re.search(r'^%s(\w+)%s'%(delim_open,
            delim_close), tmpsubject.strip())

        class_re = r'%s(?P<classname>(%s))(?P<nodeid>\d+)?%s'%(delim_open,
            "|".join(self.db.getclasses()), delim_close)
        # Note: re.search, not re.match as there might be garbage
        # (mailing list prefix, etc.) before the class identifier
        m = re.search(class_re, tmpsubject, re.IGNORECASE)
        if m:
            matches.update(m.groupdict())
            # Skip to the end of the class identifier, including any
            # garbage before it.

            tmpsubject = tmpsubject[m.end():]

        # if we've not found a valid classname prefix then force the
        # scanning to handle there being a leading delimiter
        title_re = r'(?P<title>%s[^%s]+)'%(
            not matches['classname'] and '.' or '', delim_open)
        m = re.match(title_re, tmpsubject.strip(), re.IGNORECASE)
        if m:
            matches.update(m.groupdict())
            tmpsubject = tmpsubject[len(matches['title']):] # Consume title

        args_re = r'(?P<argswhole>%s(?P<args>.+?)%s)?'%(delim_open,
            delim_close)
        m = re.search(args_re, tmpsubject.strip(), re.IGNORECASE|re.VERBOSE)
        if m:
            matches.update(m.groupdict())

        # figure subject line parsing modes
        pfxmode = config['MAILGW_SUBJECT_PREFIX_PARSING']
        sfxmode = config['MAILGW_SUBJECT_SUFFIX_PARSING']

        # check for registration OTK
        # or fallback on the default class
        if self.db.config['EMAIL_REGISTRATION_CONFIRMATION']:
            otk_re = re.compile('-- key (?P<otk>[a-zA-Z0-9]{32})')
            otk = otk_re.search(matches['title'] or '')
            if otk:
                self.db.confirm_registration(otk.group('otk'))
                subject = 'Your registration to %s is complete' % \
                          config['TRACKER_NAME']
                sendto = [from_list[0][1]]
                self.mailer.standard_message(sendto, subject, '')
                return

        # get the classname
        if pfxmode == 'none':
            classname = None
        else:
            classname = matches['classname']

        if not classname and has_prefix and pfxmode == 'strict':
            raise MailUsageError, _("""
The message you sent to roundup did not contain a properly formed subject
line. The subject must contain a class name or designator to indicate the
'topic' of the message. For example:
    Subject: [issue] This is a new issue
      - this will create a new issue in the tracker with the title 'This is
        a new issue'.
    Subject: [issue1234] This is a followup to issue 1234
      - this will append the message's contents to the existing issue 1234
        in the tracker.

Subject was: '%(subject)s'
""") % locals()

        # try to get the class specified - if "loose" or "none" then fall
        # back on the default
        attempts = []
        if classname:
            attempts.append(classname)

        if self.default_class:
            attempts.append(self.default_class)
        else:
            attempts.append(config['MAILGW_DEFAULT_CLASS'])

        # first valid class name wins
        cl = None
        for trycl in attempts:
            try:
                cl = self.db.getclass(trycl)
                classname = trycl
                break
            except KeyError:
                pass

        if not cl:
            validname = ', '.join(self.db.getclasses())
            if classname:
                raise MailUsageError, _("""
The class name you identified in the subject line ("%(classname)s") does
not exist in the database.

Valid class names are: %(validname)s
Subject was: "%(subject)s"
""") % locals()
            else:
                raise MailUsageError, _("""
You did not identify a class name in the subject line and there is no
default set for this tracker. The subject must contain a class name or
designator to indicate the 'topic' of the message. For example:
    Subject: [issue] This is a new issue
      - this will create a new issue in the tracker with the title 'This is
        a new issue'.
    Subject: [issue1234] This is a followup to issue 1234
      - this will append the message's contents to the existing issue 1234
        in the tracker.

Subject was: '%(subject)s'
""") % locals()

        # get the optional nodeid
        if pfxmode == 'none':
            nodeid = None
        else:
            nodeid = matches['nodeid']

        # try in-reply-to to match the message if there's no nodeid
        inreplyto = message.getheader('in-reply-to') or ''
        if nodeid is None and inreplyto:
            l = self.db.getclass('msg').stringFind(messageid=inreplyto)
            if l:
                nodeid = cl.filter(None, {'messages':l})[0]

        # title is optional too
        title = matches['title']
        if title:
            title = title.strip()
        else:
            title = ''

        # strip off the quotes that dumb emailers put around the subject, like
        #      Re: "[issue1] bla blah"
        if matches['quote'] and title.endswith('"'):
            title = title[:-1]

        # but we do need either a title or a nodeid...
        if nodeid is None and not title:
            raise MailUsageError, _("""
I cannot match your message to a node in the database - you need to either
supply a full designator (with number, eg "[issue123]") or keep the
previous subject title intact so I can match that.

Subject was: "%(subject)s"
""") % locals()

        # If there's no nodeid, check to see if this is a followup and
        # maybe someone's responded to the initial mail that created an
        # entry. Try to find the matching nodes with the same title, and
        # use the _last_ one matched (since that'll _usually_ be the most
        # recent...). The subject_content_match config may specify an
        # additional restriction based on the matched node's creation or
        # activity.
        tmatch_mode = config['MAILGW_SUBJECT_CONTENT_MATCH']
        if tmatch_mode != 'never' and nodeid is None and matches['refwd']:
            l = cl.stringFind(title=title)
            limit = None
            if (tmatch_mode.startswith('creation') or
                    tmatch_mode.startswith('activity')):
                limit, interval = tmatch_mode.split(' ', 1)
                threshold = date.Date('.') - date.Interval(interval)
            for id in l:
                if limit:
                    if threshold < cl.get(id, limit):
                        nodeid = id
                else:
                    nodeid = id

        # if a nodeid was specified, make sure it's valid
        if nodeid is not None and not cl.hasnode(nodeid):
            if pfxmode == 'strict':
                raise MailUsageError, _("""
The node specified by the designator in the subject of your message
("%(nodeid)s") does not exist.

Subject was: "%(subject)s"
""") % locals()
            else:
                title = subject
                nodeid = None

        # Handle the arguments specified by the email gateway command line.
        # We do this by looping over the list of self.arguments looking for
        # a -C to tell us what class then the -S setting string.
        msg_props = {}
        user_props = {}
        file_props = {}
        issue_props = {}
        # so, if we have any arguments, use them
        if self.arguments:
            current_class = 'msg'
            for option, propstring in self.arguments:
                if option in ( '-C', '--class'):
                    current_class = propstring.strip()
                    # XXX this is not flexible enough.
                    #   we should chect for subclasses of these classes,
                    #   not for the class name...
                    if current_class not in ('msg', 'file', 'user', 'issue'):
                        mailadmin = config['ADMIN_EMAIL']
                        raise MailUsageError, _("""
The mail gateway is not properly set up. Please contact
%(mailadmin)s and have them fix the incorrect class specified as:
  %(current_class)s
""") % locals()
                if option in ('-S', '--set'):
                    if current_class == 'issue' :
                        errors, issue_props = setPropArrayFromString(self,
                            cl, propstring.strip(), nodeid)
                    elif current_class == 'file' :
                        temp_cl = self.db.getclass('file')
                        errors, file_props = setPropArrayFromString(self,
                            temp_cl, propstring.strip())
                    elif current_class == 'msg' :
                        temp_cl = self.db.getclass('msg')
                        errors, msg_props = setPropArrayFromString(self,
                            temp_cl, propstring.strip())
                    elif current_class == 'user' :
                        temp_cl = self.db.getclass('user')
                        errors, user_props = setPropArrayFromString(self,
                            temp_cl, propstring.strip())
                    if errors:
                        mailadmin = config['ADMIN_EMAIL']
                        raise MailUsageError, _("""
The mail gateway is not properly set up. Please contact
%(mailadmin)s and have them fix the incorrect properties:
  %(errors)s
""") % locals()

        #
        # handle the users
        #
        # Don't create users if anonymous isn't allowed to register
        create = 1
        anonid = self.db.user.lookup('anonymous')
        if not (self.db.security.hasPermission('Create', anonid, 'user')
                and self.db.security.hasPermission('Email Access', anonid)):
            create = 0

        # ok, now figure out who the author is - create a new user if the
        # "create" flag is true
        author = uidFromAddress(self.db, from_list[0], create=create)

        # if we're not recognised, and we don't get added as a user, then we
        # must be anonymous
        if not author:
            author = anonid

        # make sure the author has permission to use the email interface
        if not self.db.security.hasPermission('Email Access', author):
            if author == anonid:
                # we're anonymous and we need to be a registered user
                from_address = from_list[0][1]
                registration_info = ""
                if self.db.security.hasPermission('Web Access', author) and \
                   self.db.security.hasPermission('Create', anonid, 'user'):
                    tracker_web = self.instance.config.TRACKER_WEB
                    registration_info = """ Please register at:

%(tracker_web)suser?template=register

...before sending mail to the tracker.""" % locals()

                raise Unauthorized, _("""
You are not a registered user.%(registration_info)s

Unknown address: %(from_address)s
""") % locals()
            else:
                # we're registered and we're _still_ not allowed access
                raise Unauthorized, _(
                    'You are not permitted to access this tracker.')

        # make sure they're allowed to edit or create this class of information
        if nodeid:
            if not self.db.security.hasPermission('Edit', author, classname,
                    itemid=nodeid):
                raise Unauthorized, _(
                    'You are not permitted to edit %(classname)s.') % locals()
        else:
            if not self.db.security.hasPermission('Create', author, classname):
                raise Unauthorized, _(
                    'You are not permitted to create %(classname)s.'
                    ) % locals()

        # the author may have been created - make sure the change is
        # committed before we reopen the database
        self.db.commit()

        # set the database user as the author
        username = self.db.user.get(author, 'username')
        self.db.setCurrentUser(username)

        # re-get the class with the new database connection
        cl = self.db.getclass(classname)

        # now update the recipients list
        recipients = []
        tracker_email = config['TRACKER_EMAIL'].lower()
        for recipient in message.getaddrlist('to') + message.getaddrlist('cc'):
            r = recipient[1].strip().lower()
            if r == tracker_email or not r:
                continue

            # look up the recipient - create if necessary (and we're
            # allowed to)
            recipient = uidFromAddress(self.db, recipient, create, **user_props)

            # if all's well, add the recipient to the list
            if recipient:
                recipients.append(recipient)

        #
        # handle the subject argument list
        #
        # figure what the properties of this Class are
        properties = cl.getprops()
        props = {}
        args = matches['args']
        argswhole = matches['argswhole']
        if args:
            if sfxmode == 'none':
                title += ' ' + argswhole
            else:
                errors, props = setPropArrayFromString(self, cl, args, nodeid)
                # handle any errors parsing the argument list
                if errors:
                    if sfxmode == 'strict':
                        errors = '\n- '.join(map(str, errors))
                        raise MailUsageError, _("""
There were problems handling your subject line argument list:
- %(errors)s

Subject was: "%(subject)s"
""") % locals()
                    else:
                        title += ' ' + argswhole


        # set the issue title to the subject
        title = title.strip()
        if (title and properties.has_key('title') and not
                issue_props.has_key('title')):
            issue_props['title'] = title

        #
        # handle message-id and in-reply-to
        #
        messageid = message.getheader('message-id')
        # generate a messageid if there isn't one
        if not messageid:
            messageid = "<%s.%s.%s%s@%s>"%(time.time(), random.random(),
                classname, nodeid, config['MAIL_DOMAIN'])

        # if they've enabled PGP processing then verify the signature
        # or decrypt the message

        # if PGP_ROLES is specified the user must have a Role in the list
        # or we will skip PGP processing
        def pgp_role():
            if self.instance.config.PGP_ROLES:
                return user_has_role(self.db, author,
                    self.instance.config.PGP_ROLES)
            else:
                return True

        if self.instance.config.PGP_ENABLE and pgp_role():
            assert pyme, 'pyme is not installed'
            # signed/encrypted mail must come from the primary address
            author_address = self.db.user.get(author, 'address')
            if self.instance.config.PGP_HOMEDIR:
                os.environ['GNUPGHOME'] = self.instance.config.PGP_HOMEDIR
            if message.pgp_signed():
                message.verify_signature(author_address)
            elif message.pgp_encrypted():
                # replace message with the contents of the decrypted
                # message for content extraction
                # TODO: encrypted message handling is far from perfect
                # bounces probably include the decrypted message, for
                # instance :(
                message = message.decrypt(author_address)
            else:
                raise MailUsageError, _("""
This tracker has been configured to require all email be PGP signed or
encrypted.""")
        # now handle the body - find the message
        ig = self.instance.config.MAILGW_IGNORE_ALTERNATIVES
        content, attachments = message.extract_content(ignore_alternatives = ig)
        if content is None:
            raise MailUsageError, _("""
Roundup requires the submission to be plain text. The message parser could
not find a text/plain part to use.
""")

        # parse the body of the message, stripping out bits as appropriate
        summary, content = parseContent(content, config=config)
        content = content.strip()

        #
        # handle the attachments
        #
        if properties.has_key('files'):
            files = []
            for (name, mime_type, data) in attachments:
                if not self.db.security.hasPermission('Create', author, 'file'):
                    raise Unauthorized, _(
                        'You are not permitted to create files.')
                if not name:
                    name = "unnamed"
                try:
                    fileid = self.db.file.create(type=mime_type, name=name,
                         content=data, **file_props)
                except exceptions.Reject:
                    pass
                else:
                    files.append(fileid)
            # attach the files to the issue
            if not self.db.security.hasPermission('Edit', author,
                    classname, 'files'):
                raise Unauthorized, _(
                    'You are not permitted to add files to %(classname)s.'
                    ) % locals()

            if nodeid:
                # extend the existing files list
                fileprop = cl.get(nodeid, 'files')
                fileprop.extend(files)
                props['files'] = fileprop
            else:
                # pre-load the files list
                props['files'] = files

        #
        # create the message if there's a message body (content)
        #
        if (content and properties.has_key('messages')):
            if not self.db.security.hasPermission('Create', author, 'msg'):
                raise Unauthorized, _(
                    'You are not permitted to create messages.')

            try:
                message_id = self.db.msg.create(author=author,
                    recipients=recipients, date=date.Date('.'),
                    summary=summary, content=content, files=files,
                    messageid=messageid, inreplyto=inreplyto, **msg_props)
            except exceptions.Reject, error:
                raise MailUsageError, _("""
Mail message was rejected by a detector.
%(error)s
""") % locals()
            # attach the message to the node
            if not self.db.security.hasPermission('Edit', author,
                    classname, 'messages'):
                raise Unauthorized, _(
                    'You are not permitted to add messages to %(classname)s.'
                    ) % locals()

            if nodeid:
                # add the message to the node's list
                messages = cl.get(nodeid, 'messages')
                messages.append(message_id)
                props['messages'] = messages
            else:
                # pre-load the messages list
                props['messages'] = [message_id]

        #
        # perform the node change / create
        #
        try:
            # merge the command line props defined in issue_props into
            # the props dictionary because function(**props, **issue_props)
            # is a syntax error.
            for prop in issue_props.keys() :
                if not props.has_key(prop) :
                    props[prop] = issue_props[prop]

            # Check permissions for each property
            for prop in props.keys():
                if not self.db.security.hasPermission('Edit', author,
                        classname, prop):
                    raise Unauthorized, _('You are not permitted to edit '
                        'property %(prop)s of class %(classname)s.') % locals()

            if nodeid:
                cl.set(nodeid, **props)
            else:
                nodeid = cl.create(**props)
        except (TypeError, IndexError, ValueError, exceptions.Reject), message:
            raise MailUsageError, _("""
There was a problem with the message you sent:
   %(message)s
""") % locals()

        # commit the changes to the DB
        self.db.commit()

        return nodeid


def setPropArrayFromString(self, cl, propString, nodeid=None):
    ''' takes string of form prop=value,value;prop2=value
        and returns (error, prop[..])
    '''
    props = {}
    errors = []
    for prop in string.split(propString, ';'):
        # extract the property name and value
        try:
            propname, value = prop.split('=')
        except ValueError, message:
            errors.append(_('not of form [arg=value,value,...;'
                'arg=value,value,...]'))
            return (errors, props)
        # convert the value to a hyperdb-usable value
        propname = propname.strip()
        try:
            props[propname] = hyperdb.rawToHyperdb(self.db, cl, nodeid,
                propname, value)
        except hyperdb.HyperdbValueError, message:
            errors.append(str(message))
    return errors, props


def extractUserFromList(userClass, users):
    '''Given a list of users, try to extract the first non-anonymous user
       and return that user, otherwise return None
    '''
    if len(users) > 1:
        for user in users:
            # make sure we don't match the anonymous or admin user
            if userClass.get(user, 'username') in ('admin', 'anonymous'):
                continue
            # first valid match will do
            return user
        # well, I guess we have no choice
        return user[0]
    elif users:
        return users[0]
    return None


def uidFromAddress(db, address, create=1, **user_props):
    ''' address is from the rfc822 module, and therefore is (name, addr)

        user is created if they don't exist in the db already
        user_props may supply additional user information
    '''
    (realname, address) = address

    # try a straight match of the address
    user = extractUserFromList(db.user, db.user.stringFind(address=address))
    if user is not None:
        return user

    # try the user alternate addresses if possible
    props = db.user.getprops()
    if props.has_key('alternate_addresses'):
        users = db.user.filter(None, {'alternate_addresses': address})
        user = extractUserFromList(db.user, users)
        if user is not None:
            return user

    # try to match the username to the address (for local
    # submissions where the address is empty)
    user = extractUserFromList(db.user, db.user.stringFind(username=address))

    # couldn't match address or username, so create a new user
    if create:
        # generate a username
        if '@' in address:
            username = address.split('@')[0]
        else:
            username = address
        trying = username
        n = 0
        while 1:
            try:
                # does this username exist already?
                db.user.lookup(trying)
            except KeyError:
                break
            n += 1
            trying = username + str(n)

        # create!
        try:
            return db.user.create(username=trying, address=address,
                realname=realname, roles=db.config.NEW_EMAIL_USER_ROLES,
                password=password.Password(password.generatePassword()),
                **user_props)
        except exceptions.Reject:
            return 0
    else:
        return 0

def parseContent(content, keep_citations=None, keep_body=None, config=None):
    """Parse mail message; return message summary and stripped content

    The message body is divided into sections by blank lines.
    Sections where the second and all subsequent lines begin with a ">"
    or "|" character are considered "quoting sections". The first line of
    the first non-quoting section becomes the summary of the message.

    Arguments:

        keep_citations: declared for backward compatibility.
            If omitted or None, use config["MAILGW_KEEP_QUOTED_TEXT"]

        keep_body: declared for backward compatibility.
            If omitted or None, use config["MAILGW_LEAVE_BODY_UNCHANGED"]

        config: tracker configuration object.
            If omitted or None, use default configuration.

    """
    if config is None:
        config = configuration.CoreConfig()
    if keep_citations is None:
        keep_citations = config["MAILGW_KEEP_QUOTED_TEXT"]
    if keep_body is None:
        keep_body = config["MAILGW_LEAVE_BODY_UNCHANGED"]
    eol = config["MAILGW_EOL_RE"]
    signature = config["MAILGW_SIGN_RE"]
    original_msg = config["MAILGW_ORIGMSG_RE"]

    # strip off leading carriage-returns / newlines
    i = 0
    for i in range(len(content)):
        if content[i] not in '\r\n':
            break
    if i > 0:
        sections = config["MAILGW_BLANKLINE_RE"].split(content[i:])
    else:
        sections = config["MAILGW_BLANKLINE_RE"].split(content)

    # extract out the summary from the message
    summary = ''
    l = []
    for section in sections:
        #section = section.strip()
        if not section:
            continue
        lines = eol.split(section)
        if (lines[0] and lines[0][0] in '>|') or (len(lines) > 1 and
                lines[1] and lines[1][0] in '>|'):
            # see if there's a response somewhere inside this section (ie.
            # no blank line between quoted message and response)
            for line in lines[1:]:
                if line and line[0] not in '>|':
                    break
            else:
                # we keep quoted bits if specified in the config
                if keep_citations:
                    l.append(section)
                continue
            # keep this section - it has reponse stuff in it
            lines = lines[lines.index(line):]
            section = '\n'.join(lines)
            # and while we're at it, use the first non-quoted bit as
            # our summary
            summary = section

        if not summary:
            # if we don't have our summary yet use the first line of this
            # section
            summary = section
        elif signature.match(lines[0]) and 2 <= len(lines) <= 10:
            # lose any signature
            break
        elif original_msg.match(lines[0]):
            # ditch the stupid Outlook quoting of the entire original message
            break

        # and add the section to the output
        l.append(section)

    # figure the summary - find the first sentence-ending punctuation or the
    # first whole line, whichever is longest
    sentence = re.search(r'^([^!?\.]+[!?\.])', summary)
    if sentence:
        sentence = sentence.group(1)
    else:
        sentence = ''
    first = eol.split(summary)[0]
    summary = max(sentence, first)

    # Now reconstitute the message content minus the bits we don't care
    # about.
    if not keep_body:
        content = '\n\n'.join(l)

    return summary, content

# vim: set filetype=python sts=4 sw=4 et si :
