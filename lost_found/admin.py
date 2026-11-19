from django.contrib import admin
from .models import Category, CampusLocation, ItemReport, ItemImage, PotentialMatch

admin.site.register(Category)
admin.site.register(CampusLocation)
admin.site.register(ItemReport)
admin.site.register(ItemImage)
admin.site.register(PotentialMatch)
