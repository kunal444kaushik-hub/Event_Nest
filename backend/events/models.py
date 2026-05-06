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
    
    # New field for multiple service types
    provider_services = models.TextField(blank=True, null=True) # Comma separated types

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Service(models.Model):
    provider = models.ForeignKey(User, on_delete=models.CASCADE)
    service_type = models.CharField(max_length=100)
    service_name = models.CharField(max_length=150)
    description = models.TextField()
    price = models.IntegerField()
    location = models.CharField(max_length=100)
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    extra_details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.service_name


class Package(models.Model):
    provider = models.ForeignKey(User, on_delete=models.CASCADE)

    package_type = models.CharField(max_length=100)
    package_name = models.CharField(max_length=150)
    included_services = models.TextField()
    description = models.TextField()
    total_price = models.IntegerField()
    image = models.ImageField(upload_to='packages/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.package_name



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
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_bookings')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='provider_bookings')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    event_date = models.DateField()
    number_of_guests = models.IntegerField(blank=True, null=True)
    number_of_days = models.IntegerField(blank=True, null=True)
    message = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} booked {self.service.service_name}"
    
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')

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
