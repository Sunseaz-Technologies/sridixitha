from django.urls import path
from .views import *
from .exports import export_dashboard_excel
from .cart_views import AddToCartView, RemoveFromCartView, ClearCartView, CartView, CheckoutView, BookingSuccessView


urlpatterns = [

    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    # path('send-otp/', SendOTPView.as_view(), name='send_otp'),
    # path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('customer-dashboard/', CustomerDashboardView.as_view(), name='customer_dashboard'),
    path('admin-dashboard/', AdminDashboardView.as_view(), name='admin_dashboard'),
    path('vendor-dashboard/', VendorDashboardView.as_view(), name='vendor_dashboard'),
    path('superadmin-dashboard/', SuperDashboardView.as_view(), name='superadmin_dashboard'),
    path('set-user-status/<int:user_id>/<str:status>/', SetUserStatusView.as_view(), name='set_user_status'),
    path('create_admin/', CreateAdminView.as_view(), name='create_admin'),
    path("superadmin/edit-admin/<int:id>/",EditAdminView.as_view(),name="edit_admin"),
    path('superadmin/all-users/', AllUsersView.as_view(), name='all_users'),
    path('api/all-users/', AllUsersAPI.as_view(), name='api_all_users'),
    path('user/delete/<int:id>/', DeleteUserView.as_view(), name='delete_user'),
    path('create_vendor/', CreateVendorView.as_view(), name='create_vendor'),
    path('service/<int:id>/', ServiceDetailView.as_view(), name='service_detail'),
    path('book_service/', BookServiceView.as_view(), name='book_service'),
    # Cart and Checkout URLs
    path('cart/add/', AddToCartView.as_view(), name='add_to_cart'),
    path('cart/remove/', RemoveFromCartView.as_view(), name='remove_from_cart'),
    path('cart/clear/', ClearCartView.as_view(), name='clear_cart'),
    path('cart/', CartView.as_view(), name='cart_view'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('booking-success/<int:booking_id>/', BookingSuccessView.as_view(), name='booking_success'),

    # path('superadmin/create-service/', CreateServiceView.as_view(), name='create_service'),
    # path('superadmin/update-service/<int:id>/', UpdateServiceView.as_view(), name='update_service'),
    # path('delete-service/', DeleteServiceView.as_view(), name='delete_service'),

    # path('send-booking-otp/', send_booking_otp, name='send_booking_otp'),
    # path('verify-booking-otp/', verify_booking_otp, name='verify_booking_otp'),

    path('my-orders/', CustomerOrdersView.as_view(), name='customer_orders'),
    path('vendor-orders/', VendorOrdersView.as_view(), name='vendor_orders'),
    path('admin-orders/', AdminOrdersView.as_view(), name='admin_orders'),
    path('superadmin-orders/', SuperAdminOrdersView.as_view(), name='superadmin_orders'),
    path('assign-vendor/', AssignVendorView.as_view()),
    path('update-status/', UpdateStatusView.as_view()),
    path('order-history/<int:id>/', OrderHistoryView.as_view(), name='order_history'),
    path('order/<int:id>/', CustomerOrderDetailView.as_view(), name='customer_order_detail'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('superadmin-payments/', SuperAdminPaymentsView.as_view(), name='superadmin_payments'),
    path('admin-payments/', AdminPaymentsView.as_view(), name='admin_payments'),
    path('invoice/<int:pk>/', PaymentInvoiceView.as_view(), name='payment_invoice'),
    path('vendor/payments/', VendorPaymentsView.as_view(), name='vendor_payments'),
    path('vendor/payments_show/', VendorPaymentsShowView.as_view(), name='vendor_payment_show'),
    path('vendor/booking/<int:pk>/', VendorBookingDetailView.as_view(), name='vendor_booking_detail'),
    path('get-services/', get_services, name='get_services'),
    path('my-bookings/', MyBookingsView.as_view(), name='my_bookings'),
    path('complaint/add/<int:booking_id>/', ComplaintCreateView.as_view(), name='complaint_add'),
    path('complaints/', ComplaintListView.as_view(), name='complaint_list'),
    path('complaint/<int:pk>/', ComplaintDetailView.as_view(), name='complaint_detail'),
    path('complaint/<int:pk>/delete/', ComplaintDeleteView.as_view(), name='complaint_delete'),
    path('complaint/ajax-update/<int:pk>/', ComplaintStatusAjaxUpdateView.as_view(), name='complaint_ajax_update'),
    path('vendors-approve/', AdminVendorApprovalView.as_view(), name='vendor_approval'),
    path('vendor-action/', VendorActionView.as_view(), name='vendor_action'),
    path('admin-booking/<int:booking_id>/', AdminBookingEditView.as_view(), name='admin_booking_edit'),
    path('renew-service/<int:booking_id>/', renew_service, name='renew_service'),
    path('vendor/payment/<int:booking_id>/', VendorPaymentPageView.as_view(), name='vendor_payment_page'),
    path('vendor/profile/<int:id>/', VendorProfileView.as_view(), name='vendor_profile'),
    path('user/all-users/', AdminUsersView.as_view(), name='admin_all_users'),
    path('customer/tracking/', CustomerTrackingView.as_view(), name='customer_tracking'),
    path('customer/tracking/<int:id>/', CustomerTrackingDetailView.as_view(), name='customer_tracking_detail'),
    path('customer/payments/', CustomerPaymentsView.as_view(), name='customer_payments'),
    path('renew-booking/<int:booking_id>/', RenewBookingPageView.as_view(), name='renew_booking_page'),
    path('admin-leads/', AdminLeadsView.as_view(), name='admin_leads'),
    path('admin-renewal-dashboard/', AdminRenewalDashboardView.as_view(), name='admin_renewal_dashboard'),
    path('customer-invoice/<int:booking_id>/', CustomerInvoiceView.as_view(), name='customer_invoice'),
    path('vendor-verify/<int:id>/', AdminVendorVerifyView.as_view(), name='admin_vendor_verify'),
    path('user-profile/<int:id>/', UserProfileView.as_view(), name='user_profile'),
    path('services_page/', ServicesListingView.as_view(), name='services_listing_page'),
    path("services_page/",ServicesListingView.as_view(),name="services_page"),
    path("send-otp/", send_otp_view, name="send_otp"),
    path("verify-otp/", verify_otp_view, name="verify_otp"),
    path('vendor-help/',VendorHelpView.as_view(),name='vendor_help'),
    path("customer-sig/terms/",CustomerTermsView.as_view(),name="customer_terms"),
    path("terms/list/",TermsListView.as_view(),name="terms_list"),
    path("terms/details/<int:pk>/",TermsDetailView.as_view(),name="terms_details"),
    
    path("customer-terms/conditions",CustomerRegisterTermsView.as_view(),name="customer_termsandconditions"),
    path("customer-privacy/",CustomerPrivacyView.as_view(),name="customer_privacy"),
    path("vendor-terms/conditions",VendorTermsView.as_view(),name="vendor_termsandconditions"),
    path("vendor-privacy/",VendorPrivacyView.as_view(),name="vendor_privacy"),
    path("login-terms/",LoginTermView.as_view(),name="login_terms"),
    
    
    path('dashboard/export-excel/',export_dashboard_excel,name='export_dashboard_excel'),
    
    
    path("admin-permissions/",AdminPermissionsView.as_view(),name="admin_permissions"),
    
    path('visitors/',VisitorListView.as_view(),name='visitors'),
    
    # Main assign leads page (GET = list, POST = assign via JSON)
    path(
        "assign-leads/",
        SuperAdminAssignLeadView.as_view(),
        name="assign_leads",
    ),

    # AJAX: filter vendors by city / category / service
    path(
        "filter-vendors/",
        VendorFilterView.as_view(),
        name="filter_vendors",
    ),

    # Form POST: assign vendor button in table
    path(
        "assign-vendor/",
        AssignVendorView.as_view(),
        name="assign_vendor",
    ),

    # AJAX POST: delete a lead
    path(
        "delete-lead/<int:booking_id>/",
        DeleteLeadView.as_view(),
        name="delete_lead",
    ),

    # AJAX POST: change vendor on existing lead
    path(
        "edit-lead-vendor/",
        EditLeadVendorView.as_view(),
        name="edit_lead_vendor",
    ),

]