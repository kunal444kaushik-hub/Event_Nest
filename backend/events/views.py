import random
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password

from django.db.models import Count, Sum, Avg, Q
from .models import Profile, Service, Package, Notification, EmailOTP, Booking, CustomPackageBooking, Wishlist, Review, PackageImage, ActivityLog

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
from django.shortcuts import get_object_or_404
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone





def home(request):
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('admin_home')
        
        # Safety check for profile existence
        if hasattr(request.user, 'profile'):
            if request.user.profile.role == 'provider':
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
def provider_home(request):
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by('-created_at')
    return render(request, 'provider_home.html', {
        'notifications': notifications,
        'notify_count': notifications.count()
    })

def services(request):
    return render(request, 'services.html')




@login_required(login_url='login')
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
            extra_details=extra_details
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

def packages(request):
    event_types = [
        "Birthday Package",
        "Marriage Package",
        "Office Party Package",
        "Bachelor Party Package",
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
        {"name": "Corporate", "icon": "fa-briefcase"},
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
            image=image
        )
        
        # Save gallery images
        for img in gallery_images:
            PackageImage.objects.create(package=package, image=img)

        Notification.objects.create(
            user=request.user,
            message=f"Success! Your professional combo package '{package_name}' has been listed."
        )

        messages.success(request, f"Package '{package_name}' listed successfully!")
        ActivityLog.objects.create(user=request.user, action="Package Listed", details=f"Created professional bundle: {package_name}")
        return redirect("provider_dashboard")

    # Pass provider's own services for the builder
    my_services = Service.objects.filter(provider=request.user)
    
    return render(request, "list_package.html", {"my_services": my_services})


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

        messages.success(request, "Registration successful! Welcome to EventNest.")
        return redirect("provider_home")

    return render(request, "provider_step4.html")


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
    logout(request)
    request.session.flush()
    messages.success(request, "You have been logged out successfully.")
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

    return render(request, 'user_dashboard.html', {
        'total_services': total_services,
        'total_packages': total_packages,
        'booking_count': my_bookings.count(),
        'wishlist_count': wishlist_count,
        'upcoming_bookings': upcoming_bookings,
        'recommended_services': recommended_services,
    })


@login_required
def provider_dashboard(request):
    my_services = Service.objects.filter(provider=request.user).order_by('-created_at')
    my_packages = Package.objects.filter(provider=request.user).order_by('-created_at')

    bookings = Booking.objects.filter(provider=request.user).order_by('-created_at')
    recent_bookings = bookings[:5]

    pending_count = bookings.filter(status="Pending").count()
    accepted_count = bookings.filter(status="Accepted").count()
    rejected_count = bookings.filter(status="Rejected").count()
    completed_count = bookings.filter(status="Completed").count()

    total_earnings = bookings.filter(status__in=["Accepted", "Completed"]).aggregate(
        total=Sum('service__price')
    )['total'] or 0

    top_services = my_services.annotate(
        booking_count=Count('booking')
    ).order_by('-booking_count')[:4]

    # Recent Reviews
    recent_reviews = Review.objects.filter(provider=request.user).order_by('-created_at')[:3]

    # Simple Monthly Earnings (simulated for UI)
    monthly_earnings = bookings.filter(status__in=["Accepted", "Completed"]).values('created_at__month').annotate(
        total=Sum('service__price')
    ).order_by('-created_at__month')[:6]

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
        # ... (POST logic remains same)
        event_date = request.POST.get("event_date")
        number_of_guests = request.POST.get("number_of_guests")
        number_of_days = request.POST.get("number_of_days")
        message = request.POST.get("message")

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
            extra_booking_details=extra_booking_details
        )

        Notification.objects.create(
            user=service.provider,
            message=f"New booking request for {service.service_name}"
        )

        messages.success(request, "Booking request sent. Please wait for provider confirmation.")
        ActivityLog.objects.create(user=request.user, action="Service Booked", details=f"Sent booking request for: {service.service_name}")
        return redirect("user_bookings")

    return render(request, "book_service.html", {"service": service, "today": today})

