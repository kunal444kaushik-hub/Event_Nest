from django.contrib import admin
from .models import Profile, Service, Package, Notification, EmailOTP, Booking, CustomPackageBooking
from .models import Wishlist



admin.site.register(Profile)
admin.site.register(Service)
admin.site.register(Package)
admin.site.register(Notification)
admin.site.register(EmailOTP)
admin.site.register(Booking)
admin.site.register(CustomPackageBooking)
admin.site.register(Wishlist)

