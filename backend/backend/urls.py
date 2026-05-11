from django.contrib import admin
from django.urls import path
from events import views
from django.conf import settings
from django.conf.urls.static import static





urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.home, name='home'),

    path('login/', views.login_choice, name='login'),
    path('user-login/', views.login_view, name='user_login'),

    path('register/', views.register_choice, name='register'),
    path('user-register/', views.register_view, name='user_register'),
    path('user-register/details/', views.user_details, name='user_details'),
    path('user-home/', views.user_home, name='user_home'),

    path('provider-login/', views.provider_login, name='provider_login'),
    path('provider-register/', views.provider_step1, name='provider_step1'),
    path('provider-register/basic/', views.provider_step2, name='provider_step2'),
    path('provider-register/contact/', views.provider_step3, name='provider_step3'),
    path('provider-register/service/', views.provider_step4, name='provider_step4'),
    path('provider-home/', views.provider_home, name='provider_home'),
    path('provider/pending/', views.pending_approval, name='pending_approval'),

    path('list-service/', views.list_service, name='list_service'),
    path('edit-service/<int:service_id>/', views.edit_service, name='edit_service'),
    path('delete-service/<int:service_id>/', views.delete_service, name='delete_service'),
    path('list-package/', views.list_package, name='list_package'),
    path('edit-package/<int:package_id>/', views.edit_package, name='edit_package'),
    path('delete-package/<int:package_id>/', views.delete_package, name='delete_package'),
    path('duplicate-package/<int:package_id>/', views.duplicate_package, name='duplicate_package'),

    path('profile-menu/', views.profile_menu, name='profile_menu'),
    path('my-profile/', views.my_profile, name='my_profile'),
    path('logout/', views.logout_view, name='logout'),

    path('services/', views.services, name='services'),
    path('services/<path:type_name>/', views.service_list_by_type, name='service_by_type'),

    path('packages/', views.packages, name='packages'),
    path('contact/', views.contact, name='contact'),
    path('custom-package/', views.custom_package, name='custom_package'),
    path('packages/<path:type_name>/', views.package_by_type, name='package_by_type'),
    
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),
    path('provider-dashboard/', views.provider_dashboard, name='provider_dashboard'),
    
    path('verify-user-otp/', views.verify_user_otp, name='verify_user_otp'),
    path('verify-provider-otp/', views.verify_provider_otp, name='verify_provider_otp'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-reset-otp/', views.verify_reset_otp, name='verify_reset_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    
    path('book-service/<int:service_id>/', views.book_service, name='book_service'),
    path('provider-bookings/', views.provider_bookings, name='provider_bookings'),
    path('accept-booking/<int:booking_id>/', views.accept_booking, name='accept_booking'),
    path('reject-booking/<int:booking_id>/', views.reject_booking, name='reject_booking'),
    path('user-bookings/', views.user_bookings, name='user_bookings'),
    
    path('about/', views.about, name='about'),
    path('make-custom-package/', views.make_custom_package, name='make_custom_package'),
    
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('start-booking/<int:booking_id>/', views.start_booking, name='start_booking'),
    path('complete-booking/<int:booking_id>/', views.complete_booking, name='complete_booking'),
    path('booking-detail/<int:booking_id>/', views.booking_detail, name='booking_detail'),
    path('provider/<int:provider_id>/', views.provider_profile, name='provider_profile'),
    path('add-review/<int:booking_id>/', views.add_review, name='add_review'),
    
    path('search-services/', views.search_services, name='search_services'),
    path('plan-event/', views.plan_event, name='plan_event'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/service/<int:service_id>/', views.add_service_wishlist, name='add_service_wishlist'),
    path('booking-invoice/<int:booking_id>/', views.booking_invoice, name='booking_invoice'),
    path('wishlist/package/<int:package_id>/', views.add_package_wishlist, name='add_package_wishlist'),
    path('wishlist/remove/<int:wishlist_id>/', views.remove_wishlist, name='remove_wishlist'),
    path('edit-provider-profile/', views.edit_provider_profile, name='edit_provider_profile'),
    path('notifications/', views.notifications_page, name='notifications'),
    path('notification/read/<int:notif_id>/', views.mark_as_read, name='mark_as_read'),
    path('notification/read-all/', views.mark_all_read, name='mark_all_read'),
    path('notification/clear-all/', views.clear_all_notifications, name='clear_all_notifications'),
    
    
    path('custom-admin/', views.custom_admin_dashboard, name='custom_admin_dashboard'),
    path('custom-admin/users/', views.admin_users, name='admin_users'),
    path('custom-admin/providers/', views.admin_providers, name='admin_providers'),
    path('custom-admin/provider/approve/<int:profile_id>/', views.approve_provider, name='approve_provider'),
    path('custom-admin/provider/reject/<int:profile_id>/', views.reject_provider, name='reject_provider'),
    path('custom-admin/block/<int:profile_id>/', views.block_user, name='block_user'),
    path('custom-admin/unblock/<int:profile_id>/', views.unblock_user, name='unblock_user'),
    path('custom-admin/services/', views.admin_services, name='admin_services'),
    path('custom-admin/services/delete/<int:service_id>/', views.delete_service_admin, name='delete_service_admin'),
    path('custom-admin/user/details/<int:user_id>/', views.admin_user_details, name='admin_user_details'),
    path('custom-admin/user/delete/<int:user_id>/', views.delete_user_admin, name='delete_user_admin'),
    path('custom-admin/booking/delete/<int:booking_id>/', views.delete_booking_admin, name='delete_booking_admin'),

    path('custom-admin/packages/', views.admin_packages, name='admin_packages'),
    path('custom-admin/packages/delete/<int:package_id>/', views.delete_package_admin, name='delete_package_admin'),
    path('custom-admin/provider/details/<int:provider_id>/', views.admin_provider_details, name='admin_provider_details'),
    path('custom-admin/provider/delete/<int:provider_id>/', views.delete_provider_admin, name='delete_provider_admin'),

    path('custom-admin/bookings/', views.admin_bookings, name='admin_bookings'),
    path('custom-admin/reviews/', views.admin_reviews, name='admin_reviews'),
    path('custom-admin/reviews/delete/<int:review_id>/', views.delete_review_admin, name='delete_review_admin'),
    path('custom-admin/notifications/', views.admin_notifications, name='admin_notifications'),
    path('custom-admin/notifications/delete/<int:notification_id>/', views.delete_notification_admin, name='delete_notification_admin'),
    path('custom-admin/database-explorer/', views.admin_database_explorer, name='admin_database_explorer'),
    path('admin-home/', views.admin_home, name='admin_home'),
    path('settings/', views.settings_view, name='settings'),
    path('book-package/<int:package_id>/', views.book_package, name='book_package'),
    path('manage-availability/', views.manage_availability, name='manage_availability'),
    path('delete-availability/<int:block_id>/', views.delete_availability, name='delete_availability'),
    path('checklist/toggle/<int:item_id>/', views.update_checklist_item, name='update_checklist_item'),
    path('checklist/delete/<int:item_id>/', views.delete_checklist_item, name='delete_checklist_item'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
