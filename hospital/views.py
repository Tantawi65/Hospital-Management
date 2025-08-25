# hospital/views.py
import json
import io
from io import BytesIO
from django.utils import timezone
from django.shortcuts import render, redirect, reverse, get_object_or_404
from . import forms, models
from django.db.models import Sum
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect, HttpResponse, FileResponse
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template.loader import get_template
from datetime import datetime, timedelta, date
from django.conf import settings
from django.db.models import Q, Case, When, Value, CharField, Count
from django.contrib.auth import login, authenticate
from django.contrib import messages
from .forms import MedicalRecordForm, DoctorMedicalRecordForm
from .models import Patient, Doctor, MedicalRecord
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from decimal import Decimal, InvalidOperation
from reportlab.pdfgen import canvas
from xhtml2pdf import pisa

def home_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request, 'hospital/index.html')



def doctorclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request, 'hospital/doctorclick.html')

def patientclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request, 'hospital/patientclick.html')

def admin_signup_view(request):
    return HttpResponse("Admin signup is not allowed.")

def doctor_signup_view(request):
    userForm = forms.DoctorUserForm()
    doctorForm = forms.DoctorForm()
    mydict = {'userForm': userForm, 'doctorForm': doctorForm}
    if request.method == 'POST':
        userForm = forms.DoctorUserForm(request.POST)
        doctorForm = forms.DoctorForm(request.POST, request.FILES)
        if userForm.is_valid() and doctorForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            doctor = doctorForm.save(commit=False)
            doctor.user = user
            doctor = doctor.save()
            my_doctor_group = Group.objects.get_or_create(name='DOCTOR')
            my_doctor_group[0].user_set.add(user)
        return HttpResponseRedirect('doctorlogin')
    return render(request, 'hospital/doctorsignup.html', context=mydict)

def patient_signup_view(request):
    userForm = forms.PatientUserForm()
    patientForm = forms.PatientForm()
    mydict = {'userForm': userForm, 'patientForm': patientForm}
    if request.method == 'POST':
        userForm = forms.PatientUserForm(request.POST)
        patientForm = forms.PatientForm(request.POST, request.FILES)
        if userForm.is_valid() and patientForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            patient = patientForm.save(commit=False)
            patient.user = user
            patient.assignedDoctorId = request.POST.get('assignedDoctorId')
            patient = patient.save()
            my_patient_group = Group.objects.get_or_create(name='PATIENT')
            my_patient_group[0].user_set.add(user)
        return HttpResponseRedirect('patientlogin')
    return render(request, 'hospital/patientsignup.html', context=mydict)



def is_admin(user):
    return user.groups.filter(name='ADMIN').exists()

def is_doctor(user):
    return user.groups.filter(name='DOCTOR').exists()

def is_patient(user):
    return user.groups.filter(name='PATIENT').exists()



def afterlogin_view(request):
    if is_admin(request.user):
        return redirect('admin-dashboard')
    elif is_doctor(request.user):
        accountapproval = models.Doctor.objects.all().filter(user_id=request.user.id, status=True)
        if accountapproval:
            return redirect('doctor-dashboard')
        else:
            return render(request, 'hospital/doctor_wait_for_approval.html')
    elif is_patient(request.user):
        accountapproval = models.Patient.objects.all().filter(user_id=request.user.id, status=True)
        if accountapproval:
            return redirect('patient-dashboard')
        else:
            return render(request, 'hospital/patient_wait_for_approval.html')

# Admin-related views
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_dashboard_view(request):
    doctors = models.Doctor.objects.all().order_by('-id')
    patients = models.Patient.objects.all().order_by('-id')
    doctorcount = models.Doctor.objects.all().filter(status=True).count()
    pendingdoctorcount = models.Doctor.objects.all().filter(status=False).count()
    patientcount = models.Patient.objects.all().filter(status=True).count()
    pendingpatientcount = models.Patient.objects.all().filter(status=False).count()
    appointmentcount = models.Appointment.objects.all().filter(status='Approved').count()
    pendingappointmentcount = models.Appointment.objects.all().filter(status='Pending').count()
    
    # Add department and room data
    departmentcount = models.Department.objects.all().count()
    activedepartmentcount = models.Department.objects.filter(head_of_department__isnull=False).count()
    wardcount = models.WardRoom.objects.all().count()
    occupiedwardcount = models.WardRoom.objects.filter(availability=False).count()
    
    mydict = {
        'doctors': doctors,
        'patients': patients,
        'doctorcount': doctorcount,
        'pendingdoctorcount': pendingdoctorcount,
        'patientcount': patientcount,
        'pendingpatientcount': pendingpatientcount,
        'appointmentcount': appointmentcount,
        'pendingappointmentcount': pendingappointmentcount,
        'departmentcount': departmentcount,
        'activedepartmentcount': activedepartmentcount,
        'wardcount': wardcount,
        'occupiedwardcount': occupiedwardcount,
    }
    return render(request, 'hospital/admin_dashboard.html', context=mydict)

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_doctor_view(request):
    return render(request, 'hospital/admin_doctor.html')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_doctor_view(request):
    doctors = models.Doctor.objects.all().filter(status=True)
    return render(request, 'hospital/admin_view_doctor.html', {'doctors': doctors})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def delete_doctor_from_hospital_view(request, pk):
    doctor = models.Doctor.objects.get(id=pk)
    user = models.User.objects.get(id=doctor.user_id)
    user.delete()
    doctor.delete()
    return redirect('admin-view-doctor')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def update_doctor_view(request, pk):
    doctor = models.Doctor.objects.get(id=pk)
    user = models.User.objects.get(id=doctor.user_id)
    userForm = forms.DoctorUserForm(instance=user)
    doctorForm = forms.DoctorForm(request.FILES, instance=doctor)
    mydict = {'userForm': userForm, 'doctorForm': doctorForm}
    if request.method == 'POST':
        userForm = forms.DoctorUserForm(request.POST, instance=user)
        doctorForm = forms.DoctorForm(request.POST, request.FILES, instance=doctor)
        if userForm.is_valid() and doctorForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            doctor = doctorForm.save(commit=False)
            doctor.status = True
            doctor.save()
            return redirect('admin-view-doctor')
    return render(request, 'hospital/admin_update_doctor.html', context=mydict)

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_doctor_view(request):
    userForm = forms.DoctorUserForm()
    doctorForm = forms.DoctorForm()
    mydict = {'userForm': userForm, 'doctorForm': doctorForm}
    if request.method == 'POST':
        userForm = forms.DoctorUserForm(request.POST)
        doctorForm = forms.DoctorForm(request.POST, request.FILES)
        if userForm.is_valid() and doctorForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            doctor = doctorForm.save(commit=False)
            doctor.user = user
            doctor.status = True
            doctor.save()
            my_doctor_group = Group.objects.get_or_create(name='DOCTOR')
            my_doctor_group[0].user_set.add(user)
        return HttpResponseRedirect('admin-view-doctor')
    return render(request, 'hospital/admin_add_doctor.html', context=mydict)

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_approve_doctor_view(request):
    doctors = models.Doctor.objects.all().filter(status=False)
    return render(request, 'hospital/admin_approve_doctor.html', {'doctors': doctors})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def approve_doctor_view(request, pk):
    doctor = models.Doctor.objects.get(id=pk)
    doctor.status = True
    doctor.save()
    return redirect(reverse('admin-approve-doctor'))

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def reject_doctor_view(request, pk):
    doctor = models.Doctor.objects.get(id=pk)
    user = models.User.objects.get(id=doctor.user_id)
    user.delete()
    doctor.delete()
    return redirect('admin-approve-doctor')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_doctor_specialisation_view(request):
    doctors = models.Doctor.objects.all().filter(status=True)
    return render(request, 'hospital/admin_view_doctor_specialisation.html', {'doctors': doctors})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_patient_view(request):
    return render(request, 'hospital/admin_patient.html')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_patient_view(request):
    patients = models.Patient.objects.all().filter(status=True)
    return render(request, 'hospital/admin_view_patient.html', {'patients': patients})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def delete_patient_from_hospital_view(request, pk):
    patient = models.Patient.objects.get(id=pk)
    user = models.User.objects.get(id=patient.user_id)
    user.delete()
    patient.delete()
    return redirect('admin-view-patient')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def update_patient_view(request, pk):
    patient = models.Patient.objects.get(id=pk)
    user = models.User.objects.get(id=patient.user_id)
    userForm = forms.PatientUserForm(instance=user)
    patientForm = forms.PatientForm(request.FILES, instance=patient)
    mydict = {'userForm': userForm, 'patientForm': patientForm}
    if request.method == 'POST':
        userForm = forms.PatientUserForm(request.POST, instance=user)
        patientForm = forms.PatientForm(request.POST, request.FILES, instance=patient)
        if userForm.is_valid() and patientForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            patient = patientForm.save(commit=False)
            patient.status = True
            patient.assignedDoctorId = request.POST.get('assignedDoctorId')
            patient.save()
            return redirect('admin-view-patient')
    return render(request, 'hospital/admin_update_patient.html', context=mydict)

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_patient_view(request):
    userForm = forms.PatientUserForm()
    patientForm = forms.PatientForm()
    available_rooms = models.WardRoom.objects.filter(availability=True)
    mydict = {'userForm': userForm, 'patientForm': patientForm, 'available_rooms': available_rooms}
    if request.method == 'POST':
        userForm = forms.PatientUserForm(request.POST)
        patientForm = forms.PatientForm(request.POST, request.FILES)
        if userForm.is_valid() and patientForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            patient = patientForm.save(commit=False)
            patient.user = user
            patient.status = True
            patient.assignedDoctorId = request.POST.get('assignedDoctorId')
            patient.save()
            
            # Handle room assignment if selected
            ward_room_id = request.POST.get('ward_room')
            if ward_room_id:
                try:
                    room = models.WardRoom.objects.get(room_id=ward_room_id, availability=True)
                    room.assign_room(patient)
                    messages.success(request, f"Patient admitted and assigned to Room {room.room_id}")
                except models.WardRoom.DoesNotExist:
                    messages.warning(request, "Selected room is no longer available")
            else:
                messages.success(request, "Patient admitted successfully")
            
            my_patient_group = Group.objects.get_or_create(name='PATIENT')
            my_patient_group[0].user_set.add(user)
        return HttpResponseRedirect('admin-view-patient')
    return render(request, 'hospital/admin_add_patient.html', context=mydict)

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_approve_patient_view(request):
    patients = models.Patient.objects.all().filter(status=False)
    return render(request, 'hospital/admin_approve_patient.html', {'patients': patients})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def approve_patient_view(request, pk):
    patient = models.Patient.objects.get(id=pk)
    patient.status = True
    patient.save()
    return redirect(reverse('admin-approve-patient'))

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def reject_patient_view(request, pk):
    patient = models.Patient.objects.get(id=pk)
    user = models.User.objects.get(id=patient.user_id)
    user.delete()
    patient.delete()
    return redirect('admin-approve-patient')