@login_required(login_url='user_login')
def book_package(request, package_id):
    package = Package.objects.get(id=package_id)

    if request.method == "POST":
        event_date = request.POST.get("event_date")
        number_of_guests = request.POST.get("number_of_guests")
        message = request.POST.get("message")
        selected_variant = request.POST.get("selected_variant", "Basic")

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
            extra_booking_details=extra_booking_details
        )

        Notification.objects.create(
            user=package.provider,
            message=f"New package booking request for {package.package_name} ({selected_variant})"
        )

        messages.success(request, f"Package '{package.package_name}' booking request sent!")
        ActivityLog.objects.create(user=request.user, action="Package Booked", details=f"Booked professional bundle: {package.package_name}")
        return redirect("user_bookings")

    return render(request, "book_package.html", {"package": package})



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
def provider_bookings(request):
    bookings = Booking.objects.filter(provider=request.user).order_by('-created_at')
    return render(request, "provider_bookings.html", {"bookings": bookings})


@login_required(login_url='provider_login')
def accept_booking(request, booking_id):
    booking = Booking.objects.get(id=booking_id, provider=request.user)
    booking.status = "Accepted"
    booking.save()

    Notification.objects.create(
        user=booking.user,
        message=f"Your booking for {booking.booked_item_name} has been accepted."
    )

    return redirect("provider_bookings")


@login_required(login_url='provider_login')
def reject_booking(request, booking_id):
    booking = Booking.objects.get(id=booking_id, provider=request.user)
    booking.status = "Rejected"
    booking.save()

    Notification.objects.create(
        user=booking.user,
        message=f"Your booking for {booking.booked_item_name} has been rejected."
    )

    return redirect("provider_bookings")


@login_required(login_url='user_login')
def cancel_booking(request, booking_id):
    booking = Booking.objects.get(id=booking_id, user=request.user)

    if booking.status == "Pending":
        booking.status = "Cancelled"
        booking.save()

        Notification.objects.create(
            user=booking.provider,
            message=f"{request.user.username} cancelled booking for {booking.booked_item_name}."
        )

    return redirect("user_bookings")


@login_required(login_url='provider_login')
def complete_booking(request, booking_id):
    booking = Booking.objects.get(id=booking_id, provider=request.user)

    if booking.status == "Accepted":
        booking.status = "Completed"
        booking.save()

        Notification.objects.create(
            user=booking.user,
            message=f"Your booking for {booking.booked_item_name} is marked as completed."
        )

    return redirect("provider_bookings")

def provider_profile(request, provider_id):
    provider = User.objects.get(id=provider_id)
    profile = Profile.objects.get(user=provider)

    services = Service.objects.filter(provider=provider).annotate(
        gallery_count=Count("gallery")
    ).order_by('-created_at')
    packages = Package.objects.filter(provider=provider).annotate(
        gallery_count=Count("gallery")
    ).order_by('-created_at')
    reviews = Review.objects.filter(provider=provider).order_by('-created_at')

    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    review_count = reviews.count()

    total_bookings = Booking.objects.filter(provider=provider).count()
    completed_bookings = Booking.objects.filter(provider=provider, status="Completed").count()

    return render(request, 'provider_profile.html', {
        'provider': provider,
        'profile': profile,
        'services': services,
        'packages': packages,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'total_bookings': total_bookings,
        'completed_bookings': completed_bookings,
        'service_count': services.count(),
        'package_count': packages.count(),
    })
    
@login_required(login_url='user_login')
def add_review(request, provider_id):
    provider = User.objects.get(id=provider_id)

    if request.method == "POST":
        rating = request.POST.get("rating")
        comment = request.POST.get("comment")

        Review.objects.create(
            user=request.user,
            provider=provider,
            rating=rating,
            comment=comment
        )

        return redirect('provider_profile', provider_id=provider.id)
    
