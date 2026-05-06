from .models import Notification

def notification_data(request):
    if request.user.is_authenticated:
        unread = Notification.objects.filter(user=request.user, is_read=False)
        return {
            'unread_notifications': unread[:5],  # only latest 5
            'unread_count': unread.count()
        }
    return {}