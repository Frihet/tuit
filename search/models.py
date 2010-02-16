from django.db import models
import datetime

# Create your models here.

PLACEHOLDER = _('Search types')

class SearchType(models.Model):
    name = models.CharField(maxlength=512)
    url = models.CharField(maxlength=512)
    view_order = models.IntegerField()
    permission = models.CharField(maxlength=64,blank=True)

    def __str__(self):
        return self.name

    class Admin: 
        pass

    class Meta:
        ordering = ['name']
        verbose_name_plural = _('Search types')
        verbose_name = _('Search type')


class Search(models.Model):
    type = models.ForeignKey(SearchType)
    name = models.CharField(maxlength=512)
    update_date = models.DateTimeField('last updated')
    freetext = models.CharField(maxlength=2048)
    status = models.CharField(maxlength=32)
    from_date = models.DateTimeField("from", null=True, blank=True)
    minimum_priority = models.IntegerField("minimum priority",null=True, blank=True)
    maximum_priority = models.IntegerField("maximum priority",null=True, blank=True)

    def is_recent(self):
        return self.update_date.date() == datetime.date.today()

    def __str__(self):
        return "name = '%s', query='%s', type= %s" % (self.name, self.query, str(self.type),)
    
    
    
