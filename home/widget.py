# Views for the widget class
# -*- coding: utf-8 -*-

from datetime import datetime
import logging

class Widget:
    """
    A class for displaying ticket Model results in a nice, paginated
    way. The model needs to have a few extra methods for formatting
    the results.
    """

    def __init__(self, name, items, request, 
                 slug='issues', columns=None, item_count=10,
                 class_names="widget_1",style='table', row_class=''):
        """
        Construct the widget. The items need to be a django orm search
        result. No limit or other silliness should be pallied, the
        widget figures those things out itself. It's so clever. yes.
        """
        self.name=name
        self.items=items
        self.columns=columns
        self.slug=slug
        self.item_count = item_count
        self.request = request
        self.class_names = class_names
        self.style = style

    def __to_json__(self):
        return {"__jsonclass__":["Widget", []],
                "name": self.name,
                "items": list(self.items),
                "columns": self.columns,
                "slug": self.slug,
                "item_count": self.item_count,
                "class_names": self.class_names,
                "style": self.style,
                "html": self.html,
                }

    @property
    def current_page(self):
        """
        What apge are we on?
        """
        try:
            return int(self.request.GET[self.slug + '_page'])
        except:
#            import traceback as tb
#            tb.print_exc()
            return 1

    @property
    def pager(self):
        """
        Returns html for a complete pager thingee. Code is currently a
        bit hackish.
        """
        def page_url(page):
            d={}#self.request.GET.copy()#dict(self.request.GET.iteritems())
            for i in self.request.GET:
                if i not in ("_HTTP_ACCEPT", "_json_selector"):
                    d[i] = self.request.GET[i]
            d[self.slug + '_page'] = str(page)
            return "?" + "&".join(map(lambda (x,y):"%s=%s"%(x,y), d.iteritems()))

        def page_click(page):
            return "tuit.updateWidget('%s', '%s')" % (self.slug, page_url(page))

        def render_item(idx):
            if idx == self.current_page:
                #~ return str(idx)
                return "<a style=\"font-size-adjust: 0.7; background: white; color: black; font-weight: bold;\">%(idx)d</a>" % {'idx':idx}
            return "<a href=\"javascript:%(click)s\">%(idx)d</a>" % {'url':page_url(idx),'click':page_click(idx), 'idx':idx}
        
        pages = ((self.items.count()-1)/self.item_count)+1
        if pages == 1:
            return ""
        if pages < 50:
            return "&nbsp;".join(map(render_item, range(1,pages+1)))

        if self.current_page > 25:
            if self.current_page < pages - 26:
                return render_item(1) + "..." + "&nbsp;".join(map(render_item, range(self.current_page-25,self.current_page+25))) + "..." + render_item(pages)
            return render_item(1) + "..." + "&nbsp;".join(map(render_item, range(self.current_page-25,pages+1)))
        else:
            return "&nbsp;".join(map(render_item, range(1,self.current_page+25))) + "..." + render_item(pages) 


    @property
    def html(self):
        """
        Render the widget to html, with pagers, header and everything.
        """
        start_time = datetime.now()

        page = self.current_page

        try:
            count = self.items.count()
            
            num_items = self.item_count
            start =min(count, max(0,(page-1)*num_items))
            stop = min(start+num_items, count)
#            print "Show items", start, "to", stop
            items_shown = self.items[start:stop]
            pages = ((count-1)/self.item_count)+1
            if len(self.items) > 0:
                if self.columns is None:
                    self.columns = self.items[0].html_default_columns

            if self.style == 'table':

                if len(self.items) == 0:
                    table = _("No matching items found")
                    message=""
                else:


                    message = _("Showing items %(first)d to %(last)d of %(total)d") % {'first':start+1,'last':stop,'total':count}
                    col_name = map(lambda x:x[1], self.columns)
                    col_desc = "<thead><tr>" + "\n".join(map(lambda x:"<th><a href=\"aaa_%s\">%s</a></th>" % (x[1], x[0]), self.columns)) + "</tr></thead>"
                    print col_desc

                    def row_class_string(row):
                        if hasattr(row, 'row_class'):
                            return 'class="%s"' % row.row_class
                        return ''


                    cells = map(lambda x: {'cells': x.html_row(col_name), 'class':row_class_string(x) }, items_shown)

                    rendered_cells = map(lambda row: ("<tr %s>" % row['class']) + "".join(map(lambda cell:"<td>%s</td>" % cell, row['cells']))+ "</tr>", cells)
                    rows = "".join(rendered_cells)
                    
                    pager=self.pager
                    if pager != "":
                        #~ pager_row ="<tr><td colspan='%d'>%s: %s</td></tr>" % (len(self.columns),_('Page'),self.pager)
                        pager_str = "<tr><td colspan='%d'> " % len(self.columns)
                        pager_str += "&nbsp;<a href=\"javascript:tuit.updateWidget('%(slug)s', '?%(slug)s_page=1')\"><<</a>&nbsp;" % {'slug': self.slug}
                        
                        prev = self.current_page-1
                        if prev < 1:
                            prev = 1
                        ne = self.current_page+1
                        if ne > pages:
                            ne = pages
                        pager_str += "<a href=\"javascript:tuit.updateWidget('%(slug)s', '?%(slug)s_page=%(prev)d')\"><</a>&nbsp;" % {'slug': self.slug, 'prev': prev}
                        pager_str += "%s" % (self.pager)
                        print pager_str
                        pager_str += "&nbsp;<a href=\"javascript:tuit.updateWidget('%(slug)s', '?%(slug)s_page=%(next)d')\">></a>&nbsp;" % {'slug': self.slug, 'next': ne}
                    
                        pager_str += "<a href=\"javascript:tuit.updateWidget('%(slug)s', '?%(slug)s_page=%(count)d')\">>></a>&nbsp;" % {'slug': self.slug, 'count': pages}
                        pager_row = pager_str + "</td></tr>"
                        #~ print pager_row
                    else:
                        pager_row = ""

                    rows = pager_row + rows + pager_row
                    table ="<table class='striped'>\n%s\n%s\n</table>" % (col_desc,rows)
                    stop_time = datetime.now()
                    time = stop_time-start_time
                    time = 0.0+time.seconds + 0.000001*time.microseconds
                    if time > 0.75:
                        logging.getLogger('performance').warning('DB access for widget «%s», user %s took %.2f seconds' % (self.slug, self.request.user.username, time))                    
                return "<div class='widget %s' id='widget_%s'><div class='widget_header'><h2>%s</h2>%s</div>%s</div>"%(self.class_names, self.slug, self.name,message,table)
            elif self.style == 'list':
                hdr = "<li><h2>%s</h2></li>" % self.name
                if len(self.items) == 0:
                    return "%s<li>%s</li>" % (hdr, _("No matching items found"))
                else:
#                    self.columns = [ self.columns[0] ]
                    col_name = map(lambda x:x[1], self.columns)
                    cells = map(lambda x: x.html_row(col_name), items_shown)
                    rows = "".join(map(lambda row: "<li>" + "".join(map(lambda cell:"%s" % cell, row))+ "</li>", cells))
                    stop_time = datetime.now()
                    time = stop_time-start_time
                    time = 0.0+time.seconds + 0.000001*time.microseconds
                    if time > 0.75:
                        logging.getLogger('performance').warning('DB access for widget «%s», user %s took %.2f seconds' % (self.slug, self.request.user.username, time))                    
                return hdr + rows
            else:
                raise Exception("Unknown widget style")
        except:
            import traceback
            traceback.print_exc()
            return _("<div class='error'>There was an problem while showing this widget.</div>")
        
