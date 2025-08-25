from django.contrib import admin
from .models import Doctor,Patient,Appointment,PatientDischargeDetails
from .models import Patient, Doctor, MedicalRecord


# Register your models here.
class DoctorAdmin(admin.ModelAdmin):
    pass
admin.site.register(Doctor, DoctorAdmin)

class PatientAdmin(admin.ModelAdmin):
    pass
admin.site.register(Patient, PatientAdmin)

class AppointmentAdmin(admin.ModelAdmin):
    pass
admin.site.register(Appointment, AppointmentAdmin)

class PatientDischargeDetailsAdmin(admin.ModelAdmin):
    pass
admin.site.register(PatientDischargeDetails, PatientDischargeDetailsAdmin)

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('record_id', 'patient', 'doctor', 'diagnosis', 'created_at')
    list_filter = ('created_at', 'patient', 'doctor')
    search_fields = ('record_id', 'diagnosis', 'prescribed_treatment')
    raw_id_fields = ('patient', 'doctor')