# Billing

# New view to list patients for discharge
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_list_patients_for_discharge(request):
    # Fetch patients who are admitted (e.g., have admitDate and no discharge record or still in a room)
    patients = models.Patient.objects.filter(admitDate__isnull=False).exclude(
        id__in=models.PatientDischargeDetails.objects.values('patientId')
    ).prefetch_related('assigned_room')
    return render(request, 'hospital/admin_list_patients_for_discharge.html', {'patients': patients})

# Existing discharge_patient_view with static method integration
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def discharge_patient_view(request, pk):
    patient = get_object_or_404(models.Patient, id=pk)
    days = (date.today() - patient.admitDate).days or 1
    assignedDoctor = models.User.objects.filter(id=patient.assignedDoctorId).first()
    room = patient.assigned_room
    bill = models.Billing.objects.filter(patient=patient).first()
    if not bill:
        bill = models.Billing.objects.create(
            patient=patient,
            bill_id=f"BILL{timezone.now().strftime('%Y%m%d%H%M%S')}",
            medical_record=None
        )

    patientDict = {
        'patientId': pk,
        'name': patient.get_name,
        'mobile': patient.mobile,
        'address': patient.address,
        'symptoms': patient.symptoms,
        'admitDate': patient.admitDate,
        'todayDate': date.today(),
        'day': days,
        'assignedDoctorName': assignedDoctor.first_name if assignedDoctor else "N/A",
        'room': room.room_id if room else "N/A",
    }

    if request.method == 'POST':
        form = forms.DischargeForm(request.POST)
        if form.is_valid():
            room_charge_per_day = form.cleaned_data['roomCharge']
            doctor_fee = form.cleaned_data['doctorFee']
            other_charge = form.cleaned_data['OtherCharge']
            medicine_cost = form.cleaned_data['medicineCost']

            room_charge = room_charge_per_day * Decimal(str(days))
            treatment_cost = doctor_fee + other_charge
            total = room_charge + medicine_cost + treatment_cost

            feeDict = {
                'roomCharge': room_charge,
                'doctorFee': doctor_fee,
                'medicineCost': medicine_cost,
                'OtherCharge': other_charge,
                'total': total
            }
            patientDict.update(feeDict)

            # Use static method to calculate and update bill
            BillingHelper.update_bill(bill, treatment_cost, medicine_cost, room_charge)

            pDD = models.PatientDischargeDetails(
                patientId=pk,
                patientName=patient.get_name,
                assignedDoctorName=assignedDoctor.first_name if assignedDoctor else "N/A",
                address=patient.address if patient.address else "N/A",
                mobile=patient.mobile if patient.mobile else "N/A",
                symptoms=patient.symptoms if patient.symptoms else "N/A",
                admitDate=patient.admitDate,
                releaseDate=date.today(),
                daySpent=days,
                roomCharge=int(room_charge.to_integral_value()),
                medicineCost=int(medicine_cost.to_integral_value()),
                doctorFee=int(doctor_fee.to_integral_value()),
                OtherCharge=int(other_charge.to_integral_value()),
                total=int(total.to_integral_value())
            )
            pDD.save()

            if room:
                room.discharge_patient()

            messages.success(request, "Patient discharged successfully.")
            return render(request, 'hospital/patient_final_bill.html', {
                'patientDict': patientDict,
                'bill': bill
            })
        else:
            messages.error(request, "Invalid form data. Please check the inputs.")
    else:
        form = forms.DischargeForm()

    return render(request, 'hospital/admin-discharge-patient.html', {
        'patientDict': patientDict,
        'form': form
    })

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_discharge_patient_view(request):
    # Fetch patients who are admitted (status=True) and prefetch related data
    patients = models.Patient.objects.filter(status=True).select_related('assigned_ward').prefetch_related('billing_set')

    # Annotate billing_status based on Billing.payment_status
    patients = patients.annotate(
        billing_status=Case(
            When(billing__payment_status='Paid', then=Value('Paid')),
            When(billing__payment_status='Partial', then=Value('Partial')),
            default=Value('Pending'),
            output_field=CharField()
        )
    )

    # Fetch occupied wards (optional, if you want to display them)
    wards = models.WardRoom.objects.filter(availability=False).select_related('assigned_patient')

    return render(request, 'hospital/admin-discharge-patient.html', {
        'patients': patients,
        'wards': wards,
    })

