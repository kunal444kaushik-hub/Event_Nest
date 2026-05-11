from .models import Service, Package
from django.db.models import Avg, Q

def get_event_recommendations(event_type, budget, guest_count, location=None):
    """
    Lightweight rule-based recommendation engine for event planning.
    Returns a dictionary with suggested services and packages.
    """
    recommendations = {
        'packages': [],
        'services': [],
        'estimated_total': 0,
        'status': 'success'
    }

    # 1. Suggest Packages matching event type and budget
    package_query = Q(package_type__icontains=event_type) | Q(occasion__icontains=event_type)
    if budget:
        package_query &= Q(total_price__lte=budget)
    
    suggested_packages = Package.objects.filter(
        package_query, 
        is_draft=False
    ).annotate(avg_rating=Avg('provider__reviews__rating')).order_by('-avg_rating', 'total_price')

    if location:
        suggested_packages = suggested_packages.filter(location_coverage__icontains=location)

    recommendations['packages'] = suggested_packages[:3]

    # 2. Suggest individual Services if no packages or for custom build
    # We prioritize key services: Venue, Catering, Decoration, Photography
    essential_categories = ["Venue Provider", "Catering", "Decoration", "Photography"]
    
    for category in essential_categories:
        service_query = Q(service_type__icontains=category)
        if budget:
            # Assume a rough split of budget for each category (simplified logic)
            cat_budget = budget / 4 
            service_query &= Q(price__lte=cat_budget)
        
        suggested_services = Service.objects.filter(
            service_query,
            is_draft=False
        ).annotate(avg_rating=Avg('provider__reviews__rating')).order_by('-avg_rating', 'price')

        if location:
            suggested_services = suggested_services.filter(location__icontains=location)
        
        if suggested_services.exists():
            recommendations['services'].append(suggested_services.first())
            recommendations['estimated_total'] += suggested_services.first().price

    if not recommendations['packages'] and not recommendations['services']:
        recommendations['status'] = 'no_results'

    return recommendations
