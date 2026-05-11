from django.contrib import admin
from .models import (
    Profile, Service, Package, Notification, EmailOTP, 
    Booking, CustomPackageBooking, Wishlist, Review, 
    PackageImage, ServiceImage, ActivityLog, 
    AvailabilityBlock, TeamMember, EventGallery, ChecklistItem
)

# --- USER & PROVIDER MANAGEMENT ---

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'business_name', 'location', 'is_approved', 'is_blocked')
    list_filter = ('role', 'is_approved', 'is_blocked', 'service_type')
    search_fields = ('user__username', 'user__email', 'business_name', 'phone')
    ordering = ('-id',)
    readonly_fields = ('user',)

# --- SERVICE & PACKAGE MANAGEMENT ---

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('service_name', 'provider', 'service_type', 'price', 'availability_status', 'is_draft')
    list_filter = ('service_type', 'availability_status', 'is_draft', 'is_featured', 'is_trending')
    search_fields = ('service_name', 'provider__username', 'location')
    ordering = ('-created_at',)

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ('package_name', 'provider', 'package_type', 'total_price', 'is_verified', 'is_draft')
    list_filter = ('package_type', 'is_verified', 'is_draft', 'is_outdoor')
    search_fields = ('package_name', 'provider__username', 'occasion', 'theme')
    ordering = ('-created_at',)

@admin.register(PackageImage)
class PackageImageAdmin(admin.ModelAdmin):
    list_display = ('package', 'image')

@admin.register(ServiceImage)
class ServiceImageAdmin(admin.ModelAdmin):
    list_display = ('service', 'image')

# --- BOOKING MANAGEMENT ---

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'provider', 'booked_item_name', 'event_date', 'status', 'created_at')
    list_filter = ('status', 'event_date', 'created_at')
    search_fields = ('id', 'user__username', 'provider__username', 'message')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

@admin.register(CustomPackageBooking)
class CustomPackageBookingAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_date', 'total_price', 'status')
    list_filter = ('status', 'event_date')

# --- ENGAGEMENT & FEEDBACK ---

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'provider__username', 'comment')

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'service', 'package', 'created_at')

# --- SYSTEM & UTILITY ---

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('user__username', 'message')

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'otp', 'purpose', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('user__username', 'action', 'details')

# --- PROVIDER ASSETS ---

@admin.register(AvailabilityBlock)
class AvailabilityBlockAdmin(admin.ModelAdmin):
    list_display = ('provider', 'start_date', 'end_date', 'reason')
    list_filter = ('start_date', 'end_date')

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'role', 'contact')
    list_filter = ('role',)

@admin.register(EventGallery)
class EventGalleryAdmin(admin.ModelAdmin):
    list_display = ('booking', 'image', 'created_at')

@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'booking', 'is_completed')
    list_filter = ('is_completed',)