import io
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.http import HttpResponse
from django.db.models import DecimalField
from django.db.models import Case, When, Value, CharField

# Helper class for billing operations
class BillingHelper:
    @staticmethod
    def calculate_total(treatment_cost, medicine_cost, room_charge=None):
        """Static method to calculate the total bill amount with optional room charge."""
        base_total = treatment_cost + medicine_cost
        return base_total + (room_charge or Decimal('0.00'))

    @staticmethod
    def update_bill(bill, treatment_cost, medicine_cost, room_charge=None):
        """Static method to update bill with calculated total."""
        total = BillingHelper.calculate_total(treatment_cost, medicine_cost, room_charge)
        bill.treatment_cost = treatment_cost
        bill.medicine_cost = medicine_cost
        bill.total_amount = total
        bill.save()

# Render to PDF
def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

def download_pdf_view(request, pk):
    # Check if discharge details exist
    discharge_details = models.PatientDischargeDetails.objects.filter(patientId=pk).order_by('-id').first()
    if not discharge_details:
        messages.error(request, "Discharge details not found. You must be discharged before downloading the invoice.")
        return redirect('patient-discharge')  # Redirect back to the discharge page

    # Check if billing details exist
    bill = models.Billing.objects.filter(patient_id=pk).order_by('-created_at').first()
    if not bill:
        messages.error(request, "Billing details not found. Please contact the hospital administration.")
        return redirect('patient-discharge')

    context_dict = {
        'bill_id': bill.bill_id,
        'patientName': discharge_details.patientName,
        'assignedDoctorName': discharge_details.assignedDoctorName,
        'address': discharge_details.address,
        'mobile': discharge_details.mobile,
        'symptoms': discharge_details.symptoms,
        'admitDate': discharge_details.admitDate,
        'releaseDate': discharge_details.releaseDate,
        'daySpent': discharge_details.daySpent,
        'medicineCost': discharge_details.medicineCost,
        'roomCharge': discharge_details.roomCharge,
        'doctorFee': discharge_details.doctorFee,
        'otherCharge': discharge_details.OtherCharge,
        'total': discharge_details.total,
        'treatmentCost': bill.treatment_cost,
        'paymentStatus': bill.payment_status,
        'generated_on': timezone.now(),
    }
    pdf = render_to_pdf('hospital/download_bill.html', context_dict)
    if pdf:
        response = pdf
        response['Content-Disposition'] = f'attachment; filename="bill_patient_{pk}_{bill.bill_id}.pdf"'
        return response
    return HttpResponse("Error generating PDF.", status=500)


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_appointment_view(request):
    return render(request, 'hospital/admin_appointment.html')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_appointment_view(request):
    appointments = models.Appointment.objects.all().filter(status='Approved')
    return render(request, 'hospital/admin_view_appointment.html', {'appointments': appointments})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_appointment_view(request):
    appointmentForm = forms.AppointmentForm()
    mydict = {'appointmentForm': appointmentForm}
    if request.method == 'POST':
        appointmentForm = forms.AppointmentForm(request.POST)
        if appointmentForm.is_valid():
            appointment = appointmentForm.save(commit=False)
            appointment.doctorId = request.POST.get('doctorId')
            appointment.patientId = request.POST.get('patientId')
            appointment.doctorName = models.User.objects.get(id=request.POST.get('doctorId')).first_name
            appointment.patientName = models.User.objects.get(id=request.POST.get('patientId')).first_name
            appointment.status = 'Approved' if appointmentForm.cleaned_data['status'] else 'Pending'
            appointment.save()
        return HttpResponseRedirect('admin-view-appointment')
    return render(request, 'hospital/admin_add_appointment.html', context=mydict)

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_approve_appointment_view(request):
    appointments = models.Appointment.objects.all().filter(status='Pending')
    return render(request, 'hospital/admin_approve_appointment.html', {'appointments': appointments})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def approve_appointment_view(request, pk):
    appointment = models.Appointment.objects.get(id=pk)
    appointment.status = 'Approved'
    appointment.save()
    return redirect(reverse('admin-approve-appointment'))

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def reject_appointment_view(request, pk):
    appointment = models.Appointment.objects.get(id=pk)
    appointment.delete()
    return redirect('admin-approve-appointment')

# Doctor-related views (unchanged except for status checks)
# Update the doctor_dashboard_view
@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_dashboard_view(request):
    patientcount = models.Patient.objects.filter(status=True, assignedDoctorId=request.user.id).count()
    appointmentcount = models.Appointment.objects.filter(status='Approved', doctorId=request.user.id).count()
    patientdischarged = models.PatientDischargeDetails.objects.filter(assignedDoctorName=request.user.first_name).distinct().count()
    medicalrecordcount = models.MedicalRecord.objects.filter(doctor__user=request.user).count()
    
    # Appointments data
    appointments = models.Appointment.objects.filter(status='Approved', doctorId=request.user.id).order_by('-appointmentDate')
    patient_ids = [a.patientId for a in appointments]
    patients = models.Patient.objects.filter(status=True, user_id__in=patient_ids).order_by('-id')
    appointments = zip(appointments, patients)
    
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    
    mydict = {
        'patientcount': patientcount,
        'appointmentcount': appointmentcount,
        'patientdischarged': patientdischarged,
        'medicalrecordcount': medicalrecordcount,
        'appointments': appointments,
        'doctor': doctor,
        'patients': patients,
    }
    return render(request, 'hospital/doctor_dashboard.html', context=mydict)

@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_patient_view(request):
    mydict = {
        'doctor': models.Doctor.objects.get(user_id=request.user.id),
    }
    return render(request, 'hospital/doctor_patient.html', context=mydict)

@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_view_patient_view(request):
    patients = models.Patient.objects.all().filter(status=True, assignedDoctorId=request.user.id)
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    return render(request, 'hospital/doctor_view_patient.html', {'patients': patients, 'doctor': doctor})

@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def search_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    query = request.GET['query']
    patients = models.Patient.objects.all().filter(status=True, assignedDoctorId=request.user.id).filter(Q(symptoms__icontains=query) | Q(user__first_name__icontains=query))
    return render(request, 'hospital/doctor_view_patient.html', {'patients': patients, 'doctor': doctor})

@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_view_discharge_patient_view(request):
    dischargedpatients = models.PatientDischargeDetails.objects.all().distinct().filter(assignedDoctorName=request.user.first_name)
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    return render(request, 'hospital/doctor_view_discharge_patient.html', {'dischargedpatients': dischargedpatients, 'doctor': doctor})

@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_appointment_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    return render(request, 'hospital/doctor_appointment.html', {'doctor': doctor})

