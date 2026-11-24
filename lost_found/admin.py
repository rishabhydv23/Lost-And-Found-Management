from django.contrib import admin

from .models import CampusLocation, Category, ItemImage, ItemReport, PotentialMatch

admin.site.register(Category)
admin.site.register(CampusLocation)
admin.site.register(ItemReport)
admin.site.register(ItemImage)
admin.site.register(PotentialMatch)