def search_services(request):
    query = request.GET.get("q", "")
    service_type = request.GET.get("service_type", "")
    location = request.GET.get("location", "")
    min_price = request.GET.get("min_price", "")
    max_price = request.GET.get("max_price", "")
    min_rating = request.GET.get("min_rating", "")

    services = Service.objects.all().annotate(
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
    service = Service.objects.get(id=service_id)

    item = Wishlist.objects.filter(
        user=request.user,
        service=service
    ).first()

    if item:
        item.delete()
    else:
        Wishlist.objects.create(
            user=request.user,
            service=service
        )

    return redirect(request.META.get('HTTP_REFERER', 'services'))

@login_required(login_url='user_login')
def add_package_wishlist(request, package_id):
    package = Package.objects.get(id=package_id)

    Wishlist.objects.get_or_create(
        user=request.user,
        package=package
    )

    return redirect(request.META.get('HTTP_REFERER', 'packages'))


@login_required(login_url='user_login')
def remove_wishlist(request, wishlist_id):
    item = Wishlist.objects.get(id=wishlist_id, user=request.user)
    item.delete()

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
    notif = Notification.objects.get(id=notif_id, user=request.user)
    notif.is_read = True
    notif.save()

    return redirect('notifications')


# Mark all as read
@login_required
def mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect('notifications')

@login_required
def clear_all_notifications(request):
    Notification.objects.filter(user=request.user).delete()
    return redirect('notifications')


@staff_member_required(login_url='login')
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

    # Calculate total revenue from completed bookings
    total_revenue = Booking.objects.filter(status="Completed").aggregate(total=Sum('service__price'))['total'] or 0

    recent_bookings = Booking.objects.all().order_by("-created_at")[:5]
    recent_providers = Profile.objects.filter(role="provider").order_by("-id")[:5]

    return render(request, "custom_admin_dashboard.html", {
        "total_users": total_users,
        "total_providers": total_providers,
        "pending_providers": pending_providers,
        "total_services": total_services,
        "total_packages": total_packages,
        "total_bookings": total_bookings,
        "pending_bookings": pending_bookings,
        "completed_bookings": completed_bookings,
        "total_revenue": total_revenue,
        "recent_bookings": recent_bookings,
        "recent_providers": recent_providers,
    })


@staff_member_required(login_url='login')
def admin_users(request):
    users = Profile.objects.filter(role="user").select_related("user")
    return render(request, "admin_users.html", {"users": users})


@staff_member_required(login_url='login')
def admin_providers(request):
    providers = Profile.objects.filter(role="provider").select_related("user")
    return render(request, "admin_providers.html", {"providers": providers})


@staff_member_required(login_url='login')
def approve_provider(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id, role="provider")
    profile.is_approved = True
    profile.save()

    Notification.objects.create(
        user=profile.user,
        message="Your provider account has been approved by admin. You can now login."
    )

    return redirect("admin_providers")


@staff_member_required(login_url='login')
def reject_provider(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id, role="provider")
    user = profile.user
    user.delete()
    return redirect("admin_providers")


@staff_member_required(login_url='login')
def block_user(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)
    profile.is_blocked = True
    profile.save()
    return redirect(request.META.get("HTTP_REFERER", "custom_admin_dashboard"))


@staff_member_required(login_url='login')
def unblock_user(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)
    profile.is_blocked = False
    profile.save()
    return redirect(request.META.get("HTTP_REFERER", "custom_admin_dashboard"))


@staff_member_required(login_url='login')
def admin_services(request):
    services = Service.objects.all().order_by("-created_at")
    return render(request, "admin_services.html", {"services": services})


@staff_member_required(login_url='login')
def delete_service_admin(request, service_id):
    service = get_object_or_404(Service, id=service_id)
    service.delete()
    return redirect("admin_services")


@staff_member_required(login_url='login')
def admin_packages(request):
    packages = Package.objects.all().order_by("-created_at")
    return render(request, "admin_packages.html", {"packages": packages})


@staff_member_required(login_url='login')
def delete_package_admin(request, package_id):
    package = get_object_or_404(Package, id=package_id)
    package.delete()
    return redirect("admin_packages")


@staff_member_required(login_url='login')
def admin_bookings(request):
    bookings = Booking.objects.all().order_by("-created_at")
    return render(request, "admin_bookings.html", {"bookings": bookings})


@staff_member_required(login_url='login')
def admin_reviews(request):
    reviews = Review.objects.all().order_by("-created_at")
    return render(request, "admin_reviews.html", {"reviews": reviews})


@staff_member_required(login_url='login')
def delete_review_admin(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    return redirect("admin_reviews")



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
    profile = get_object_or_404(Profile, id=user_id)
    user = profile.user
    user.delete()
    messages.success(request, "User and associated data deleted successfully.")
    return redirect("admin_users")

@staff_member_required(login_url='login')
def delete_provider_admin(request, provider_id):
    profile = get_object_or_404(Profile, id=provider_id)
    user = profile.user
    user.delete()
    messages.success(request, "Provider and associated data deleted successfully.")
    return redirect("admin_providers")

@staff_member_required(login_url='login')
def delete_booking_admin(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    user_id = booking.user.profile.id
    booking.delete()
    messages.success(request, "Booking deleted successfully.")
    return redirect("admin_user_details", user_id=user_id)

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
            profile.default_guest_count = request.POST.get("default_guest_count") or None
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