@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_view_appointment_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    # Fetch only uncompleted appointments (Pending and Approved) for the doctor
    appointments = models.Appointment.objects.filter(
        doctorId=doctor.user_id,
        status__in=['Pending', 'Approved']
    ).order_by('-appointmentDate')
    
    # Debug: Print the appointments
    print("Doctor ID:", doctor.user_id)
    print("Appointments (Uncompleted):", list(appointments))
    
    # Create a list of (appointment, patient, can_mark_completed) tuples
    now = timezone.now()  # Current time in UTC
    now_local = timezone.localtime(now)  # Convert to local timezone (Africa/Cairo)
    print("Current time (UTC):", now)
    print("Current time (Local, Africa/Cairo):", now_local)
    
    appointment_patient_pairs = []
    for appt in appointments:
        try:
            patient = models.Patient.objects.get(user_id=appt.patientId)
        except models.Patient.DoesNotExist:
            patient = None
        
        # Convert appointmentDate to local timezone
        appointment_date_local = timezone.localtime(appt.appointmentDate)
        
        # Determine if the appointment can be marked as completed
        can_mark_completed = (appt.status == 'Approved' and appointment_date_local <= now_local)
        print(f"Appointment {appt.id}: Status={appt.status}, Date (UTC)={appt.appointmentDate}, Date (Local)={appointment_date_local}, Can Mark Completed={can_mark_completed}")
        
        appointment_patient_pairs.append((appt, patient, can_mark_completed))
    
    # Debug: Print the pairs
    print("Appointment-Patient Pairs:", appointment_patient_pairs)
    
    return render(request, 'hospital/doctor_view_appointment.html', {
        'appointments': appointment_patient_pairs,
        'doctor': doctor
    })

@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_view_completed_appointments_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    # Fetch only completed appointments for the doctor
    appointments = models.Appointment.objects.filter(
        doctorId=doctor.user_id,
        status='Completed'
    ).order_by('-appointmentDate')
    
    # Debug: Print the appointments
    print("Doctor ID:", doctor.user_id)
    print("Completed Appointments:", list(appointments))
    
    # Create a list of (appointment, patient) tuples
    appointment_patient_pairs = []
    for appt in appointments:
        try:
            patient = models.Patient.objects.get(user_id=appt.patientId)
        except models.Patient.DoesNotExist:
            patient = None
        
        appointment_patient_pairs.append((appt, patient))
    
    # Debug: Print the pairs
    print("Completed Appointment-Patient Pairs:", appointment_patient_pairs)
    
    return render(request, 'hospital/doctor_view_completed_appointments.html', {
        'appointments': appointment_patient_pairs,
        'doctor': doctor
    })

@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_delete_appointment_view(request):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    appointments = models.Appointment.objects.all().filter(doctorId=doctor.user_id, status='Approved')  # Only show Approved appointments
    patients = models.Patient.objects.all().filter(user_id__in=[appt.patientId for appt in appointments])
    appointments = zip(appointments, patients)
    return render(request, 'hospital/doctor_delete_appointment.html', {'appointments': appointments, 'doctor': doctor})

@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def delete_appointment_view(request, pk):
    appointment = models.Appointment.objects.get(id=pk)
    appointment.delete()
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    appointments = models.Appointment.objects.all().filter(status='Approved', doctorId=request.user.id)
    patientid = [a.patientId for a in appointments]
    patients = models.Patient.objects.all().filter(status=True, user_id__in=patientid)
    appointments = zip(appointments, patients)
    return render(request, 'hospital/doctor_delete_appointment.html', {'appointments': appointments, 'doctor': doctor})

# Helper function to check if the user is a doctor
def is_doctor(user):
    return user.groups.filter(name='DOCTOR').exists()

@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_mark_appointment_completed_view(request, pk):
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    appointment = get_object_or_404(models.Appointment, id=pk, doctorId=request.user.id)

    # Check if the appointment is in the Approved state
    if appointment.status != 'Approved':
        messages.error(request, f"Cannot mark this appointment as completed. Current status: {appointment.status}.")
        return redirect('doctor-view-appointment')

    # Mark the appointment as Completed
    appointment.status = 'Completed'
    appointment.save()
    messages.success(request, "Appointment marked as completed successfully!")
    return redirect('doctor-view-appointment')


# Patient-related views (updated for new features)
@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_dashboard_view(request):
    patient = models.Patient.objects.get(user_id=request.user.id)
    doctor = models.Doctor.objects.get(user_id=patient.assignedDoctorId)
    medical_history = patient.view_medical_history().order_by('-created_at')[:5]
    bills = models.Billing.objects.filter(patient=patient).order_by('-created_at')[:3]
    room = models.WardRoom.objects.filter(assigned_patient=patient).first()
    
    # Calculate statistics for dashboard cards
    total_appointment = models.Appointment.objects.filter(patientId=request.user.id).count()
    total_doctor = models.Doctor.objects.all().count()
    total_department = models.Doctor.objects.values('department').distinct().count()
    total_medical_records = patient.view_medical_history().count()
    
    mydict = {
        'patient': patient,
        'doctorName': doctor.get_name,
        'doctorMobile': doctor.mobile,
        'doctorAddress': doctor.address,
        'symptoms': patient.symptoms,
        'doctorDepartment': doctor.department,
        'admitDate': patient.admitDate,
        'medical_history': medical_history,
        'bills': bills,
        'room': room,
        'total_appointment': total_appointment,
        'total_doctor': total_doctor,
        'total_department': total_department,
        'total_medical_records': total_medical_records,
    }
    return render(request, 'hospital/patient_dashboard.html', context=mydict)

@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_appointment_view(request):
    patient = models.Patient.objects.get(user_id=request.user.id)
    
    # Calculate appointment statistics
    total_appointments = models.Appointment.objects.filter(patientId=request.user.id).count()
    pending_appointments = models.Appointment.objects.filter(patientId=request.user.id, status='Pending').count()
    completed_appointments = models.Appointment.objects.filter(patientId=request.user.id, status='Completed').count()
    upcoming_appointments = models.Appointment.objects.filter(patientId=request.user.id, status='Approved').count()
    
    context = {
        'patient': patient,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'completed_appointments': completed_appointments,
        'upcoming_appointments': upcoming_appointments,
    }
    
    return render(request, 'hospital/patient_appointment.html', context)

@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_book_appointment_view(request):
    appointmentForm = forms.PatientAppointmentForm()
    patient = models.Patient.objects.get(user_id=request.user.id)
    message = None
    mydict = {'appointmentForm': appointmentForm, 'patient': patient, 'message': message}
    if request.method == 'POST':
        appointmentForm = forms.PatientAppointmentForm(request.POST)
        if appointmentForm.is_valid():
            appointment = appointmentForm.save(commit=False)
            appointment.doctorId = request.POST.get('doctorId')
            appointment.patientId = request.user.id
            appointment.doctorName = models.User.objects.get(id=request.POST.get('doctorId')).first_name
            appointment.patientName = request.user.first_name
            appointment.status = 'Pending'
            appointment.save()
            messages.success(request, "Appointment booked successfully! Awaiting approval.")
            return HttpResponseRedirect('patient-view-appointment')
        else:
            messages.error(request, "Failed to book appointment. Please check the form.")
    return render(request, 'hospital/patient_book_appointment.html', context=mydict)

@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_view_doctor_view(request):
    doctors = models.Doctor.objects.all().filter(status=True)
    patient = models.Patient.objects.get(user_id=request.user.id)
    return render(request, 'hospital/patient_view_doctor.html', {'patient': patient, 'doctors': doctors})

@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def search_doctor_view(request):
    patient = models.Patient.objects.get(user_id=request.user.id)
    query = request.GET['query']
    doctors = models.Doctor.objects.all().filter(status=True).filter(Q(department__icontains=query) | Q(user__first_name__icontains=query))
    return render(request, 'hospital/patient_view_doctor.html', {'patient': patient, 'doctors': doctors})

