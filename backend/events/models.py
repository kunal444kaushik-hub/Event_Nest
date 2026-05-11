from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('provider', 'Provider'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    phone = models.CharField(max_length=15, blank=True)
    location = models.CharField(max_length=100, blank=True)

    business_name = models.CharField(max_length=100, blank=True)
    owner_name = models.CharField(max_length=100, blank=True)
    service_type = models.CharField(max_length=100, blank=True)
    profile_image = models.ImageField(upload_to='provider_profiles/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='provider_covers/', blank=True, null=True)
    experience = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    is_blocked = models.BooleanField(default=False)
    # Settings fields
    notify_booking_updates = models.BooleanField(default=True)
    notify_offers = models.BooleanField(default=True)

    preferred_location = models.CharField(max_length=100, blank=True, null=True)
    preferred_category = models.CharField(max_length=100, blank=True, null=True)
    default_guest_count = models.IntegerField(blank=True, null=True)

    auto_accept_bookings = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)

    gst_number = models.CharField(max_length=50, blank=True, null=True)
    fssai_number = models.CharField(max_length=50, blank=True, null=True)
    id_proof = models.FileField(upload_to='provider_documents/', blank=True, null=True)
    business_certificate = models.FileField(upload_to='provider_documents/', blank=True, null=True)
    is_deactivated = models.BooleanField(default=False)
    admin_remark = models.TextField(blank=True, null=True)
    
    # New field for multiple service types
    provider_services = models.TextField(blank=True, null=True) # Comma separated types

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Service(models.Model):
    provider = models.ForeignKey(User, on_delete=models.CASCADE)
    service_type = models.CharField(max_length=100)
    service_name = models.CharField(max_length=150)
    short_description = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField()
    price = models.IntegerField()  # Starting Price
    location = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15, blank=True, null=True)
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    extra_details = models.JSONField(default=dict, blank=True)
    
    # New Common Fields
    experience_years = models.IntegerField(default=0)
    min_booking_price = models.IntegerField(default=0)
    max_capacity = models.IntegerField(blank=True, null=True)
    advance_payment_required = models.BooleanField(default=False)
    availability_status = models.CharField(max_length=50, default='Available')
    # Marketplace Features
    is_trending = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.service_name


class Package(models.Model):
    provider = models.ForeignKey(User, on_delete=models.CASCADE)
    package_type = models.CharField(max_length=100) # Wedding, Birthday, Corporate, etc.
    package_name = models.CharField(max_length=150)
    short_description = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField()
    
    # Pricing
    total_price = models.IntegerField() # Base/Starting Price
    pricing_structure = models.CharField(max_length=50, default='Fixed Price') # Fixed, Per Guest, Per Day
    
    # Capacity & Duration
    max_guests = models.IntegerField(blank=True, null=True)
    package_duration = models.CharField(max_length=100, blank=True, null=True)
    
    # Logistics
    location_coverage = models.CharField(max_length=100, blank=True, null=True)
    availability_status = models.CharField(max_length=50, default='Available')
    
    # Media
    image = models.ImageField(upload_to='packages/', blank=True, null=True)
    
    # Marketplace Features
    is_trending = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_outdoor = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False)
    discount_percentage = models.IntegerField(default=0)
    
    # Categorization
    occasion = models.CharField(max_length=100, blank=True, null=True) # Birthday, Wedding, etc.
    theme = models.CharField(max_length=100, blank=True, null=True) # Royal, Minimal, etc.
    
    # Dynamic & Professional Data
    included_services = models.TextField() # Comma separated list of services (Decoration, Catering, etc.)
    extra_details = models.JSONField(default=dict, blank=True) # Type specific details (Theme, Add-ons)
    variants = models.JSONField(default=dict, blank=True) # Basic/Standard/Premium variants
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.package_name

class PackageImage(models.Model):
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='package_gallery/')

class ServiceImage(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='gallery')
    image = models.ImageField(upload_to='service_gallery/')



class EmailOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    purpose = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
       return self.email


    
class CustomPackageBooking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    selected_services = models.ManyToManyField(Service)

    event_date = models.DateField()
    message = models.TextField(blank=True)

    total_price = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="Pending")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Custom Package by {self.user.username}"

class Booking(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
        ('In Progress', 'In Progress'),
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_bookings')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='provider_bookings')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    package = models.ForeignKey(Package, on_delete=models.CASCADE, null=True, blank=True)

    event_date = models.DateField()
    number_of_guests = models.IntegerField(blank=True, null=True)
    number_of_days = models.IntegerField(blank=True, null=True)
    message = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_number = models.CharField(max_length=15, blank=True, null=True)
    
    # New Dynamic Booking Fields
    extra_booking_details = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def booked_item_name(self):
        if self.service:
            return self.service.service_name
        if self.package:
            return self.package.package_name
        return "Unknown"

    def __str__(self):
        return f"{self.user.username} booked {self.booked_item_name}"
    
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, null=True, blank=True, related_name='review')

    rating = models.IntegerField()  # 1 to 5
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} → {self.provider.username}"
    
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, blank=True, null=True)
    package = models.ForeignKey(Package, on_delete=models.CASCADE, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Wishlist - {self.user.username}"
    


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()

    is_read = models.BooleanField(default=False)

    # optional linking
    booking_id = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.user.username} - {self.message[:20]}"


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    details = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.action}"

class AvailabilityBlock(models.Model):
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='availability_blocks')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.provider.username} blocked {self.start_date} to {self.end_date}"

class TeamMember(models.Model):
    ROLE_CHOICES = (
        ('Photographer', 'Photographer'),
        ('Decorator', 'Decorator'),
        ('Caterer', 'Caterer'),
        ('Assistant', 'Assistant'),
        ('Manager', 'Manager'),
        ('Other', 'Other'),
    )
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='team_members')
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    contact = models.CharField(max_length=15, blank=True)
    image = models.ImageField(upload_to='team_members/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.role})"

class EventGallery(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='event_gallery')
    image = models.ImageField(upload_to='event_galleries/')
    video_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ChecklistItem(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='checklist')
    title = models.CharField(max_length=100)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.booking.booked_item_name}"
