# hospital/urls.py
from django.contrib import admin
from django.urls import path
from hospital import views
from django.contrib.auth.views import LoginView, LogoutView

from django.conf import settings
from django.conf.urls.static import static

# Admin-related URLs
urlpatterns = [
    path('admin/', admin.site.urls),    path('', views.home_view, name=''),
    path('aboutus', views.aboutus_view),

    path('doctorclick', views.doctorclick_view),
    path('patientclick', views.patientclick_view),
    path('adminsignup', views.admin_signup_view),
    path('doctorsignup', views.doctor_signup_view, name='doctorsignup'),
    path('patientsignup', views.patient_signup_view),

    path('adminlogin', LoginView.as_view(template_name='hospital/adminlogin.html'), name='adminlogin'),
    path('doctorlogin', LoginView.as_view(template_name='hospital/doctorlogin.html'), name='doctorlogin'),
    path('patientlogin', LoginView.as_view(
        template_name='hospital/patientlogin.html',
        redirect_authenticated_user=True,
        extra_context={'next': 'patient-dashboard'}
    ), name='patientlogin'),
    path('afterlogin', views.afterlogin_view, name='afterlogin'),
    path('logout', LogoutView.as_view(template_name='hospital/index.html'), name='logout'),
    path('admin-dashboard', views.admin_dashboard_view, name='admin-dashboard'),
    path('admin-doctor', views.admin_doctor_view, name='admin-doctor'),
    path('admin-view-doctor', views.admin_view_doctor_view, name='admin-view-doctor'),
    path('delete-doctor-from-hospital/<int:pk>', views.delete_doctor_from_hospital_view, name='delete-doctor-from-hospital'),
    path('update-doctor/<int:pk>', views.update_doctor_view, name='update-doctor'),
    path('admin-add-doctor', views.admin_add_doctor_view, name='admin-add-doctor'),
    path('admin-approve-doctor', views.admin_approve_doctor_view, name='admin-approve-doctor'),
    path('approve-doctor/<int:pk>', views.approve_doctor_view, name='approve-doctor'),
    path('reject-doctor/<int:pk>', views.reject_doctor_view, name='reject-doctor'),
    path('admin-view-doctor-specialisation', views.admin_view_doctor_specialisation_view, name='admin-view-doctor-specialisation'),
    path('admin-patient', views.admin_patient_view, name='admin-patient'),
    path('admin-view-patient', views.admin_view_patient_view, name='admin-view-patient'),
    path('delete-patient-from-hospital/<int:pk>', views.delete_patient_from_hospital_view, name='delete-patient-from-hospital'),
    path('update-patient/<int:pk>', views.update_patient_view, name='update-patient'),
    path('admin-add-patient', views.admin_add_patient_view, name='admin-add-patient'),
    path('admin-approve-patient', views.admin_approve_patient_view, name='admin-approve-patient'),
    path('approve-patient/<int:pk>', views.approve_patient_view, name='approve-patient'),
    path('reject-patient/<int:pk>', views.reject_patient_view, name='reject-patient'),    path('admin-discharge-patient', views.admin_discharge_patient_view, name='admin-discharge-patient'),
    path('discharge-patient/<int:pk>', views.discharge_patient_view, name='discharge-patient'),
    path('generate-patient-bill/<int:pk>/', views.discharge_patient_view, name='generate-patient-bill'),
    path('download-pdf/<int:pk>', views.download_pdf_view, name='download_pdf_view'),
    path('admin-appointment', views.admin_appointment_view, name='admin-appointment'),
    path('admin-view-appointment', views.admin_view_appointment_view, name='admin-view-appointment'),
    path('admin-add-appointment', views.admin_add_appointment_view, name='admin-add-appointment'),
    path('admin-approve-appointment', views.admin_approve_appointment_view, name='admin-approve-appointment'),
    path('approve-appointment/<int:pk>', views.approve_appointment_view, name='approve-appointment'),
    path('reject-appointment/<int:pk>', views.reject_appointment_view, name='reject-appointment'),

    # Billing
    path('generate-bill-pdf/<int:patient_id>', views.generate_bill_pdf, name='generate_bill_pdf'),
    path('admin-list-patients-for-discharge', views.admin_list_patients_for_discharge, name='admin-list-patients-for-discharge'),
]

# Doctor-related URLs
urlpatterns += [
    path('doctor-dashboard', views.doctor_dashboard_view, name='doctor-dashboard'),
    path('search', views.search_view, name='search'),
    path('doctor-patient', views.doctor_patient_view, name='doctor-patient'),
    path('doctor-view-patient', views.doctor_view_patient_view, name='doctor-view-patient'),
    path('doctor-view-patient', views.doctor_patient_view, name='doctor-view-patient'),
    path('doctor-view-discharge-patient', views.doctor_view_discharge_patient_view, name='doctor-view-discharge-patient'),
    path('doctor-appointment', views.doctor_appointment_view, name='doctor-appointment'),
    path('doctor-view-appointment', views.doctor_view_appointment_view, name='doctor-view-appointment'),
    path('doctor-delete-appointment', views.doctor_delete_appointment_view, name='doctor-delete-appointment'),
    path('delete-appointment/<int:pk>', views.delete_appointment_view, name='delete-appointment'),
    path('doctor-mark-appointment-completed/<int:pk>/', views.doctor_mark_appointment_completed_view, name='doctor-mark-appointment-completed'),
    path('doctor-view-completed-appointments', views.doctor_view_completed_appointments_view, name='doctor-view-completed-appointments'),
    path('doctor-update-patient/<int:pk>', views.doctor_update_patient_view, name='doctor-update-patient'),
    path('doctor/medical-record/<str:record_id>/edit/', views.doctor_edit_medical_record, name='doctor_edit_medical_record'),
    path('doctor/medical-record/<str:record_id>/delete/', views.doctor_delete_medical_record, name='doctor_delete_medical_record'),  # New URL
]