@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_view_appointment_view(request):
    patient = models.Patient.objects.get(user_id=request.user.id)
    appointments = models.Appointment.objects.all().filter(patientId=request.user.id).order_by('appointmentDate')
    return render(request, 'hospital/patient_view_appointment.html', {'appointments': appointments, 'patient': patient})

@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_reschedule_appointment_view(request, pk):
    patient = models.Patient.objects.get(user_id=request.user.id)
    appointment = get_object_or_404(models.Appointment, id=pk, patientId=request.user.id)
    
    # Prevent rescheduling if the appointment is cancelled or completed
    if appointment.status in ['Cancelled', 'Completed']:
        messages.error(request, f"Cannot reschedule an appointment that is {appointment.status.lower()}.")
        return redirect('patient-view-appointment')

    appointmentForm = forms.PatientRescheduleAppointmentForm(instance=appointment)  # Use the new form
    if request.method == 'POST':
        appointmentForm = forms.PatientRescheduleAppointmentForm(request.POST, instance=appointment)
        if appointmentForm.is_valid():
            appointment = appointmentForm.save(commit=False)
            appointment.status = 'Pending'  # Reset status to Pending after rescheduling
            appointment.save()
            messages.success(request, "Appointment rescheduled successfully! Awaiting approval.")
            return redirect('patient-view-appointment')
        else:
            # Log form errors for debugging
            print("Form errors:", appointmentForm.errors)  # This will print to your console
            messages.error(request, "Failed to reschedule appointment. Please check the form.")

    return render(request, 'hospital/patient_reschedule_appointment.html', {
        'appointmentForm': appointmentForm,
        'patient': patient,
        'appointment': appointment
    })

@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_cancel_appointment_view(request, pk):
    patient = models.Patient.objects.get(user_id=request.user.id)
    appointment = get_object_or_404(models.Appointment, id=pk, patientId=request.user.id)
    
    # Prevent cancelling if the appointment is already cancelled or completed
    if appointment.status in ['Cancelled', 'Completed']:
        messages.error(request, f"Cannot cancel an appointment that is already {appointment.status.lower()}.")
        return redirect('patient-view-appointment')

    if request.method == 'POST':
        appointment.status = 'Cancelled'
        appointment.save()
        messages.success(request, "Appointment cancelled successfully.")
        return redirect('patient-view-appointment')

    return render(request, 'hospital/patient_cancel_appointment.html', {
        'appointment': appointment,
        'patient': patient
    })

@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_discharge_view(request):
    patient = models.Patient.objects.get(user_id=request.user.id)
    dischargeDetails = models.PatientDischargeDetails.objects.all().filter(patientId=patient.id).order_by('-id')[:1]
    patientDict = None
    if dischargeDetails:
        patientDict = {
            'is_discharged': True,
            'patient': patient,
            'patientId': patient.id,
            'patientName': patient.get_name,
            'assignedDoctorName': dischargeDetails[0].assignedDoctorName,
            'address': patient.address,
            'mobile': patient.mobile,
            'symptoms': patient.symptoms,
            'admitDate': patient.admitDate,
            'releaseDate': dischargeDetails[0].releaseDate,
            'daySpent': dischargeDetails[0].daySpent,
            'medicineCost': dischargeDetails[0].medicineCost,
            'roomCharge': dischargeDetails[0].roomCharge,
            'doctorFee': dischargeDetails[0].doctorFee,
            'OtherCharge': dischargeDetails[0].OtherCharge,
            'total': dischargeDetails[0].total,
        }
    else:
        patientDict = {
            'is_discharged': False,
            'patient': patient,
            'patientId': request.user.id,
        }
    return render(request, 'hospital/patient_discharge.html', context=patientDict)

# Nurse-related views


# About and Contact views (unchanged)
def aboutus_view(request):
    return render(request, 'hospital/aboutus.html')

def contactus_view(request):
    sub = forms.ContactusForm()
    if request.method == 'POST':
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            email = sub.cleaned_data['Email']
            name = sub.cleaned_data['Name']
            message = sub.cleaned_data['Message']
            send_mail(str(name) + ' || ' + str(email), message, settings.EMAIL_HOST_USER, settings.EMAIL_RECEIVING_USER, fail_silently=False)
            return render(request, 'hospital/contactussuccess.html')
    return render(request, 'hospital/contactus.html', {'form': sub})

# Pharmacy Views
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_pharmacy_view(request):
    return render(request, 'hospital/admin_pharmacy.html')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_pharmacy_view(request):
    pharmacies = models.Pharmacy.objects.all()
    return render(request, 'hospital/admin_view_pharmacy.html', {'pharmacies': pharmacies})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_pharmacy_view(request):
    pharmacyForm = forms.PharmacyForm()

    if request.method == 'POST':
        pharmacyForm = forms.PharmacyForm(request.POST)

        if pharmacyForm.is_valid():
            pharmacy = pharmacyForm.save()
            if pharmacy.pharmacist:
                pharmacist_group, _ = Group.objects.get_or_create(name='PHARMACIST')
                pharmacy.pharmacist.groups.add(pharmacist_group)
            messages.success(request, "Pharmacy added successfully.")
            return redirect('/admin-view-pharmacy')
        else:
            messages.error(request, "Form validation failed. Please check the fields.")
            for error in pharmacyForm.errors:
                messages.error(request, f"Pharmacy Form Error - {error}: {pharmacyForm.errors[error]}")
    return render(request, 'hospital/admin_add_pharmacy.html', {
        'pharmacyForm': pharmacyForm,
    })

# Medical Record Views
@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_add_medical_record_view(request, patient_id):
    patient = get_object_or_404(models.Patient, id=patient_id)
    medicalRecordForm = forms.DoctorMedicalRecordForm(initial={'doctor': request.user.doctor})
    test_result_formset = forms.TestResultFormSet()

    if request.method == 'POST':
        medicalRecordForm = forms.DoctorMedicalRecordForm(request.POST)
        test_result_formset = forms.TestResultFormSet(request.POST)
        if medicalRecordForm.is_valid() and test_result_formset.is_valid():
            medical_record = medicalRecordForm.save(commit=False)
            medical_record.patient = patient
            medical_record.doctor = request.user.doctor
            medical_record.save()

            test_results = []
            for form in test_result_formset:
                if form.cleaned_data:
                    test = form.cleaned_data.get('test')
                    result = form.cleaned_data.get('result')
                    if test and result:
                        test_results.append({"test": test, "result": result})
            if test_results:
                medical_record.test_results = test_results
                medical_record.save()

            messages.success(request, "Medical record added successfully.")
            return redirect('doctor-view-patient')
    return render(request, 'hospital/doctor_add_medical_record.html', {
        'medicalRecordForm': medicalRecordForm,
        'test_result_formset': test_result_formset,
        'patient': patient,
    })

# Billing Views
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_billing_view(request):
    return render(request, 'hospital/admin_billing.html')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_billing_view(request):
    bills = models.Billing.objects.all()
    return render(request, 'hospital/admin_view_billing.html', {'bills': bills})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_billing_view(request):
    billingForm = forms.BillingForm()
    if request.method == 'POST':
        billingForm = forms.BillingForm(request.POST)
        if billingForm.is_valid():
            bill = billingForm.save(commit=False)
            bill.generate_bill(bill.treatment_cost, bill.medicine_cost)
            return redirect('admin-view-billing')
    return render(request, 'hospital/admin_add_billing.html', {'billingForm': billingForm})

