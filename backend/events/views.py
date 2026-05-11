import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password

from django.db.models import Count, Sum, Avg, Q
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.core.paginator import Paginator
from .models import Profile, Service, Package, Notification, EmailOTP, Booking, CustomPackageBooking, Wishlist, Review, PackageImage, ServiceImage, ActivityLog, AvailabilityBlock, TeamMember, EventGallery, ChecklistItem
from .planner_logic import get_event_recommendations

# Global constant for service categories
SERVICE_CATEGORIES = [
    "DJ & Music", "Catering", "Decoration", "Photography", 
    "Lighting Setup", "Event Planning", "Host / Anchor", 
    "Cake Service", "Furniture / Tent", "Car Rental", 
    "Venue Provider", "Wedding Planner"
]

# Global constant for popular locations
POPULAR_LOCATIONS = [
    "Guwahati", "Jorhat", "Dibrugarh", "Silchar", "Tezpur", 
    "Nagaon", "Tinsukia", "Sivasagar", "Delhi", "Mumbai", 
    "Bangalore", "Kolkata"
]

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from functools import wraps

def provider_approved_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated:
            if hasattr(request.user, 'profile') and request.user.profile.role == 'provider':
                if not request.user.profile.is_approved:
                    return redirect('pending_approval')
        return view_func(request, *args, **kwargs)
    return _wrapped_view





def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin_home')
        
        # Safety check for profile existence
        if hasattr(request.user, 'profile'):
            if request.user.profile.role == 'provider':
                if not request.user.profile.is_approved:
                    return redirect('pending_approval')
                return redirect('provider_home')
            return redirect('user_home')
        else:
            # Fallback for users without profiles (should be rare)
            logout(request)
            return render(request, 'index.html')
            
    return render(request, 'index.html')