# Patient-related URLs
urlpatterns += [
    path('patient-dashboard', views.patient_dashboard_view, name='patient-dashboard'),
    path('patient-appointment', views.patient_appointment_view, name='patient-appointment'),
    path('patient-book-appointment', views.patient_book_appointment_view, name='patient-book-appointment'),
    path('patient-view-appointment', views.patient_view_appointment_view, name='patient-view-appointment'),
    path('patient-view-doctor', views.patient_view_doctor_view, name='patient-view-doctor'),
    path('searchdoctor', views.search_doctor_view, name='searchdoctor'),
    path('patient-discharge', views.patient_discharge_view, name='patient-discharge'),
    # New URLs for rescheduling and cancelling appointments
    path('patient-reschedule-appointment/<int:pk>', views.patient_reschedule_appointment_view, name='patient-reschedule-appointment'),
    path('patient-cancel-appointment/<int:pk>', views.patient_cancel_appointment_view, name='patient-cancel-appointment'),
]




urlpatterns += [
    # Department URLs
    path('admin-view-departments', views.admin_list_departments, name='admin-view-departments'),
    path('admin-add-department', views.admin_add_department, name='admin-add-department'),
    path('admin-view-department/<str:department_id>', views.admin_view_department, name='admin-view-department'),
    path('admin-update-department/<str:department_id>', views.admin_update_department, name='admin-update-department'),
    path('admin-delete-department/<str:department_id>', views.admin_delete_department, name='admin-delete-department'),
    path('patient-view-departments', views.patient_view_departments, name='patient-view-departments'),

    # Pharmacy URLs
    path('admin-pharmacy', views.admin_pharmacy_view, name='admin-pharmacy'),
    path('admin-view-pharmacy', views.admin_view_pharmacy_view, name='admin-view-pharmacy'),
    path('admin-add-pharmacy', views.admin_add_pharmacy_view, name='admin-add-pharmacy'),
    path('admin-update-pharmacy/<int:pk>', views.admin_update_pharmacy_view, name='admin-update-pharmacy'),
    path('admin-delete-pharmacy/<int:pk>', views.admin_delete_pharmacy_view, name='admin-delete-pharmacy'),
    path('admin-dispense-medication', views.admin_dispense_medication_view, name='admin-dispense-medication'),
    path('admin-dispense-medication/<int:patient_id>/', views.admin_dispense_medication_view, name='admin-dispense-medication-for-patient'),
    path('admin-dispense-medication/', views.admin_dispense_medication_view, name='admin-dispense-medication'),
    path('admin-dispense-medication/<int:patient_id>/', views.admin_dispense_medication_view, name='admin-dispense-medication-for-patient'),

    # Billing URLs
    path('admin-billing', views.admin_billing_view, name='admin-billing'),
    path('admin-view-billing', views.admin_view_billing_view, name='admin-view-billing'),
    path('admin-add-billing', views.admin_add_billing_view, name='admin-add-billing'),

    # Ward/Room URLs
    path('admin-ward-room', views.admin_ward_room_view, name='admin-ward-room'),
    path('admin-view-ward-room', views.admin_view_ward_room_view, name='admin-view-ward-room'),
    path('admin-add-ward-room', views.admin_add_ward_room_view, name='admin-add-ward-room'),
    path('doctor/room-management/', views.room_management, name='room_management'),  # New URL

    # Medical History URLs
    path('patient/medical-records/', views.patient_medical_records, name='patient_medical_records'),
    path('doctor/patient/<int:patient_id>/records/', views.doctor_view_medical_records, name='doctor_view_medical_records'),
    path('doctor/patient/<int:patient_id>/add-record/', views.add_medical_record, name='add_medical_record'),
    path('admin/medical-records/', views.admin_view_medical_records, name='admin_view_medical_records'),
    path('admin/medical-records/add/', views.admin_add_medical_record, name='admin_add_medical_record'),
    path('admin/medical-record/<str:record_id>/edit/', views.edit_medical_record, name='edit_medical_record'),
    path('doctor-view-medical-records/<int:patient_id>', views.doctor_view_medical_records, name='doctor-view-medical-records'),
    path('add-medical-record/<int:patient_id>', views.doctor_add_medical_record_view, name='add-medical-record'),
    path('edit-medical-record/<str:record_id>', views.doctor_edit_medical_record, name='edit-medical-record'),
]

# hospital/urls.py (partial update)
urlpatterns += [
    
    # Pharmacy URLs
    path('admin-dispense-medication/<int:record_id>', views.admin_dispense_medication_view, name='admin-dispense-medication'),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)