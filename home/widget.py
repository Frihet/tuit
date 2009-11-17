# -*- coding: utf-8 -*-

from datetime import datetime
import logging

class Widget:

    def __init__(self, name, items, request, slug='issues', columns=None, item_count=10,class_names=""):
        self.name=name
        self.items=items
        self.columns=columns
        self.slug=slug
        self.item_count = item_count
        self.request = request
        self.class_names = class_names

    @property
    def current_page(self):
        try:
            return int(self.request.GET[self.slug + '_page'])
        except:
#            import traceback as tb
#            tb.print_exc()
            return 1

    @property
    def pager(self):
        def page_url(page):
            d={}#self.request.GET.copy()#dict(self.request.GET.iteritems())
            for i in self.request.GET:
                d[i] = self.request.GET[i]
            d[self.slug + '_page'] = str(page)
            #print 'AAA', page
            #print d
            return "?" + "&".join(map(lambda (x,y):"%s=%s"%(x,y), d.iteritems()))

        def render_item(idx):
            if idx == self.current_page:
                return str(idx)
            return "<a href='%(url)s'>%(idx)d</a>" % {'url':page_url(idx),'idx':idx}
        
        
        pages = ((self.items.count()-1)/self.item_count)+1
        if pages < 12:
            return "&nbsp;".join(map(render_item, range(1,pages+1)))

        if self.current_page > 5:
            if self.current_page < pages - 6:
                return render_item(1) + "..." + "&nbsp;".join(map(render_item, range(self.current_page-5,self.current_page+5))) + "..." + render_item(pages)
            return render_item(1) + "..." + "&nbsp;".join(map(render_item, range(self.current_page-5,pages+1)))
        else:
            return "&nbsp;".join(map(render_item, range(1,self.current_page+5))) + "..." + render_item(pages) 

    @property
    def html(self):
        start_time = datetime.now()

        page = self.current_page

        try:
            count = self.items.count()
            
            num_items = self.item_count
            start =min(count, max(0,(page-1)*num_items))
            stop = min(start+num_items, count)
#            print "Show items", start, "to", stop
            items_shown = self.items[start:stop]

            if len(self.items) == 0:
                table = _("No matching items found")
                message=""
            else:
                if self.columns is None:
                    self.columns = self.items[0].html_default_columns

                message = _("Showing items %(first)d to %(last)d of %(total)d") % {'first':start,'last':stop,'total':count}

                col_name = map(lambda x:x[1], self.columns)
                col_desc = "<tr>" + "\n".join(map(lambda x:"<th>%s</th>"%x[0], self.columns)) + "</tr>"
                rows = "\n".join(map(lambda x: x.html_row(col_name), items_shown))
                pager_row ="<tr><td colspan='%d'>%s: %s</td></tr>" % (len(self.columns),_('Page'),self.pager)
                rows = pager_row + rows + pager_row
                table ="<table class='striped'>\n%s\n%s\n</table>" % (col_desc,rows)
                stop_time = datetime.now()
                time = stop_time-start_time
                time = 0.0+time.seconds + 0.000001*time.microseconds
                if time > 0.75:
                    logging.getLogger('performance').warning('DB access for widget «%s», user %s took %.2f seconds' % (self.slug, self.request.user.username, time))                    
            return "<div class='widget %s'><h2>%s</h2>%s%s</div>"%(self.class_names, self.name,message,table)
        except:
            import traceback
            traceback.print_exc()
            return ""
        
