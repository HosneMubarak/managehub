from django.urls import path
from . import views

app_name = 'leaves'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),
    
    # Leave Requests
    path('requests/', views.LeaveRequestListView.as_view(), name='list'),
    path('requests/my/', views.MyLeaveRequestsView.as_view(), name='my_requests'),
    path('requests/employee/<uuid:user_id>/', views.EmployeeLeaveRequestsView.as_view(), name='employee_requests'),
    path('requests/create/', views.LeaveRequestCreateView.as_view(), name='create'),
    path('requests/create-for-user/', views.AdminLeaveRequestCreateView.as_view(), name='admin_create'),
    path('requests/<uuid:id>/', views.LeaveRequestDetailView.as_view(), name='detail'),
    path('requests/<uuid:id>/edit/', views.LeaveRequestUpdateView.as_view(), name='edit'),
    
    # Calendar
    path('calendar/', views.leave_calendar_view, name='calendar'),
    
    # Entitlements
    path('entitlements/', views.entitlement_list_view, name='entitlements'),
    path('entitlements/create/', views.EntitlementCreateView.as_view(), name='entitlement_create'),
    path('entitlements/<uuid:id>/edit/', views.EntitlementUpdateView.as_view(), name='entitlement_edit'),
    
    # Reports
    path('reports/', views.reports_view, name='reports'),
    
    # Carry Over Processing
    path('process-carry-over/', views.process_carry_over_view, name='process_carry_over'),
    
    # Leave request management endpoints
    path('requests/<uuid:pk>/comment/', views.add_comment_ajax, name='add_comment'),
    path('requests/<uuid:pk>/approve/', views.approve_leave_ajax, name='approve'),
    path('requests/<uuid:pk>/cancel/', views.cancel_leave_ajax, name='cancel'),
    path('balance/', views.get_leave_balance_ajax, name='balance'),
]