# Ward/Room Views
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_ward_room_view(request):
    return render(request, 'hospital/admin_ward_room.html')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_ward_room_view(request):
    rooms = models.WardRoom.objects.all()
    return render(request, 'hospital/admin_view_ward_room.html', {'rooms': rooms})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_ward_room_view(request):
    wardRoomForm = forms.WardRoomForm()
    if request.method == 'POST':
        wardRoomForm = forms.WardRoomForm(request.POST)
        if wardRoomForm.is_valid():
            wardRoomForm.save()
            return redirect('admin-view-ward-room')
    return render(request, 'hospital/admin_add_ward_room.html', {'wardRoomForm': wardRoomForm})

# Pharmacy Views
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_pharmacy_view(request):
    return render(request, 'hospital/admin_pharmacy.html')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_pharmacy_view(request):
    pharmacies = models.Pharmacy.objects.all()
    return render(request, 'hospital/admin_view_pharmacy.html', {'pharmacies': pharmacies})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_pharmacy_view(request):
    pharmacyForm = forms.PharmacyForm()
    if request.method == 'POST':
        pharmacyForm = forms.PharmacyForm(request.POST)
        if pharmacyForm.is_valid():
            pharmacyForm.save()
            messages.success(request, "Pharmacy added successfully.")
            return redirect('admin-view-pharmacy')
    return render(request, 'hospital/admin_add_pharmacy.html', {'pharmacyForm': pharmacyForm})

# Medical Record Views
@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_add_medical_record_view(request, patient_id):
    patient = get_object_or_404(models.Patient, id=patient_id)
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    medicalRecordForm = forms.MedicalRecordForm(initial={'patient': patient, 'doctor': doctor})
    if request.method == 'POST':
        medicalRecordForm = forms.MedicalRecordForm(request.POST)
        if medicalRecordForm.is_valid():
            medicalRecordForm.save()
            messages.success(request, "Medical record added successfully.")
            return redirect('doctor-view-patient')
    return render(request, 'hospital/doctor_add_medical_record.html', {'medicalRecordForm': medicalRecordForm, 'patient': patient})

# Billing Views
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_billing_view(request):
    return render(request, 'hospital/admin_billing.html')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_billing_view(request):
    bills = models.Billing.objects.all()
    return render(request, 'hospital/admin_view_billing.html', {'bills': bills})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_billing_view(request):
    billingForm = forms.BillingForm()
    if request.method == 'POST':
        billingForm = forms.BillingForm(request.POST)
        if billingForm.is_valid():
            bill = billingForm.save(commit=False)
            bill.generate_bill(bill.treatment_cost, bill.medicine_cost)
            messages.success(request, "Bill generated successfully.")
            return redirect('admin-view-billing')
    return render(request, 'hospital/admin_add_billing.html', {'billingForm': billingForm})

# Ward/Room Views
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_ward_room_view(request):
    return render(request, 'hospital/admin_ward_room.html')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_ward_room_view(request):
    rooms = models.WardRoom.objects.all()
    return render(request, 'hospital/admin_view_ward_room.html', {'rooms': rooms})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_ward_room_view(request):
    wardRoomForm = forms.WardRoomForm()
    if request.method == 'POST':
        wardRoomForm = forms.WardRoomForm(request.POST)
        if wardRoomForm.is_valid():
            wardRoomForm.save()
            messages.success(request, "Ward/Room added successfully.")
            return redirect('admin-view-ward-room')
    return render(request, 'hospital/admin_add_ward_room.html', {'wardRoomForm': wardRoomForm})

# Nurse Views


# Medical Records Related files

# Patient: View own medical records
@login_required
def patient_medical_records(request):
    if not hasattr(request.user, 'patient'):
        messages.error(request, "You are not registered as a patient.")
        return redirect('home')  # Replace with your home URL, e.g., 'login'
    patient = request.user.patient
    records = patient.medical_history.all()
    return render(request, 'hospital/patient_medical_records.html', {
        'patient': patient,
        'medical_records': records
    })

# Doctor: View a patient's medical records
@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_view_medical_records(request, patient_id):
    patient = get_object_or_404(models.Patient, id=patient_id)
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    records = models.MedicalRecord.objects.filter(patient=patient, doctor=doctor).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        records = records.filter(
            Q(diagnosis__icontains=search_query) |
            Q(prescribed_treatment__icontains=search_query) |
            Q(record_id__icontains=search_query)
        )
    
    # Check for an existing record before pagination
    existing_record = records.first()  # This works because records is still a QuerySet
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(records, 10)
    try:
        records_page = paginator.page(page)
    except PageNotAnInteger:
        records_page = paginator.page(1)
    except EmptyPage:
        records_page = paginator.page(paginator.num_pages)
    
    return render(request, 'hospital/doctor_medical_records.html', {
        'medical_records': records_page,
        'patient': patient,
        'doctor': doctor,
        'search_query': search_query,
        'existing_record': existing_record,
    })

def is_doctor(user):
    return hasattr(user, 'doctor')

@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_delete_medical_record(request, record_id):
    record = get_object_or_404(models.MedicalRecord, record_id=record_id)
    # Ensure the record belongs to the logged-in doctor
    if record.doctor.user_id != request.user.id:
        messages.error(request, "You do not have permission to delete this record.")
        return redirect('doctor_view_medical_records', patient_id=record.patient.id)
    
    # Store patient_id for redirection
    patient_id = record.patient.id
    # Delete the record
    record.delete()
    messages.success(request, f"Medical record {record_id} deleted successfully.")
    return redirect('doctor_view_medical_records', patient_id=patient_id)


# Doctor: Update Patient
@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_update_patient_view(request, pk):
    patient = models.Patient.objects.get(id=pk)
    user = models.User.objects.get(id=patient.user_id)
    userForm = forms.PatientUserForm(instance=user)
    patientForm = forms.PatientForm(request.FILES, instance=patient)
    mydict = {'userForm': userForm, 'patientForm': patientForm}
    if request.method == 'POST':
        userForm = forms.PatientUserForm(request.POST, instance=user)
        patientForm = forms.PatientForm(request.POST, request.FILES, instance=patient)
        if userForm.is_valid() and patientForm.is_valid():
            user = userForm.save()
            user.set_password(user.password)
            user.save()
            patient = patientForm.save(commit=False)
            patient.status = True
            patient.save()
            messages.success(request, "Patient details updated successfully.")
            return redirect('doctor-view-patient')
    return render(request, 'hospital/doctor_update_patient.html', context=mydict)


# Doctor: Add a medical record
@login_required
def add_medical_record(request, patient_id):
    if not hasattr(request.user, 'doctor'):
        messages.error(request, "You do not have permission to add records.")
        return redirect('home')
    patient = get_object_or_404(models.Patient, id=patient_id)
    if request.method == 'POST':
        form = forms.DoctorMedicalRecordForm(request.POST)
        test_result_formset = forms.TestResultFormSet(request.POST)
        if form.is_valid() and test_result_formset.is_valid():
            record = form.save(commit=False)
            record.record_id = f"REC{timezone.now().strftime('%Y%m%d%H%M%S')}"
            record.patient = patient
            record.doctor = request.user.doctor
            # Convert formset data to JSON array
            test_results = []
            for test_form in test_result_formset:
                if test_form.cleaned_data and test_form.cleaned_data['test'] and test_form.cleaned_data['result']:
                    test_results.append({
                        'test': test_form.cleaned_data['test'],
                        'result': test_form.cleaned_data['result'],
                    })
            record.test_results = test_results
            record.save()
            messages.success(request, "Medical record added successfully.")
            return redirect('doctor_view_medical_records', patient_id=patient_id)
    else:
        form = forms.DoctorMedicalRecordForm()
        test_result_formset = forms.TestResultFormSet()
    return render(request, 'hospital/add_medical_record.html', {
        'form': form,
        'test_result_formset': test_result_formset,
        'patient': patient
    })