@login_required
def user_home(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
    return render(request, 'user_home.html', {
        'notifications': notifications,
        'notify_count': notifications.count()
    })


@login_required
@provider_approved_required
def provider_home(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
    return render(request, 'provider_home.html', {
        'notifications': notifications,
        'notify_count': notifications.count()
    })

def services(request):
    return render(request, 'services.html')




@login_required(login_url='login')
@provider_approved_required
def list_service(request):
    # Check if provider
    if request.user.profile.role != 'provider':
        messages.error(request, "Only providers can list services.")
        return redirect('home')

    # Block listing if not approved
    if not request.user.profile.is_approved:
        messages.error(request, "Your account is not yet verified by Admin. You cannot list services until verification is complete.")
        return redirect('provider_dashboard')

    if request.method == "POST":
        service_type = request.POST.get("service_type")
        service_name = request.POST.get("service_name")
        short_description = request.POST.get("short_description")
        description = request.POST.get("description")
        price = request.POST.get("price")
        location = request.POST.get("location")
        contact_number = request.POST.get("contact_number")
        experience_years = request.POST.get("experience_years", 0)
        min_booking_price = request.POST.get("min_booking_price", 0)
        max_capacity = request.POST.get("max_capacity")
        advance_payment_required = request.POST.get("advance_payment_required") == 'on'
        availability_status = request.POST.get("availability_status", "Available")
        image = request.FILES.get("image")
        gallery_images = request.FILES.getlist("gallery_images")
        is_draft = request.POST.get("is_draft") == 'on'

        # Validation: Min 3, Max 10 total (Main + Gallery)
        total_images = (1 if image else 0) + len(gallery_images)
        if total_images < 3:
            messages.error(request, f"Please upload at least 3 photos in total (1 main photo and at least 2 gallery photos). You have uploaded {total_images}.")
            return render(request, "list_service.html")
        if total_images > 10:
            messages.error(request, f"You can upload a maximum of 10 photos in total. You have uploaded {total_images}.")
            return render(request, "list_service.html")

        # Collect dynamic extra details
        extra_details = {}
        for key in request.POST:
            if key.startswith("detail_"):
                val = request.POST.get(key)
                if val:
                    # Strip 'detail_' prefix for cleaner storage
                    clean_key = key.replace("detail_", "")
                    extra_details[clean_key] = val

        service = Service.objects.create(
            provider=request.user,
            service_type=service_type,
            service_name=service_name,
            short_description=short_description,
            description=description,
            price=price,
            location=location,
            contact_number=contact_number,
            experience_years=experience_years if experience_years else 0,
            min_booking_price=min_booking_price if min_booking_price else 0,
            max_capacity=max_capacity if max_capacity else None,
            advance_payment_required=advance_payment_required,
            availability_status=availability_status,
            image=image,
            extra_details=extra_details,
            is_draft=is_draft
        )

        # Save gallery images
        for img in gallery_images:
            ServiceImage.objects.create(service=service, image=img)
        
        Notification.objects.create(
            user=request.user,
            message=f"Success! Your service '{service_name}' has been listed."
        )

        messages.success(request, f"Service '{service_name}' listed successfully!")
        ActivityLog.objects.create(user=request.user, action="Service Listed", details=f"Listed new service: {service_name}")
        return redirect("provider_dashboard")

    return render(request, "list_service.html")

@login_required(login_url='login')
@provider_approved_required
def edit_service(request, service_id):
    service = get_object_or_404(Service, id=service_id, provider=request.user)

    if request.method == "POST":
        service.service_type = request.POST.get("service_type")
        service.service_name = request.POST.get("service_name")
        service.short_description = request.POST.get("short_description")
        service.description = request.POST.get("description")
        service.price = request.POST.get("price")
        service.location = request.POST.get("location")
        service.contact_number = request.POST.get("contact_number")
        service.experience_years = request.POST.get("experience_years", 0)
        service.min_booking_price = request.POST.get("min_booking_price", 0)
        service.max_capacity = request.POST.get("max_capacity")
        service.advance_payment_required = request.POST.get("advance_payment_required") == 'on'
        service.availability_status = request.POST.get("availability_status", "Available")
        
        new_image = request.FILES.get("image")
        if new_image:
            service.image = new_image

        # Update extra details
        extra_details = {}
        for key in request.POST:
            if key.startswith("detail_"):
                val = request.POST.get(key)
                if val:
                    clean_key = key.replace("detail_", "")
                    extra_details[clean_key] = val
        service.extra_details = extra_details
        service.save()

        messages.success(request, f"Service '{service.service_name}' updated successfully!")
        return redirect("provider_dashboard")

    return render(request, "edit_service.html", {"service": service})

@login_required(login_url='login')
@provider_approved_required
def delete_service(request, service_id):
    if request.method == "POST":
        service = get_object_or_404(Service, id=service_id, provider=request.user)
        service_name = service.service_name
        service.delete()
        messages.success(request, f"Service '{service_name}' deleted.")
    return redirect("provider_dashboard")

def packages(request):
    event_types = [
        "Birthday Package",
        "Marriage Package",
        "Engagement Package",
        "Sangeet Package",
        "Office Party Package",
        "Bachelor Party Package",
        "Exhibition Package",
        "Workshop Package",
        "Custom Combo Package"
    ]

    trending_packages = Package.objects.filter(is_trending=True).annotate(gallery_count=Count('gallery'))[:6]
    featured_packages = Package.objects.filter(is_featured=True).annotate(gallery_count=Count('gallery'))[:4]
    budget_packages = Package.objects.filter(total_price__lte=50000).annotate(gallery_count=Count('gallery'))[:6]
    luxury_packages = Package.objects.filter(total_price__gte=100000).annotate(gallery_count=Count('gallery'))[:6]
    custom_combo_packages = Package.objects.filter(package_type="Custom Combo Package").annotate(gallery_count=Count('gallery'))[:6]
    
    # Simple recommendation based on random for now, or could be based on user preference if exists
    recommended_packages = Package.objects.all().annotate(gallery_count=Count('gallery')).order_by('?')[:6]

    occasions = [
        {"name": "Birthday", "icon": "fa-cake-candles"},
        {"name": "Wedding", "icon": "fa-ring"},
        {"name": "Engagement", "icon": "fa-gem"},
        {"name": "Sangeet", "icon": "fa-music"},
        {"name": "Corporate", "icon": "fa-briefcase"},
        {"name": "Exhibition", "icon": "fa-palette"},
        {"name": "Workshop", "icon": "fa-chalkboard-user"},
        {"name": "Festival", "icon": "fa-holly-berry"},
        {"name": "College", "icon": "fa-graduation-cap"},
        {"name": "Luxury", "icon": "fa-crown"},
        {"name": "Outdoor", "icon": "fa-tree"},
        {"name": "Budget", "icon": "fa-tags"},
    ]

    themes = ["Royal Theme", "Minimal Theme", "Traditional Theme", "Luxury Theme", "Outdoor Garden Theme"]

    return render(request, 'packages.html', {
        'event_types': event_types,
        'trending_packages': trending_packages,
        'featured_packages': featured_packages,
        'budget_packages': budget_packages,
        'luxury_packages': luxury_packages,
        'custom_combo_packages': custom_combo_packages,
        'recommended_packages': recommended_packages,
        'occasions': occasions,
        'themes': themes
    })


def package_by_type(request, type_name):
    # Base Query with Annotations
    packages = Package.objects.all().annotate(
        gallery_count=Count("gallery"),
        avg_rating=Avg("provider__reviews__rating")
    )

    # Theme/Occasion/Type Filter
    if type_name != "All":
        packages = packages.filter(Q(package_type=type_name) | Q(occasion=type_name) | Q(theme=type_name))

    # Query Parameters for Advanced Filtering
    q = request.GET.get('q')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    guests = request.GET.get('guests')
    location = request.GET.get('location')
    outdoor = request.GET.get('outdoor')
    verified = request.GET.get('verified')
    rating = request.GET.get('rating')

    if q:
        packages = packages.filter(
            Q(package_name__icontains=q) |
            Q(description__icontains=q) |
            Q(provider__username__icontains=q)
        )
    if min_price:
        packages = packages.filter(total_price__gte=min_price)
    if max_price:
        packages = packages.filter(total_price__lte=max_price)
    if guests:
        packages = packages.filter(max_guests__gte=guests)
    if location:
        packages = packages.filter(location_coverage__icontains=location)
    if outdoor == 'yes':
        packages = packages.filter(is_outdoor=True)
    elif outdoor == 'no':
        packages = packages.filter(is_outdoor=False)
    if verified == 'yes':
        packages = packages.filter(is_verified=True)
    if rating:
        packages = packages.filter(avg_rating__gte=rating)

    packages = packages.order_by('-created_at')

    return render(request, 'package_list.html', {
        'packages': packages,
        'type_name': type_name,
        'filters': {
            'min_price': min_price,
            'max_price': max_price,
            'guests': guests,
            'location': location,
            'outdoor': outdoor,
            'verified': verified,
            'rating': rating
        }
    })

def custom_package(request):
    services = Service.objects.all()

    if request.method == "POST":
        selected = request.POST.getlist("services")
        total = 0

        selected_services = Service.objects.filter(id__in=selected)

        for s in selected_services:
            total += s.price

        return render(request, "custom_result.html", {
            "services": selected_services,
            "total": total
        })

    return render(request, "custom_package.html", {"services": services})


@login_required(login_url='login')
@provider_approved_required
def list_package(request):
    # Check if provider
    if request.user.profile.role != 'provider':
        messages.error(request, "Only providers can list packages.")
        return redirect('home')

    # Block listing if not approved
    if not request.user.profile.is_approved:
        messages.error(request, "Your account is not yet verified by Admin. You cannot list packages until verification is complete.")
        return redirect('provider_dashboard')

    if request.method == "POST":
        package_type = request.POST.get("package_type")
        package_name = request.POST.get("package_name")
        short_description = request.POST.get("short_description")
        description = request.POST.get("description")
        total_price = request.POST.get("total_price")
        pricing_structure = request.POST.get("pricing_structure", "Fixed Price")
        max_guests = request.POST.get("max_guests")
        package_duration = request.POST.get("package_duration")
        location_coverage = request.POST.get("location_coverage")
        availability_status = request.POST.get("availability_status", "Available")
        
        included_services = request.POST.getlist("included_services")
        image = request.FILES.get("image")
        gallery_images = request.FILES.getlist("gallery_images")
        is_draft = request.POST.get("is_draft") == 'on'

        # Validation: Min 3, Max 10 total (Main + Gallery)
        total_images = (1 if image else 0) + len(gallery_images)
        if total_images < 3:
            my_services = Service.objects.filter(provider=request.user)
            messages.error(request, f"Please upload at least 3 photos in total (1 main photo and at least 2 gallery photos). You have uploaded {total_images}.")
            return render(request, "list_package.html", {"my_services": my_services})
        if total_images > 10:
            my_services = Service.objects.filter(provider=request.user)
            messages.error(request, f"You can upload a maximum of 10 photos in total. You have uploaded {total_images}.")
            return render(request, "list_package.html", {"my_services": my_services})

        # Collect dynamic extra details (themes, add-ons, etc.)
        extra_details = {}
        for key in request.POST:
            if key.startswith("detail_"):
                val = request.POST.get(key)
                if val:
                    extra_details[key.replace("detail_", "")] = val

        # Collect Variants (Basic, Standard, Premium)
        variants = {
            "Basic": {
                "price": request.POST.get("variant_basic_price"),
                "features": request.POST.get("variant_basic_features")
            },
            "Standard": {
                "price": request.POST.get("variant_standard_price"),
                "features": request.POST.get("variant_standard_features")
            },
            "Premium": {
                "price": request.POST.get("variant_premium_price"),
                "features": request.POST.get("variant_premium_features")
            }
        }

        package = Package.objects.create(
            provider=request.user,
            package_type=package_type,
            package_name=package_name,
            short_description=short_description,
            description=description,
            total_price=total_price,
            pricing_structure=pricing_structure,
            max_guests=max_guests if max_guests else None,
            package_duration=package_duration,
            location_coverage=location_coverage,
            availability_status=availability_status,
            included_services=", ".join(included_services),
            extra_details=extra_details,
            variants=variants,
            image=image,
            is_draft=is_draft
        )
        
        # Save gallery images
        for img in gallery_images:
            PackageImage.objects.create(package=package, image=img)

        Notification.objects.create(
            user=request.user,
            message=f"Success! Your professional combo package '{package_name}' has been listed."
        )

        messages.success(request, f"Combo Package '{package_name}' launched successfully!")
        ActivityLog.objects.create(user=request.user, action="Package Listed", details=f"Listed new package: {package_name}")
        return redirect("provider_dashboard")

    # Pass provider's own services for the builder
    my_services = Service.objects.filter(provider=request.user)
    
    return render(request, "list_package.html", {"my_services": my_services})

@login_required(login_url='login')
@provider_approved_required
def edit_package(request, package_id):
    package = get_object_or_404(Package, id=package_id, provider=request.user)
    if request.method == "POST":
        package.package_name = request.POST.get("package_name")
        package.package_type = request.POST.get("package_type")
        package.total_price = request.POST.get("total_price")
        package.pricing_structure = request.POST.get("pricing_structure")
        package.included_services = request.POST.get("included_services")
        package.description = request.POST.get("description")
        package.max_guests = request.POST.get("max_guests")
        
        new_image = request.FILES.get("image")
        if new_image:
            package.image = new_image
            
        package.save()
        messages.success(request, f"Package '{package.package_name}' updated.")
        return redirect("provider_dashboard")
        
    return render(request, "edit_package.html", {"package": package})

@login_required(login_url='login')
@provider_approved_required
def delete_package(request, package_id):
    if request.method == "POST":
        package = get_object_or_404(Package, id=package_id, provider=request.user)
        package_name = package.package_name
        package.delete()
        messages.success(request, f"Package '{package_name}' deleted.")
    return redirect("provider_dashboard")

@login_required(login_url='login')
@provider_approved_required
def duplicate_package(request, package_id):
    if request.method == "POST":
        original_pkg = get_object_or_404(Package, id=package_id, provider=request.user)
        
        # Clone the package
        new_pkg = Package.objects.get(id=package_id)
        new_pkg.pk = None # Setting pk to None creates a new record on save
        new_pkg.package_name = f"Copy of {original_pkg.package_name}"
        new_pkg.is_draft = True # Set to draft so they can edit it
        new_pkg.save()

        # Clone gallery images
        for img in original_pkg.gallery.all():
            PackageImage.objects.create(package=new_pkg, image=img.image)

        messages.success(request, f"Package duplicated as '{new_pkg.package_name}'. You can now edit and publish it.")
        return redirect("list_package")
    return redirect("provider_dashboard")


def contact(request):
    return render(request, 'contact.html')


def login_choice(request):
    return render(request, 'login_choice.html')


def register_view(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if User.objects.filter(email=email).exists():
            return render(request, "register.html", {"error": "Email already registered"})

        request.session["user_register_email"] = email
        send_otp_email(email, "user_register")
        return redirect("verify_user_otp")

    return render(request, "register.html")

def user_details(request):
    email = request.session.get("user_register_email")
    otp_verified = request.session.get("user_otp_verified")

    if not email or not otp_verified:
        return redirect("register")

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        username = request.POST.get("username")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(request, "user_details.html", {"error": "Passwords do not match"})

        if User.objects.filter(username=username).exists():
            return render(request, "user_details.html", {"error": "Username already exists"})

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        Profile.objects.create(
            user=user,
            role="user",
            phone=phone
        )

        # Auto login
        from django.contrib.auth import login
        login(request, user)

        # Clear session
        del request.session["user_register_email"]
        del request.session["user_otp_verified"]

        return redirect("user_home")

    return render(request, "user_details.html")

def provider_step1(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if User.objects.filter(email=email).exists():
            return render(request, "provider_step1.html", {"error": "Email already registered"})

        request.session["provider_register_email"] = email
        send_otp_email(email, "provider_register")
        return redirect("verify_provider_otp")

    return render(request, "provider_step1.html")


def provider_step2(request):
    email = request.session.get("provider_register_email")
    otp_verified = request.session.get("provider_otp_verified")

    if not email or not otp_verified:
        return redirect("provider_step1")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(request, "provider_step2.html", {"error": "Passwords do not match"})

        if User.objects.filter(username=username).exists():
            return render(request, "provider_step2.html", {"error": "Username already exists"})

        request.session["provider_username"] = username
        request.session["provider_password"] = password

        return redirect("provider_step3")

    return render(request, "provider_step2.html")


def provider_step3(request):
    if not request.session.get("provider_username"):
        return redirect("provider_step2")

    if request.method == "POST":
        request.session["business_name"] = request.POST.get("business_name")
        request.session["owner_name"] = request.POST.get("owner_name")
        request.session["phone"] = request.POST.get("phone")
        request.session["location"] = request.POST.get("location")

        return redirect("provider_step4")

    return render(request, "provider_step3.html")


def provider_step4(request):
    if not request.session.get("business_name"):
        return redirect("provider_step3")

    if request.method == "POST":
        # Multi-service support
        service_types = request.POST.getlist("service_types")
        bio = request.POST.get("bio")
        experience = request.POST.get("experience")
        
        email = request.session.get("provider_register_email")
        username = request.session.get("provider_username")
        password = request.session.get("provider_password")
        business_name = request.session.get("business_name")
        owner_name = request.session.get("owner_name")
        phone = request.session.get("phone")
        location = request.session.get("location")

        from django.contrib.auth.models import User
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=owner_name,
            last_name=business_name
        )

        Profile.objects.create(
            user=user,
            role="provider",
            phone=phone,
            location=location,
            business_name=business_name,
            owner_name=owner_name,
            bio=bio,
            experience=experience,
            provider_services=",".join(service_types),
            is_approved=False
        )

        # Clear registration session data safely before login
        request.session.flush()

        # Auto login
        from django.contrib.auth import login
        login(request, user)

        messages.success(request, "Registration successful! Your application is now pending admin approval.")
        return redirect("pending_approval")

    return render(request, "provider_step4.html")

@login_required
def pending_approval(request):
    if request.user.profile.role != 'provider':
        return redirect('home')
    
    if request.user.profile.is_approved:
        return redirect('provider_dashboard')
        
    return render(request, 'provider_pending.html', {
        'profile': request.user.profile
    })


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:

            # ✅ Admin login first
            if user.is_staff or user.is_superuser:
                login(request, user)
                return redirect("admin_home")   # 🔥 changed

            try:
                if user.profile.role == "user":
                    login(request, user)
                    return redirect("user_home")

                return render(request, "login.html", {
                    "error": "This account is not a user account"
                })

            except Profile.DoesNotExist:
                return render(request, "login.html", {
                    "error": "Profile not found"
                })

        return render(request, "login.html", {
            "error": "Invalid username or password"
        })

    return render(request, "login.html")

def provider_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:

            # ✅ ADD THIS (ADMIN CHECK FIRST)
            if user.is_staff or user.is_superuser:
                login(request, user)
                return redirect("admin_home")

            try:
                if user.profile.role == "provider":

                    if user.profile.is_blocked:
                        return render(request, "provider_login.html", {
                            "error": "Your provider account has been blocked by admin."
                        })

                    login(request, user)
                    
                    if not user.profile.is_approved:
                        return redirect("pending_approval")
                        
                    return redirect("provider_home")

                return render(request, "provider_login.html", {
                    "error": "This account is not a provider account"
                })

            except Profile.DoesNotExist:
                return render(request, "provider_login.html", {
                    "error": "Profile not found"
                })

        return render(request, "provider_login.html", {
            "error": "Invalid provider username or password"
        })

    return render(request, "provider_login.html")

@login_required
def profile_menu(request):
    if request.user.profile.role == "provider":
        dashboard_url = "provider_dashboard"
    else:
        dashboard_url = "user_dashboard"

    return render(request, 'profile_menu.html', {
        'dashboard_url': dashboard_url
    })

@login_required
def my_profile(request):
    profile = request.user.profile
    stats = {}

    if profile.role == "provider":
        services = Service.objects.filter(provider=request.user)
        bookings = Booking.objects.filter(provider=request.user)
        reviews = Review.objects.filter(provider=request.user)
        
        stats = {
            'total_services': services.count(),
            'total_bookings': bookings.count(),
            'completed_bookings': bookings.filter(status='Completed').count(),
            'avg_rating': reviews.aggregate(Avg('rating'))['rating__avg'] or 0,
            'review_count': reviews.count()
        }
    else:
        bookings = Booking.objects.filter(user=request.user)
        wishlist = Wishlist.objects.filter(user=request.user)
        
        stats = {
            'total_bookings': bookings.count(),
            'completed_events': bookings.filter(status='Completed').count(),
            'wishlist_count': wishlist.count()
        }

    return render(request, 'my_profile.html', {
        'profile': profile,
        'stats': stats
    })


def settings_page(request):
    return render(request, 'settings.html')


def logout_view(request):
    # Clear all pending messages to prevent them from showing on the home page after logout
    storage = messages.get_messages(request)
    for _ in storage:
        pass
    
    logout(request)
    request.session.flush()
    # No message added here as per user request
    return redirect('home')


@login_required
def user_dashboard(request):
    total_services = Service.objects.count()
    total_packages = Package.objects.count()

    my_bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    upcoming_bookings = my_bookings.filter(status__in=["Pending", "Accepted"])[:5]

    wishlist_count = Wishlist.objects.filter(user=request.user).count()

    recommended_services = Service.objects.annotate(
        avg_rating=Avg('provider__reviews__rating'),
        review_count=Count('provider__reviews')
    ).order_by('-created_at')[:4]
    
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')[:3]

    return render(request, 'user_dashboard.html', {
        'total_services': total_services,
        'total_packages': total_packages,
        'booking_count': my_bookings.count(),
        'wishlist_count': wishlist_count,
        'upcoming_bookings': upcoming_bookings,
        'recommended_services': recommended_services,
        'latest_notifications': notifications,
    })


@login_required
@provider_approved_required
def provider_dashboard(request):
    my_services = Service.objects.filter(provider=request.user).order_by('-created_at')
    my_packages = Package.objects.filter(provider=request.user).order_by('-created_at')

    bookings = Booking.objects.filter(provider=request.user).order_by('-created_at')
    recent_bookings = bookings[:5]

    pending_count = bookings.filter(status="Pending").count()
    accepted_count = bookings.filter(status="Accepted").count()
    rejected_count = bookings.filter(status="Rejected").count()
    completed_count = bookings.filter(status="Completed").count()

    total_earnings_services = bookings.filter(status__in=["Accepted", "Completed"], service__isnull=False).aggregate(
        total=Sum('service__price')
    )['total'] or 0
    total_earnings_packages = bookings.filter(status__in=["Accepted", "Completed"], package__isnull=False).aggregate(
        total=Sum('package__total_price')
    )['total'] or 0
    total_earnings = total_earnings_services + total_earnings_packages

    top_services = my_services.annotate(
        booking_count=Count('booking')
    ).order_by('-booking_count')[:4]

    # Recent Reviews
    recent_reviews = Review.objects.filter(provider=request.user).order_by('-created_at')[:3]

    # Monthly Earnings
    # Note: Complex aggregation across nullable fields for monthly trend
    # We'll just use service price for trend for now, or sum both
    monthly_earnings = bookings.filter(status__in=["Accepted", "Completed"]).values('created_at__month').annotate(
        total_service=Sum('service__price'),
        total_package=Sum('package__total_price')
    ).order_by('-created_at__month')[:6]
    
    # Process monthly earnings to handle None
    for entry in monthly_earnings:
        entry['total'] = (entry['total_service'] or 0) + (entry['total_package'] or 0)

    # Profile Completion Logic
    profile = request.user.profile
    required_fields = [
        profile.business_name, profile.owner_name, profile.service_type, 
        profile.phone, profile.location, profile.profile_image, 
        profile.gst_number, profile.id_proof
    ]
    filled_fields = [f for f in required_fields if f]
    profile_completeness = int((len(filled_fields) / len(required_fields)) * 100)

    # Average Rating
    avg_rating = Review.objects.filter(provider=request.user).aggregate(
        avg=Avg('rating')
    )['avg']

    return render(request, 'provider_dashboard.html', {
        'my_services': my_services,
        'my_packages': my_packages,
        'service_count': my_services.count(),
        'package_count': my_packages.count(),
        'booking_count': bookings.count(),
        'pending_count': pending_count,
        'accepted_count': accepted_count,
        'rejected_count': rejected_count,
        'completed_count': completed_count,
        'recent_bookings': recent_bookings,
        'recent_reviews': recent_reviews,
        'monthly_earnings': monthly_earnings,
        'profile_completeness': profile_completeness,
        'total_earnings': total_earnings,
        'top_services': top_services,
        'avg_rating': avg_rating,
    })
def send_otp_email(email, purpose):
    otp = str(random.randint(100000, 999999))

    EmailOTP.objects.create(
        email=email,
        otp=otp,
        purpose=purpose
    )

    send_mail(
        'EventNest Verification Code',
        f'Your EventNest verification code is: {otp}',
        'eventnest@example.com',
        [email],
        fail_silently=False,
    )
    
def verify_user_otp(request):
    email = request.session.get("user_register_email")

    if not email:
        return redirect("register")

    if request.method == "POST":
        otp = request.POST.get("otp")

        valid_otp = EmailOTP.objects.filter(
            email=email,
            otp=otp,
            purpose="user_register"
        ).last()

        if valid_otp:
            request.session["user_otp_verified"] = True
            return redirect("user_details")

        return render(request, "verify_otp.html", {"error": "Invalid OTP"})

    return render(request, "verify_otp.html", {"purpose": "User Registration"})
    
def verify_provider_otp(request):
    email = request.session.get("provider_register_email")

    if not email:
        return redirect("provider_step1")

    if request.method == "POST":
        otp = request.POST.get("otp")

        valid_otp = EmailOTP.objects.filter(
            email=email,
            otp=otp,
            purpose="provider_register"
        ).last()

        if valid_otp:
            request.session["provider_otp_verified"] = True
            return redirect("provider_step2")

        return render(request, "verify_otp.html", {"error": "Invalid OTP"})

    return render(request, "verify_otp.html", {"purpose": "Provider Registration"})

def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if User.objects.filter(email=email).exists():
            request.session["reset_email"] = email
            send_otp_email(email, "password_reset")
            return redirect("verify_reset_otp")

        return render(request, "forgot_password.html", {"error": "Email not found"})

    return render(request, "forgot_password.html")


def verify_reset_otp(request):
    email = request.session.get("reset_email")

    if not email:
        return redirect("forgot_password")

    if request.method == "POST":
        otp = request.POST.get("otp")

        valid_otp = EmailOTP.objects.filter(
            email=email,
            otp=otp,
            purpose="password_reset"
        ).last()

        if valid_otp:
            request.session["reset_verified"] = True
            return redirect("reset_password")

        return render(request, "verify_reset_otp.html", {"error": "Invalid OTP"})

    return render(request, "verify_reset_otp.html")


def reset_password(request):
    email = request.session.get("reset_email")
    verified = request.session.get("reset_verified")

    if not email or not verified:
        return redirect("forgot_password")

    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            return render(request, "reset_password.html", {"error": "Passwords do not match"})

        user = User.objects.get(email=email)
        user.password = make_password(password)
        user.save()

        request.session.flush()

        return redirect("login")

    return render(request, "reset_password.html")


@login_required(login_url='user_login')
def book_service(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    today = timezone.now().date()

    if request.method == "POST":
        event_date_str = request.POST.get("event_date")
        event_date = timezone.datetime.strptime(event_date_str, "%Y-%m-%d").date()
        number_of_guests = request.POST.get("number_of_guests")
        number_of_days = request.POST.get("number_of_days")
        message = request.POST.get("message")
        
        # Emergency Contact
        emergency_contact_name = request.POST.get("emergency_contact_name")
        emergency_contact_number = request.POST.get("emergency_contact_number")

        # Conflict Detection 1: Check if date is blocked by provider
        is_blocked = AvailabilityBlock.objects.filter(
            provider=service.provider,
            start_date__lte=event_date,
            end_date__gte=event_date
        ).exists()
        
        if is_blocked:
            messages.error(request, "Sorry, the provider is unavailable on this date.")
            return redirect("book_service", service_id=service_id)

        # Conflict Detection 2: Check for existing bookings on same date
        existing_booking = Booking.objects.filter(
            provider=service.provider,
            event_date=event_date,
            status__in=["Pending", "Accepted", "In Progress"]
        ).exists()
        
        if existing_booking:
            messages.error(request, "The provider is already booked for this date.")
            return redirect("book_service", service_id=service_id)

        # Collect dynamic booking details
        extra_booking_details = {}
        for key in request.POST:
            if key.startswith("booking_detail_"):
                val = request.POST.get(key)
                if val:
                    clean_key = key.replace("booking_detail_", "")
                    extra_booking_details[clean_key] = val

        Booking.objects.create(
            user=request.user,
            provider=service.provider,
            service=service,
            event_date=event_date,
            number_of_guests=number_of_guests if number_of_guests else None,
            number_of_days=number_of_days if number_of_days else None,
            message=message,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_number=emergency_contact_number,
            extra_booking_details=extra_booking_details
        )

        Notification.objects.create(
            user=service.provider,
            message=f"New booking request for {service.service_name}"
        )

        messages.success(request, "Booking request sent. Please wait for provider confirmation.")
        return redirect("user_dashboard")

    return render(request, "book_service.html", {"service": service, "today": today})

@login_required(login_url='user_login')
def book_package(request, package_id):
    package = get_object_or_404(Package, id=package_id)
    today = timezone.now().date()

    if request.method == "POST":
        event_date_str = request.POST.get("event_date")
        event_date = timezone.datetime.strptime(event_date_str, "%Y-%m-%d").date()
        number_of_guests = request.POST.get("number_of_guests")
        message = request.POST.get("message")
        selected_variant = request.POST.get("selected_variant", "Basic")
        
        # Emergency Contact
        emergency_contact_name = request.POST.get("emergency_contact_name")
        emergency_contact_number = request.POST.get("emergency_contact_number")

        # Conflict Detection
        is_blocked = AvailabilityBlock.objects.filter(
            provider=package.provider,
            start_date__lte=event_date,
            end_date__gte=event_date
        ).exists()
        
        if is_blocked:
            messages.error(request, "Sorry, the provider is unavailable on this date.")
            return redirect("book_package", package_id=package_id)

        existing_booking = Booking.objects.filter(
            provider=package.provider,
            event_date=event_date,
            status__in=["Pending", "Accepted", "In Progress"]
        ).exists()
        
        if existing_booking:
            messages.error(request, "The provider is already booked for this date.")
            return redirect("book_package", package_id=package_id)

        # Collect dynamic booking details if any
        extra_booking_details = {"variant": selected_variant}
        for key in request.POST:
            if key.startswith("booking_detail_"):
                val = request.POST.get(key)
                if val:
                    extra_booking_details[key.replace("booking_detail_", "")] = val

        Booking.objects.create(
            user=request.user,
            provider=package.provider,
            package=package,
            event_date=event_date,
            number_of_guests=number_of_guests if number_of_guests else None,
            message=message,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_number=emergency_contact_number,
            extra_booking_details=extra_booking_details
        )

        Notification.objects.create(
            user=package.provider,
            message=f"New package booking request for {package.package_name} ({selected_variant})"
        )

        messages.success(request, f"Package '{package.package_name}' booking request sent!")
        return redirect("user_dashboard")

    return render(request, "book_package.html", {"package": package, "today": today})



def about(request):
    notify_count = 0
    notifications = []

    if request.user.is_authenticated:
        notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')
        notify_count = notifications.count()

    return render(request, 'about.html', {
        'notify_count': notify_count,
        'notifications': notifications
    })
    





@login_required(login_url='user_login')
def user_bookings(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "user_bookings.html", {"bookings": bookings})


@login_required(login_url='provider_login')
@provider_approved_required
def provider_bookings(request):
    bookings = Booking.objects.filter(provider=request.user).order_by('-created_at')
    return render(request, "provider_bookings.html", {"bookings": bookings})


@login_required(login_url='provider_login')
@provider_approved_required
def accept_booking(request, booking_id):
    if request.method == "POST":
        booking = get_object_or_404(Booking, id=booking_id, provider=request.user)
        if booking.status == "Pending":
            booking.status = "Accepted"
            booking.save()

            Notification.objects.create(
                user=booking.user,
                message=f"Your booking for {booking.booked_item_name} has been accepted."
            )
            messages.success(request, "Booking accepted.")
        else:
            messages.error(request, "Only pending bookings can be accepted.")
    return redirect("provider_bookings")


@login_required(login_url='provider_login')
@provider_approved_required
def reject_booking(request, booking_id):
    if request.method == "POST":
        booking = get_object_or_404(Booking, id=booking_id, provider=request.user)
        if booking.status == "Pending":
            booking.status = "Rejected"
            booking.save()

            Notification.objects.create(
                user=booking.user,
                message=f"Your booking for {booking.booked_item_name} has been rejected."
            )
            messages.warning(request, "Booking rejected.")
        else:
            messages.error(request, "Only pending bookings can be rejected.")
    return redirect("provider_bookings")


@login_required(login_url='user_login')
def cancel_booking(request, booking_id):
    if request.method == "POST":
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)

        if booking.status in ["Pending", "Accepted"]:
            booking.status = "Cancelled"
            booking.save()

            Notification.objects.create(
                user=booking.provider,
                message=f"{request.user.username} cancelled booking for {booking.booked_item_name}."
            )
            messages.success(request, "Booking cancelled successfully.")
        else:
            messages.error(request, "You cannot cancel this booking now.")

    return redirect("user_bookings")


@login_required(login_url='provider_login')
@provider_approved_required
def start_booking(request, booking_id):
    if request.method == "POST":
        booking = get_object_or_404(Booking, id=booking_id, provider=request.user)
        if booking.status == "Accepted":
            booking.status = "In Progress"
            booking.save()
            Notification.objects.create(
                user=booking.user,
                message=f"Your event for {booking.booked_item_name} is now In Progress."
            )
            messages.success(request, "Event started.")
    return redirect("provider_bookings")

@login_required(login_url='provider_login')
@provider_approved_required
def complete_booking(request, booking_id):
    if request.method == "POST":
        booking = get_object_or_404(Booking, id=booking_id, provider=request.user)

        if booking.status == "In Progress":
            booking.status = "Completed"
            booking.save()

            Notification.objects.create(
                user=booking.user,
                message=f"Your booking for {booking.booked_item_name} is marked as completed."
            )
            messages.success(request, "Booking completed.")
        else:
            messages.error(request, "Booking must be 'In Progress' to mark as complete.")

    return redirect("provider_bookings")

@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    if booking.user != request.user and booking.provider != request.user and not request.user.is_staff:
        messages.error(request, "Access denied.")
        return redirect('home')

    if request.method == "POST" and "add_item" in request.POST:
        task = request.POST.get("task")
        if task:
            ChecklistItem.objects.create(booking=booking, task=task)
            messages.success(request, "Task added to checklist.")
        return redirect("booking_detail", booking_id=booking_id)
        
    checklist = ChecklistItem.objects.filter(booking=booking).order_by('created_at')
    
    return render(request, "booking_detail.html", {
        "booking": booking,
        "checklist": checklist
    })

@login_required
def update_checklist_item(request, item_id):
    item = get_object_or_404(ChecklistItem, id=item_id)
    # Only provider or user can toggle
    if item.booking.user == request.user or item.booking.provider == request.user:
        item.is_completed = not item.is_completed
        item.save()
        return redirect("booking_detail", booking_id=item.booking.id)
    return redirect('home')

@login_required
def delete_checklist_item(request, item_id):
    item = get_object_or_404(ChecklistItem, id=item_id)
    if item.booking.user == request.user or item.booking.provider == request.user:
        booking_id = item.booking.id
        item.delete()
        messages.success(request, "Item removed.")
        return redirect("booking_detail", booking_id=booking_id)
    return redirect('home')

def provider_profile(request, provider_id):
    provider = get_object_or_404(User, id=provider_id)
    profile = get_object_or_404(Profile, user=provider)

    services = Service.objects.filter(provider=provider, is_draft=False).annotate(
        gallery_count=Count("gallery")
    ).order_by('-created_at')
    
    packages = Package.objects.filter(provider=provider, is_draft=False).annotate(
        gallery_count=Count("gallery")
    ).order_by('-created_at')
    
    reviews = Review.objects.filter(provider=provider).order_by('-created_at')
    team_members = TeamMember.objects.filter(provider=provider)
    
    # Fetch images from completed bookings for the portfolio gallery
    completed_bookings = Booking.objects.filter(provider=provider, status="Completed")
    event_gallery = EventGallery.objects.filter(booking__in=completed_bookings).order_by('-created_at')

    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    review_count = reviews.count()

    total_bookings = Booking.objects.filter(provider=provider).count()
    completed_bookings_count = completed_bookings.count()

    return render(request, 'provider_profile.html', {
        'provider': provider,
        'profile': profile,
        'services': services,
        'packages': packages,
        'reviews': reviews,
        'team_members': team_members,
        'event_gallery': event_gallery,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'total_bookings': total_bookings,
        'completed_bookings_count': completed_bookings_count,
    })

@login_required(login_url='provider_login')
@provider_approved_required
def manage_availability(request):
    if request.method == "POST":
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        reason = request.POST.get("reason", "")
        
        if start_date and end_date:
            AvailabilityBlock.objects.create(
                provider=request.user,
                start_date=start_date,
                end_date=end_date,
                reason=reason
            )
            messages.success(request, "Availability updated. Customers cannot book on these dates.")
        else:
            messages.error(request, "Please provide both start and end dates.")
            
        return redirect("manage_availability")

    blocks = AvailabilityBlock.objects.filter(provider=request.user).order_by('start_date')
    return render(request, "manage_availability.html", {"blocks": blocks})

@login_required(login_url='provider_login')
@provider_approved_required
def delete_availability(request, block_id):
    if request.method == "POST":
        block = get_object_or_404(AvailabilityBlock, id=block_id, provider=request.user)
        block.delete()
        messages.success(request, "Block removed.")
    return redirect("manage_availability")

@login_required(login_url='user_login')
def add_review(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status != "Completed":
        messages.error(request, "You can only review completed services.")
        return redirect("user_bookings")

    if hasattr(booking, 'review'):
        messages.info(request, "You have already reviewed this service.")
        return redirect("user_bookings")

    if request.method == "POST":
        rating = request.POST.get("rating")
        comment = request.POST.get("comment")

        Review.objects.create(
            user=request.user,
            provider=booking.provider,
            booking=booking,
            rating=rating,
            comment=comment
        )

        messages.success(request, "Thank you for your feedback!")
        return redirect('user_bookings')

    return render(request, "add_review.html", {"booking": booking})
    
def search_services(request):
    query = request.GET.get("q", "")
    service_type = request.GET.get("service_type", "")
    location = request.GET.get("location", "")
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")
    min_rating = request.GET.get("min_rating", "")

    services = Service.objects.filter(is_draft=False).annotate(
        avg_rating=Avg("provider__reviews__rating"),
        review_count=Count("provider__reviews"),
        gallery_count=Count("gallery")
    ).order_by("-created_at")

    if query:
        services = services.filter(
            Q(service_name__icontains=query) |
            Q(description__icontains=query) |
            Q(location__icontains=query) |
            Q(provider__username__icontains=query)
        )

    if service_type:
        services = services.filter(service_type=service_type)

    if location:
        services = services.filter(location__icontains=location)

    if min_price:
        services = services.filter(price__gte=min_price)
    if max_price:
        services = services.filter(price__lte=max_price)

    if min_rating:
        services = services.filter(avg_rating__gte=min_rating)

    return render(request, "search_services.html", {
        "services": services,
        "service_types": SERVICE_CATEGORIES,
        "locations": POPULAR_LOCATIONS,
        "query": query,
        "selected_type": service_type,
        "location": location,
        "min_price": min_price,
        "max_price": max_price,
        "min_rating": min_rating,
    })

def service_list_by_type(request, type_name):
    services = Service.objects.filter(service_type=type_name).annotate(
        avg_rating=Avg("provider__reviews__rating"),
        review_count=Count("provider__reviews"),
        gallery_count=Count("gallery")
    ).order_by("-created_at")
    
    return render(request, "search_services.html", {
        "services": services,
        "selected_type": type_name,
        "query": "",
        "location": "",
        "min_price": "",
        "max_price": "",
        "min_rating": "",
        "service_types": SERVICE_CATEGORIES,
        "locations": POPULAR_LOCATIONS
    })

@login_required(login_url='user_login')
def make_custom_package(request):
    event_requirements = {
        "Birthday Event": ["Decoration", "Catering", "DJ & Music", "Photography"],
        "Marriage Event": ["Decoration", "Catering", "Photography", "Lighting Setup", "Event Planning"],
        "Office Party": ["Catering", "Lighting Setup", "Event Planning", "Photography"],
        "Bachelor Party": ["DJ & Music", "Catering", "Decoration", "Lighting Setup"],
        "College Event": ["DJ & Music", "Lighting Setup", "Photography", "Event Planning"],
        "Engagement": ["Decoration", "Photography", "Catering", "Event Planning"],
        "Sangeet": ["DJ & Music", "Decoration", "Photography", "Catering"],
        "Cocktail Party": ["Catering", "DJ & Music", "Lighting Setup", "Decoration"],
        "Exhibition": ["Furniture / Tent", "Lighting Setup", "Venue Provider", "Event Planning"],
        "Concert": ["DJ & Music", "Lighting Setup", "Venue Provider", "Host / Anchor", "Photography"],
        "Workshop / Seminar": ["Venue Provider", "Catering", "Furniture / Tent", "Lighting Setup"],
        "House Warming": ["Catering", "Decoration", "Photography"],
        "Naming Ceremony": ["Decoration", "Catering", "Photography", "Host / Anchor"],
        "Religious Event": ["Decoration", "Catering", "Furniture / Tent", "Host / Anchor"],
    }

    selected_event = request.GET.get("event_type", "Birthday Event") # Default to Birthday
    services_by_type = {}

    # Fetch all services grouped by category for the builder
    for category in SERVICE_CATEGORIES:
        services = Service.objects.filter(service_type=category).annotate(avg_rating=Avg('provider__reviews__rating'))
        if services.exists():
            services_by_type[category] = services

    if request.method == "POST":
        event_type = request.POST.get("event_type")
        event_date = request.POST.get("event_date")
        message = request.POST.get("message")
        selected_service_ids = request.POST.getlist("selected_services")

        if not selected_service_ids:
            messages.error(request, "Please select at least one service.")
            return redirect("make_custom_package")

        selected_services = Service.objects.filter(id__in=selected_service_ids)
        total_price = sum(service.price for service in selected_services)

        custom_booking = CustomPackageBooking.objects.create(
            user=request.user,
            event_date=event_date,
            message=message,
            total_price=total_price
        )

        custom_booking.selected_services.set(selected_services)

        for service in selected_services:
            Notification.objects.create(
                user=service.provider,
                message=f"New custom package request for {event_type}: {service.service_name} from {request.user.username}."
            )

        messages.success(request, f"Your custom {event_type} request for ₹{total_price} has been sent!")
        return redirect("user_bookings")

    return render(request, "make_custom_package.html", {
        "event_requirements": event_requirements,
        "selected_event": selected_event,
        "services_by_type": services_by_type,
        "categories": SERVICE_CATEGORIES
    })


@login_required(login_url='user_login')
def add_service_wishlist(request, service_id):
    if request.method == "POST":
        service = get_object_or_404(Service, id=service_id)

        item = Wishlist.objects.filter(
            user=request.user,
            service=service
        ).first()

        if item:
            item.delete()
            messages.success(request, "Removed from wishlist.")
        else:
            Wishlist.objects.create(
                user=request.user,
                service=service
            )
            messages.success(request, "Added to wishlist.")

    return redirect(request.META.get('HTTP_REFERER', 'services'))

@login_required(login_url='user_login')
def add_package_wishlist(request, package_id):
    if request.method == "POST":
        package = get_object_or_404(Package, id=package_id)

        Wishlist.objects.get_or_create(
            user=request.user,
            package=package
        )
        messages.success(request, "Added to wishlist.")

    return redirect(request.META.get('HTTP_REFERER', 'packages'))


@login_required(login_url='user_login')
def remove_wishlist(request, wishlist_id):
    if request.method == "POST":
        item = get_object_or_404(Wishlist, id=wishlist_id, user=request.user)
        item.delete()
        messages.success(request, "Removed from wishlist.")

    return redirect('wishlist')


@login_required(login_url='user_login')
def wishlist(request):
    saved_services = Wishlist.objects.filter(
        user=request.user,
        service__isnull=False
    )

    saved_packages = Wishlist.objects.filter(
        user=request.user,
        package__isnull=False
    )

    return render(request, 'wishlist.html', {
        'saved_services': saved_services,
        'saved_packages': saved_packages
    })
    
@login_required(login_url='provider_login')
@provider_approved_required
def edit_provider_profile(request):
    profile = request.user.profile

    if request.method == "POST":
        profile.business_name = request.POST.get("business_name")
        profile.owner_name = request.POST.get("owner_name")
        profile.phone = request.POST.get("phone")
        profile.location = request.POST.get("location")
        profile.service_type = request.POST.get("service_type")
        profile.experience = request.POST.get("experience")
        profile.bio = request.POST.get("bio")

        if request.FILES.get("profile_image"):
            profile.profile_image = request.FILES.get("profile_image")

        if request.FILES.get("cover_image"):
            profile.cover_image = request.FILES.get("cover_image")

        if request.POST.get("remove_profile_image") == "on":
            profile.profile_image.delete(save=False)
            profile.profile_image = None

        if request.POST.get("remove_cover_image") == "on":
            profile.cover_image.delete(save=False)
            profile.cover_image = None

        profile.save()

        messages.success(request, "Provider profile updated successfully.")
        return redirect("provider_profile", provider_id=request.user.id)

    return render(request, "edit_provider_profile.html", {
        "profile": profile
    })
# Show all notifications page
@login_required
def notifications_page(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    return render(request, 'notifications.html', {
        'notifications': notifications
    })


# Mark single notification as read
@login_required
def mark_as_read(request, notif_id):
    if request.method == "POST":
        notif = get_object_or_404(Notification, id=notif_id, user=request.user)
        notif.is_read = True
        notif.save()
    return redirect('notifications')


# Mark all as read
@login_required
def mark_all_read(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('notifications')

@login_required
def clear_all_notifications(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user).delete()
    return redirect('notifications')


@staff_member_required(login_url='login')
def custom_admin_dashboard(request):
    total_users = Profile.objects.filter(role="user").count()
    total_providers = Profile.objects.filter(role="provider").count()
    pending_providers = Profile.objects.filter(role="provider", is_approved=False).count()
    total_services = Service.objects.count()
    total_packages = Package.objects.count()
    total_bookings = Booking.objects.count()
    pending_bookings = Booking.objects.filter(status="Pending").count()
    completed_bookings = Booking.objects.filter(status="Completed").count()
    cancelled_bookings = Booking.objects.filter(status="Cancelled").count()

    # Calculate total revenue from completed bookings
    rev_services = Booking.objects.filter(status="Completed", service__isnull=False).aggregate(total=Sum('service__price'))['total'] or 0
    rev_packages = Booking.objects.filter(status="Completed", package__isnull=False).aggregate(total=Sum('package__total_price'))['total'] or 0
    total_revenue = rev_services + rev_packages

    recent_bookings = Booking.objects.all().order_by("-created_at")[:8]
    recent_providers = Profile.objects.filter(role="provider").order_by("-id")[:8]
    recent_activities = ActivityLog.objects.all().order_by("-created_at")[:10]
    recent_reviews = Review.objects.all().order_by("-created_at")[:5]

    return render(request, "custom_admin_dashboard.html", {
        "total_users": total_users,
        "total_providers": total_providers,
        "pending_providers": pending_providers,
        "total_services": total_services,
        "total_packages": total_packages,
        "total_bookings": total_bookings,
        "pending_bookings": pending_bookings,
        "completed_bookings": completed_bookings,
        "cancelled_bookings": cancelled_bookings,
        "total_revenue": total_revenue,
        "recent_bookings": recent_bookings,
        "recent_providers": recent_providers,
        "recent_activities": recent_activities,
        "recent_reviews": recent_reviews,
    })


@staff_member_required(login_url='login')
def admin_users(request):
    query = request.GET.get("q", "")
    status_filter = request.GET.get("status", "")
    
    users_list = Profile.objects.filter(role="user").select_related("user")
    
    if query:
        users_list = users_list.filter(
            Q(user__username__icontains=query) | 
            Q(user__email__icontains=query) |
            Q(phone__icontains=query)
        )
        
    if status_filter == "blocked":
        users_list = users_list.filter(is_blocked=True)
    elif status_filter == "active":
        users_list = users_list.filter(is_blocked=False)

    paginator = Paginator(users_list.order_by("-user__date_joined"), 15)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)

    return render(request, "admin_users.html", {
        "users": users, 
        "query": query, 
        "status_filter": status_filter
    })

@staff_member_required(login_url='login')
def admin_user_details(request, user_id):
    profile = get_object_or_404(Profile, id=user_id)
    return render(request, "admin_user_details.html", {"profile": profile})

@staff_member_required(login_url='login')
def delete_user_admin(request, user_id):
    if request.method == "POST":
        profile = get_object_or_404(Profile, id=user_id, role="user")
        profile.user.delete()
        messages.success(request, "User deleted successfully.")
    return redirect("admin_users")


@staff_member_required(login_url='login')
def admin_providers(request):
    query = request.GET.get("q", "")
    status_filter = request.GET.get("status", "")
    
    providers_list = Profile.objects.filter(role="provider").select_related("user")
    
    if query:
        providers_list = providers_list.filter(
            Q(user__username__icontains=query) | 
            Q(business_name__icontains=query) |
            Q(user__email__icontains=query)
        )
        
    if status_filter == "pending":
        providers_list = providers_list.filter(is_approved=False)
    elif status_filter == "approved":
        providers_list = providers_list.filter(is_approved=True)

    paginator = Paginator(providers_list.order_by("-id"), 15)
    page_number = request.GET.get('page')
    providers = paginator.get_page(page_number)

    return render(request, "admin_providers.html", {
        "providers": providers, 
        "query": query, 
        "status_filter": status_filter
    })


@staff_member_required(login_url='login')
def approve_provider(request, profile_id):
    if request.method == "POST":
        profile = get_object_or_404(Profile, id=profile_id, role="provider")
        remark = request.POST.get("remark", "Your account has been approved.")
        profile.is_approved = True
        profile.admin_remark = remark
        profile.save()

        Notification.objects.create(
            user=profile.user,
            message=f"🎉 Verification Successful! Your account is now Verified. You can now list services, packages, and start accepting bookings. {remark}"
        )
        messages.success(request, f"Provider {profile.user.username} approved.")
    return redirect("admin_providers")

@staff_member_required(login_url='login')
def delete_provider_admin(request, profile_id):
    if request.method == "POST":
        profile = get_object_or_404(Profile, id=profile_id, role="provider")
        profile.user.delete() # Deletes User and Profile due to cascade
        messages.success(request, "Provider deleted successfully.")
    return redirect("admin_providers")

@staff_member_required(login_url='login')
def admin_provider_details(request, provider_id):
    profile = get_object_or_404(Profile, id=provider_id, role="provider")
    services = Service.objects.filter(provider=profile.user)
    packages = Package.objects.filter(provider=profile.user)
    return render(request, "admin_provider_details.html", {
        "profile": profile,
        "services": services,
        "packages": packages
    })


@staff_member_required(login_url='login')
def reject_provider(request, profile_id):
    if request.method == "POST":
        profile = get_object_or_404(Profile, id=profile_id, role="provider")
        remark = request.POST.get("remark", "Your application was rejected.")
        profile.is_approved = False
        profile.admin_remark = remark
        profile.save()

        Notification.objects.create(
            user=profile.user,
            message=f"Application Rejected: {remark}"
        )
        messages.warning(request, f"Provider {profile.user.username} rejected.")
    return redirect("admin_providers")


@staff_member_required(login_url='login')
def block_user(request, profile_id):
    if request.method == "POST":
        profile = get_object_or_404(Profile, id=profile_id)
        profile.is_blocked = True
        profile.save()
        messages.warning(request, f"User {profile.user.username} blocked.")
    return redirect(request.META.get("HTTP_REFERER", "custom_admin_dashboard"))


@staff_member_required(login_url='login')
def unblock_user(request, profile_id):
    if request.method == "POST":
        profile = get_object_or_404(Profile, id=profile_id)
        profile.is_blocked = False
        profile.save()
        messages.success(request, f"User {profile.user.username} unblocked.")
    return redirect(request.META.get("HTTP_REFERER", "custom_admin_dashboard"))


@staff_member_required(login_url='login')
def admin_services(request):
    query = request.GET.get("q", "")
    type_filter = request.GET.get("type", "")
    
    services_list = Service.objects.all().select_related("provider")
    
    if query:
        services_list = services_list.filter(
            Q(service_name__icontains=query) | 
            Q(provider__username__icontains=query)
        )
    
    if type_filter:
        services_list = services_list.filter(service_type=type_filter)

    paginator = Paginator(services_list.order_by("-created_at"), 15)
    page_number = request.GET.get('page')
    services = paginator.get_page(page_number)

    return render(request, "admin_services.html", {
        "services": services, 
        "query": query, 
        "type_filter": type_filter,
        "categories": SERVICE_CATEGORIES
    })

@staff_member_required(login_url='login')
def delete_service_admin(request, service_id):
    if request.method == "POST":
        service = get_object_or_404(Service, id=service_id)
        service.delete()
        messages.success(request, "Service deleted successfully.")
    return redirect("admin_services")

@staff_member_required(login_url='login')
def admin_packages(request):
    query = request.GET.get("q", "")
    type_filter = request.GET.get("type", "")
    
    packages_list = Package.objects.all().select_related("provider")
    
    if query:
        packages_list = packages_list.filter(
            Q(package_name__icontains=query) | 
            Q(provider__username__icontains=query)
        )
    
    if type_filter:
        packages_list = packages_list.filter(package_type=type_filter)

    paginator = Paginator(packages_list.order_by("-created_at"), 15)
    page_number = request.GET.get('page')
    packages = paginator.get_page(page_number)

    return render(request, "admin_packages.html", {
        "packages": packages, 
        "query": query, 
        "type_filter": type_filter
    })

@staff_member_required(login_url='login')
def delete_package_admin(request, package_id):
    if request.method == "POST":
        package = get_object_or_404(Package, id=package_id)
        package.delete()
        messages.success(request, "Package deleted successfully.")
    return redirect("admin_packages")

@staff_member_required(login_url='login')
def admin_bookings(request):
    query = request.GET.get("q", "")
    status_filter = request.GET.get("status", "")
    
    bookings_list = Booking.objects.all().select_related("user", "provider", "service", "package")
    
    if query:
        bookings_list = bookings_list.filter(
            Q(id__icontains=query) | 
            Q(user__username__icontains=query) | 
            Q(provider__username__icontains=query)
        )
    
    if status_filter:
        bookings_list = bookings_list.filter(status=status_filter)

    paginator = Paginator(bookings_list.order_by("-created_at"), 15)
    page_number = request.GET.get('page')
    bookings = paginator.get_page(page_number)

    return render(request, "admin_bookings.html", {
        "bookings": bookings, 
        "query": query, 
        "status_filter": status_filter
    })

@staff_member_required(login_url='login')
def delete_booking_admin(request, booking_id):
    if request.method == "POST":
        booking = get_object_or_404(Booking, id=booking_id)
        booking.delete()
        messages.success(request, "Booking record deleted.")
    return redirect("admin_bookings")

@staff_member_required(login_url='login')
def admin_reviews(request):
    query = request.GET.get("q", "")
    rating_filter = request.GET.get("rating", "")
    
    reviews_list = Review.objects.all().select_related("user", "provider")
    
    if query:
        reviews_list = reviews_list.filter(
            Q(comment__icontains=query) | 
            Q(user__username__icontains=query) | 
            Q(provider__username__icontains=query)
        )
    
    if rating_filter:
        reviews_list = reviews_list.filter(rating=rating_filter)

    paginator = Paginator(reviews_list.order_by("-created_at"), 15)
    page_number = request.GET.get('page')
    reviews = paginator.get_page(page_number)

    return render(request, "admin_reviews.html", {
        "reviews": reviews, 
        "query": query, 
        "rating_filter": rating_filter
    })


@staff_member_required(login_url='login')
def delete_review_admin(request, review_id):
    if request.method == "POST":
        review = get_object_or_404(Review, id=review_id)
        review.delete()
        messages.success(request, "Review deleted successfully.")
    return redirect("admin_reviews")



@staff_member_required(login_url='login')
def admin_notifications(request):
    query = request.GET.get("q", "")
    notifications_list = Notification.objects.all().select_related("user")
    
    if query:
        notifications_list = notifications_list.filter(
            Q(message__icontains=query) | 
            Q(user__username__icontains=query)
        )

    paginator = Paginator(notifications_list.order_by("-created_at"), 20)
    page_number = request.GET.get('page')
    notifications = paginator.get_page(page_number)

    return render(request, "admin_notifications.html", {
        "notifications": notifications, 
        "query": query
    })

@staff_member_required(login_url='login')
def delete_notification_admin(request, notification_id):
    if request.method == "POST":
        notification = get_object_or_404(Notification, id=notification_id)
        notification.delete()
        messages.success(request, "Notification cleared.")
    return redirect("admin_notifications")

@staff_member_required(login_url='login')
def admin_database_explorer(request):
    model_stats = [
        {"name": "Users / Profiles", "count": Profile.objects.count(), "url": "admin_users", "icon": "fa-users"},
        {"name": "Services", "count": Service.objects.count(), "url": "admin_services", "icon": "fa-briefcase"},
        {"name": "Packages", "count": Package.objects.count(), "url": "admin_packages", "icon": "fa-box-open"},
        {"name": "Bookings", "count": Booking.objects.count(), "url": "admin_bookings", "icon": "fa-calendar-check"},
        {"name": "Reviews", "count": Review.objects.count(), "url": "admin_reviews", "icon": "fa-star"},
        {"name": "Notifications", "count": Notification.objects.count(), "url": "admin_notifications", "icon": "fa-bell"},
        {"name": "Activity Logs", "count": ActivityLog.objects.count(), "url": "#", "icon": "fa-list-ul"},
        {"name": "Availability Blocks", "count": AvailabilityBlock.objects.count(), "url": "#", "icon": "fa-calendar-minus"},
        {"name": "Team Members", "count": TeamMember.objects.count(), "url": "#", "icon": "fa-user-group"},
        {"name": "Event Galleries", "count": EventGallery.objects.count(), "url": "#", "icon": "fa-images"},
        {"name": "Checklist Items", "count": ChecklistItem.objects.count(), "url": "#", "icon": "fa-tasks"},
    ]
    
    return render(request, "admin_database_explorer.html", {
        "model_stats": model_stats
    })

@staff_member_required(login_url='login')
def admin_home(request):
    pending_count = Profile.objects.filter(role="provider", is_approved=False).count()
    return render(request, "admin_home.html", {"pending_count": pending_count})

@staff_member_required(login_url='login')
def admin_user_details(request, user_id):
    profile = get_object_or_404(Profile, id=user_id, role="user")
    bookings = Booking.objects.filter(user=profile.user).order_by("-created_at")
    return render(request, "admin_user_details.html", {
        "profile": profile,
        "bookings": bookings
    })

@staff_member_required(login_url='login')
def admin_provider_details(request, provider_id):
    profile = get_object_or_404(Profile, id=provider_id, role="provider")
    services = Service.objects.filter(provider=profile.user).order_by("-created_at")
    packages = Package.objects.filter(provider=profile.user).order_by("-created_at")
    return render(request, "admin_provider_details.html", {
        "profile": profile,
        "services": services,
        "packages": packages
    })

@staff_member_required(login_url='login')
def delete_user_admin(request, user_id):
    if request.method == "POST":
        profile = get_object_or_404(Profile, id=user_id)
        user = profile.user
        user.delete()
        messages.success(request, "User and associated data deleted successfully.")
    return redirect(request.META.get("HTTP_REFERER", "admin_users"))

@staff_member_required(login_url='login')
def delete_provider_admin(request, provider_id):
    if request.method == "POST":
        profile = get_object_or_404(Profile, id=provider_id)
        user = profile.user
        user.delete()
        messages.success(request, "Provider and associated data deleted successfully.")
    return redirect(request.META.get("HTTP_REFERER", "admin_providers"))

@staff_member_required(login_url='login')
def delete_booking_admin(request, booking_id):
    if request.method == "POST":
        booking = get_object_or_404(Booking, id=booking_id)
        booking.delete()
        messages.success(request, "Booking deleted successfully.")
    return redirect(request.META.get("HTTP_REFERER", "admin_bookings"))

@login_required(login_url='login')
def settings_view(request):
    if not hasattr(request.user, 'profile'):
        messages.error(request, "Profile not found. Please contact support.")
        return redirect('home')
        
    profile = request.user.profile
    activities = ActivityLog.objects.filter(user=request.user).order_by("-created_at")[:10]

    if request.method == "POST":
        action = request.POST.get("action")

        # PROFILE UPDATE
        if action == "profile":
            request.user.first_name = request.POST.get("first_name")
            request.user.email = request.POST.get("email")
            request.user.save()

            profile.phone = request.POST.get("phone")
            profile.location = request.POST.get("location")

            if profile.role == "provider":
                profile.business_name = request.POST.get("business_name")
                profile.owner_name = request.POST.get("owner_name")
                profile.service_type = request.POST.get("service_type")
                profile.experience = request.POST.get("experience")
                profile.bio = request.POST.get("bio")

                if request.FILES.get("profile_image"):
                    profile.profile_image = request.FILES.get("profile_image")

                if request.FILES.get("cover_image"):
                    profile.cover_image = request.FILES.get("cover_image")

            profile.save()
            ActivityLog.objects.create(user=request.user, action="Profile Updated", details="Changed personal or business information.")
            messages.success(request, "Profile updated successfully.")
            return redirect("settings")

        # PASSWORD CHANGE
        if action == "security":
            old_password = request.POST.get("old_password")
            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")

            if not request.user.check_password(old_password):
                messages.error(request, "Old password is incorrect.")
                return redirect("settings")

            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
                return redirect("settings")

            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            ActivityLog.objects.create(user=request.user, action="Password Changed", details="User updated account security credentials.")

            messages.success(request, "Password changed successfully.")
            return redirect("settings")

        # NOTIFICATIONS
        if action == "notifications":
            profile.notify_booking_updates = "notify_booking_updates" in request.POST
            profile.notify_offers = "notify_offers" in request.POST
            profile.save()

            messages.success(request, "Notification settings updated.")
            return redirect("settings")

        # USER PREFERENCES
        if action == "preferences":
            profile.preferred_location = request.POST.get("preferred_location")
            profile.preferred_category = request.POST.get("preferred_category")
            guest_count = request.POST.get("default_guest_count")
            profile.default_guest_count = int(guest_count) if guest_count and guest_count.isdigit() else None
            profile.save()

            messages.success(request, "Preferences updated.")
            return redirect("settings")

        # PROVIDER BOOKING SETTINGS
        if action == "provider_booking":
            profile.auto_accept_bookings = "auto_accept_bookings" in request.POST
            profile.is_available = "is_available" in request.POST
            profile.save()

            messages.success(request, "Booking settings updated.")
            return redirect("settings")

        # PROVIDER VERIFICATION
        if action == "verification":
            profile.gst_number = request.POST.get("gst_number")
            profile.fssai_number = request.POST.get("fssai_number")

            if request.FILES.get("id_proof"):
                profile.id_proof = request.FILES.get("id_proof")

            if request.FILES.get("business_certificate"):
                profile.business_certificate = request.FILES.get("business_certificate")

            profile.save()

            messages.success(request, "Verification details submitted.")
            return redirect("settings")

        # DEACTIVATE ACCOUNT
        if action == "deactivate":
            profile.is_deactivated = True
            profile.save()
            messages.success(request, "Your account has been deactivated.")
            return redirect("logout")

    return render(request, "settings.html", {
        "profile": profile,
        "activities": activities
    })


from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    ActivityLog.objects.create(user=user, action="Account Login", details="Signed in to EventNest platform.")


@login_required
def booking_invoice(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    # Only user who booked or the provider can see the invoice
    if request.user != booking.user and request.user != booking.provider:
        return redirect('home')

    return render(request, 'invoice.html', {'booking': booking})
@login_required
def plan_event(request):
    recommendations = None
    if request.method == "POST":
        event_type = request.POST.get("event_type")
        
        # Safely parse budget and guest_count
        try:
            budget_raw = request.POST.get("budget", "0")
            budget = float(budget_raw) if budget_raw.strip() else 0
        except ValueError:
            budget = 0
            
        try:
            guest_raw = request.POST.get("guest_count", "0")
            guest_count = int(guest_raw) if guest_raw.strip() else 0
        except ValueError:
            guest_count = 0
            
        location = request.POST.get("location")
        
        recommendations = get_event_recommendations(event_type, budget, guest_count, location)

    return render(request, "plan_event.html", {
        "recommendations": recommendations,
        "event_types": SERVICE_CATEGORIES,
        "locations": POPULAR_LOCATIONS
    })
