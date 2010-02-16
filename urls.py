from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # Example:

    # Uncomment this for admin:
     (r'^tuit/admin/', include('django.contrib.admin.urls')),
     (r'^tuit/search/', 'tuit.search.views.results'),
     (r'^tuit/ticket/new/(?P<id>\w+)', 'tuit.ticket.views.new'),
     (r'^tuit/ticket/new/', 'tuit.ticket.views.new'),
     (r'^tuit/ticket/view/(?P<id>\d+)', 'tuit.ticket.views.view'),
     (r'^tuit/ticket/view/', 'tuit.ticket.views.view'),
     (r'^tuit/ticket/attachment/(?P<id>\d+)/.*', 'tuit.ticket.views.attachment'),
     (r'^tuit/ticket/i18n.js', 'tuit.ticket.views.i18n'),
     (r'^tuit/ticket/email/(?P<id>\d+)', 'tuit.ticket.views.email'),
     (r'^tuit/menu/', 'tuit.menu.views.menu'),
     (r'^tuit/query/user_complete', 'tuit.query.views.user_complete'),
     (r'^tuit/query/autofill', 'tuit.query.views.autofill'),
     (r'^tuit/query/issue_complete', 'tuit.query.views.issue_complete'),
     (r'^tuit/account/logout', 'tuit.account.views.logout'),
     (r'^tuit/account/login', 'tuit.account.views.login'),
     (r'^tuit/account/session/', 'tuit.account.views.session'),
     (r'^tuit/account/(?P<id>\d+)/', 'tuit.account.views.show'),
     (r'^tuit/account/show/', 'tuit.account.views.show'),
     (r'^tuit/account/(?P<uname>[^/]+)/', 'tuit.account.views.show'),
     (r'^tuit/comment/get', 'tuit.comment.views.get'),
     (r'^tuit/comment/set', 'tuit.comment.views.set'),
     (r'^tuit/status/view', 'tuit.status.views.view'),
     (r'^tuit/status/edit', 'tuit.status.views.edit'),
     (r'^tuit/trend', 'tuit.trend.views.view'),
     (r'^tuit/help/?', 'tuit.help.views.help'),
     (r'^tuit/log/', 'tuit.log.views.view'),
     (r'^tuit/?$', 'tuit.home.views.home'),
)