# Admin: View all medical records
@login_required
def admin_view_medical_records(request):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home')
    records = MedicalRecord.objects.select_related('patient', 'doctor').all()
    return render(request, 'hospital/admin_medical_records.html', {
        'medical_records': records
    })

# Admin: Add a medical record
@login_required
def admin_add_medical_record(request):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to add records.")
        return redirect('home')
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(request, "Medical record added successfully.")
            return redirect('admin_view_medical_records')
    else:
        form = MedicalRecordForm()
    return render(request, 'hospital/admin_add_medical_record.html', {
        'form': form
    })

# Admin: Edit a medical record
@login_required
def edit_medical_record(request, record_id):
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to edit records.")
        return redirect('home')
    record = get_object_or_404(MedicalRecord, record_id=record_id)
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Medical record updated successfully.")
            return redirect('admin_view_medical_records')
    else:
        # Pre-populate test_results as JSON string
        form = MedicalRecordForm(instance=record, initial={'test_results': json.dumps(record.test_results)})
    return render(request, 'hospital/edit_medical_record.html', {
        'form': form,
        'record': record,
        'patient': record.patient
    })

# Add medical record view (consistent with your style)
@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_add_medical_record(request, patient_id):
    patient = get_object_or_404(models.Patient, id=patient_id)
    doctor = models.Doctor.objects.get(user_id=request.user.id)
    
    if request.method == 'POST':
        form = forms.DoctorMedicalRecordForm(request.POST)
        test_result_formset = forms.TestResultFormSet(request.POST)
        if form.is_valid() and test_result_formset.is_valid():
            record = form.save(commit=False)
            record.record_id = f"REC{timezone.now().strftime('%Y%m%d%H%M%S')}"
            record.patient = patient
            record.doctor = doctor
            test_results = []
            for test_form in test_result_formset:
                if test_form.cleaned_data and test_form.cleaned_data['test'] and test_form.cleaned_data['result']:
                    test_results.append({
                        'test': test_form.cleaned_data['test'],
                        'result': test_form.cleaned_data['result'],
                    })
            record.test_results = test_results
            record.save()
            messages.success(request, "Medical record added successfully!")
            return redirect('doctor_view_medical_records', patient_id=patient.id)
    else:
        form = forms.DoctorMedicalRecordForm()
        test_result_formset = forms.TestResultFormSet()
    
    return render(request, 'hospital/doctor_add_medical_record.html', {
        'form': form,
        'test_result_formset': test_result_formset,
        'patient': patient,
        'doctor': doctor,
    })

@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def doctor_edit_medical_record(request, record_id):
    record = get_object_or_404(models.MedicalRecord, record_id=record_id)
    if record.doctor.user_id != request.user.id:
        messages.error(request, "You do not have permission to edit this record.")
        return redirect('doctor_view_medical_records', patient_id=record.patient.id)

    if request.method == 'POST':
        print("POST data:", request.POST)  # Debug: Inspect submitted data
        form = forms.DoctorMedicalRecordForm(request.POST, instance=record)
        test_result_formset = forms.TestResultFormSet(request.POST)
        if form.is_valid() and test_result_formset.is_valid():
            record = form.save(commit=False)
            test_results = []
            for test_form in test_result_formset:
                if test_form.cleaned_data and test_form.cleaned_data['test'] and test_form.cleaned_data['result']:
                    test_results.append({
                        'test': test_form.cleaned_data['test'],
                        'result': test_form.cleaned_data['result'],
                    })
            record.test_results = test_results
            record.save()
            messages.success(request, "Medical record updated successfully.")
            return redirect('doctor_view_medical_records', patient_id=record.patient.id)
        else:
            messages.error(request, "Form validation failed. Please check the fields.")
            print("Form errors:", form.errors)  # Debug: Print form errors
            print("Formset errors:", test_result_formset.errors)  # Debug: Print formset errors
    else:
        form = forms.DoctorMedicalRecordForm(instance=record)
        initial_data = [{'test': item['test'], 'result': item['result']} for item in record.test_results]
        test_result_formset = forms.TestResultFormSet(initial=initial_data if initial_data else None)
        print("Initial treatment_quantities:", form['treatment_quantities'].value())  # Debug: Check initial value

    return render(request, 'hospital/doctor_edit_medical_record.html', {
        'form': form,
        'test_result_formset': test_result_formset,
        'record': record,
        'patient': record.patient,
    })


# Pharmacy

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_pharmacy_view(request):
    return render(request, 'hospital/admin_pharmacy.html')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_pharmacy_view(request):
    pharmacies = models.Pharmacy.objects.all()
    return render(request, 'hospital/admin_view_pharmacy.html', {'pharmacies': pharmacies})

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_pharmacy_view(request):
    pharmacyForm = forms.PharmacyForm()
    if request.method == 'POST':
        pharmacyForm = forms.PharmacyForm(request.POST)
        if pharmacyForm.is_valid():
            pharmacy = pharmacyForm.save()
            if pharmacy.pharmacist:
                pharmacist_group, _ = Group.objects.get_or_create(name='PHARMACIST')
                pharmacy.pharmacist.groups.add(pharmacist_group)
            messages.success(request, "Pharmacy added successfully.")
            return redirect('/admin-view-pharmacy')
    return render(request, 'hospital/admin_add_pharmacy.html', {
        'pharmacyForm': pharmacyForm,
        'medicine_placeholder': 'Available Medicines (JSON, e.g., {"Paracetamol": 50, "Ibuprofen": 30})'
    })

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_update_pharmacy_view(request, pk):
    pharmacy = models.Pharmacy.objects.get(id=pk)
    pharmacyForm = forms.PharmacyForm(instance=pharmacy)

    if request.method == 'POST':
        pharmacyForm = forms.PharmacyForm(request.POST, instance=pharmacy)

        if pharmacyForm.is_valid():
            pharmacy = pharmacyForm.save()
            pharmacist_group, _ = Group.objects.get_or_create(name='PHARMACIST')
            old_pharmacist = models.Pharmacy.objects.get(id=pk).pharmacist
            if old_pharmacist and old_pharmacist != pharmacy.pharmacist:
                old_pharmacist.groups.remove(pharmacist_group)
            if pharmacy.pharmacist:
                pharmacy.pharmacist.groups.add(pharmacist_group)
            messages.success(request, "Pharmacy updated successfully.")
            return redirect('/admin-view-pharmacy')
        else:
            messages.error(request, "Form validation failed. Please check the fields.")
            for error in pharmacyForm.errors:
                messages.error(request, f"Pharmacy Form Error - {error}: {pharmacyForm.errors[error]}")
    return render(request, 'hospital/admin_update_pharmacy.html', {
        'pharmacyForm': pharmacyForm,
    })

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_delete_pharmacy_view(request, pk):
    pharmacy = models.Pharmacy.objects.get(id=pk)
    if pharmacy.pharmacist:
        pharmacist_group = Group.objects.get(name='PHARMACIST')
        pharmacy.pharmacist.groups.remove(pharmacist_group)
    pharmacy.delete()
    messages.success(request, "Pharmacy deleted successfully.")
    return redirect('/admin-view-pharmacy')

