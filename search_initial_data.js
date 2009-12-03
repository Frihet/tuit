[
{"pk": "1", "model": "search.searchtype", "fields": {"url": "\/cgi-bin\/foswiki\/search\/KB\/?search=%(freetext)s&skin=json&type=literal&scope=all", "view_order": 30, "name": "Knowlege Base", "permission": ""}},
 {"pk": "2", "model": "search.searchtype", "fields": {"url": "\/FreeCMDB\/?controller=ciList&filter_type=-1&filter_column=4&filter_column_value=%(freetext)s&output=json", "view_order": 20, "name": "CMDB", "permission": ""}},
 {"pk": "3", "model": "search.searchtype", "fields": {"url": "\/tuit\/query\/issue_complete\/?query=%(freetext)s&search=t&from_date=%(from_date)s&to_date=%(to_date)s&priority=%(priority)s&status=%(status)s", "view_order": 10, "name": "Issues", "permission": ""}},
 {"pk": "5", "model": "search.searchtype", "fields": {"url": "\/cgi-bin\/foswiki\/search\/IKB\/?search=%(freetext)s&skin=json&type=literal&scope=all", "view_order": 35, "name": "Internal Knowledge Base", "permission": "is_staff"}},
 {"pk": "4", "model": "search.searchtype", "fields": {"url": "\/tuit\/query\/user_complete\/?query=%(freetext)s&search", "view_order": 100, "name": "Brukere", "permission": ""}}
]