@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_dispense_medication_view(request, patient_id=None):
    if patient_id:
        patient = get_object_or_404(models.Patient, id=patient_id, status=True, assigned_room__isnull=False)
        medical_records = models.MedicalRecord.objects.filter(patient=patient, status='pending').select_related('patient')
    else:
        patient = None
        medical_records = models.MedicalRecord.objects.filter(
            patient__status=True, 
            patient__assigned_room__isnull=False, 
            status='pending'
        ).select_related('patient')

    pharmacies = models.Pharmacy.objects.all()

    if request.method == 'POST':
        pharmacy_id = request.POST.get('pharmacy')
        prescription_id = request.POST.get('prescription')

        try:
            pharmacy = models.Pharmacy.objects.get(id=pharmacy_id)
            prescription = models.MedicalRecord.objects.get(id=prescription_id)

            success, result = pharmacy.dispense_medication(prescription)
            if success:
                prescription.dispensed_items = result
                prescription.status = 'dispensed'
                prescription.save()
                messages.success(request, "Medication dispensed successfully.")
            else:
                error_msg = result.get("error", "Unknown error occurred")
                messages.error(request, f"Failed to dispense medication: {error_msg}")

            return redirect('admin-dispense-medication') if patient_id is None else redirect('admin-dispense-medication-for-patient', patient_id=patient_id)

        except models.Pharmacy.DoesNotExist:
            messages.error(request, "Invalid pharmacy selected.")
        except models.MedicalRecord.DoesNotExist:
            messages.error(request, "Invalid prescription selected.")
        except Exception as e:
            messages.error(request, f"Error during dispensing: {str(e)}")

    return render(request, 'hospital/admin_dispense_medication.html', {
        'pharmacies': pharmacies,
        'medical_records': medical_records,
        'patient': patient,
    })

# Rooms

def is_doctor(user):
    return hasattr(user, 'doctor')

@login_required(login_url='doctorlogin')
@user_passes_test(is_doctor)
def room_management(request):
    rooms = models.WardRoom.objects.all()
    
    # Calculate room counts
    total_rooms_count = rooms.count()
    available_rooms_count = rooms.filter(availability=True).count()
    occupied_rooms_count = rooms.filter(availability=False).count()
    
    if request.method == 'POST':
        if 'assign' in request.POST:
            assign_form = forms.RoomAssignmentForm(request.POST)
            discharge_form = forms.RoomDischargeForm()
            if assign_form.is_valid():
                room = assign_form.cleaned_data['room']
                patient = assign_form.cleaned_data['patient']
                if room.assign_room(patient):
                    messages.success(request, f"Room {room.room_id} assigned to {patient.get_name} successfully.") 
                else:
                    messages.error(request, f"Failed to assign Room {room.room_id}. It may not be available.")
                return redirect('room_management')
        elif 'discharge' in request.POST:
            assign_form = forms.RoomAssignmentForm()
            discharge_form = forms.RoomDischargeForm(request.POST)
            if discharge_form.is_valid():
                room = discharge_form.cleaned_data['room']
                try:
                    room.discharge_patient()
                    messages.success(request, f"Patient discharged from Room {room.room_id} successfully.")
                except ValueError as e:
                    messages.error(request, str(e))
                return redirect('room_management')
    else:
        assign_form = forms.RoomAssignmentForm()
        discharge_form = forms.RoomDischargeForm()
    
    return render(request, 'hospital/room_management.html', {
        'rooms': rooms,
        'assign_form': assign_form,
        'discharge_form': discharge_form,
        'total_rooms_count': total_rooms_count,
        'available_rooms_count': available_rooms_count,
        'occupied_rooms_count': occupied_rooms_count,
    })


# Departements
# List all departments
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_list_departments(request):
    departments = models.Department.objects.all().order_by('name')
    return render(request, 'hospital/admin_list_departments.html', {'departments': departments})

# Add a new department
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_add_department(request):
    if request.method == 'POST':
        form = forms.DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Department added successfully!")
            return redirect('admin-view-departments')  # Updated redirect
        else:
            messages.error(request, "Failed to add department. Please check the form.")
    else:
        form = forms.DepartmentForm()
    return render(request, 'hospital/admin_add_department.html', {'form': form})

# View department details
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_view_department(request, department_id):
    department = get_object_or_404(models.Department, department_id=department_id)
    return render(request, 'hospital/admin_view_department.html', {'department': department})

# Update a department
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_update_department(request, department_id):
    department = get_object_or_404(models.Department, department_id=department_id)
    if request.method == 'POST':
        form = forms.DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated successfully!")
            return redirect('admin-view-departments')  # Updated redirect
        else:
            messages.error(request, "Failed to update department. Please check the form.")
    else:
        form = forms.DepartmentForm(instance=department)
    return render(request, 'hospital/admin_add_department.html', {'form': form, 'department': department})

# Delete a department
@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def admin_delete_department(request, department_id):
    department = get_object_or_404(models.Department, department_id=department_id)
    if request.method == 'POST':
        department.delete()
        messages.success(request, "Department deleted successfully!")
        return redirect('admin-view-departments')
    return render(request, 'hospital/admin_delete_department.html', {'department': department})

# view for patients to view departments
@login_required(login_url='patientlogin')
@user_passes_test(is_patient)
def patient_view_departments(request):
    departments = models.Department.objects.all().order_by('name')
    patient = models.Patient.objects.get(user_id=request.user.id)
    return render(request, 'hospital/patient_view_departments.html', {
        'departments': departments,
        'patient': patient,
    })


@login_required(login_url='adminlogin')
@user_passes_test(is_admin)
def generate_bill_pdf(request, patient_id):
    patient = get_object_or_404(models.Patient, id=patient_id)
    bill = models.Billing.objects.filter(patient=patient).first()
    discharge = models.PatientDischargeDetails.objects.filter(patientId=patient_id).first()

    if not bill or not discharge:
        messages.error(request, "Bill or discharge details not found.")
        return redirect('admin-view-departments')

    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    # PDF content
    p.setFont("Helvetica", 16)
    p.drawString(100, 750, "Hospital Bill")
    p.setFont("Helvetica", 12)
    p.drawString(100, 730, f"Bill ID: {bill.bill_id}")
    p.drawString(100, 710, f"Patient Name: {patient.get_name}")
    p.drawString(100, 690, f"Admit Date: {discharge.admitDate}")
    p.drawString(100, 670, f"Release Date: {discharge.releaseDate}")
    p.drawString(100, 650, f"Days Spent: {discharge.daySpent}")
    p.drawString(100, 630, f"Room Charge: ${discharge.roomCharge}")
    p.drawString(100, 610, f"Doctor Fee: ${discharge.doctorFee}")
    p.drawString(100, 590, f"Medicine Cost: ${discharge.medicineCost}")
    p.drawString(100, 570, f"Other Charges: ${discharge.OtherCharge}")
    p.drawString(100, 550, f"Total Amount: ${discharge.total}")
    p.drawString(100, 530, f"Payment Status: {bill.payment_status}")
    p.drawString(100, 510, f"Generated On: {timezone.now()}")

    p.showPage()
    p.save()

    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"bill_{bill.bill_id}.pdf")