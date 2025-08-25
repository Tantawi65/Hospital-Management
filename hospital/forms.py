# hospital/forms.py
from django import forms
from . import models
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
import django.forms as forms
import json
from . import models
from django.forms import formset_factory
from django.contrib.auth.models import User, Group  # Added Group here

# Existing forms (unchanged)
class AdminSigupForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'password']
        widgets = {'password': forms.PasswordInput()}

class DoctorUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'password']
        widgets = {'password': forms.PasswordInput()}

class DoctorForm(forms.ModelForm):
    class Meta:
        model = models.Doctor
        fields = ['address', 'mobile', 'department', 'status', 'profile_pic']

class PatientUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'password']
        widgets = {'password': forms.PasswordInput()}

class PatientForm(forms.ModelForm):
    assignedDoctorId = forms.ModelChoiceField(
        queryset=models.Doctor.objects.all().filter(status=True),
        empty_label="Name and Department",
        to_field_name="user_id"
    )
    
    class Meta:
        model = models.Patient
        fields = ['address', 'mobile', 'email', 'symptoms', 'age', 'gender', 'profile_pic']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}, choices=[('', 'Select Gender'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]),
            'profile_pic': forms.FileInput(attrs={'class': 'form-control', 'required': 'required'}),
        }

class NurseUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'password']
        widgets = {'password': forms.PasswordInput()}

class NurseForm(forms.ModelForm):
    class Meta:
        model = models.Nurse
        fields = ['mobile', 'assignedWard', 'profile_pic']

class NurseLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))

class AppointmentForm(forms.ModelForm):
    doctorId = forms.ModelChoiceField(queryset=models.Doctor.objects.all().filter(status=True), empty_label="Doctor Name and Department", to_field_name="user_id")
    patientId = forms.ModelChoiceField(queryset=models.Patient.objects.all().filter(status=True), empty_label="Patient Name and Symptoms", to_field_name="user_id")
    appointmentDate = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        label="Appointment Date and Time"
    )

    class Meta:
        model = models.Appointment
        fields = ['description', 'status', 'appointmentDate']
        widgets = {'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})}

class PatientAppointmentForm(forms.ModelForm):
    doctorId = forms.ModelChoiceField(queryset=models.Doctor.objects.all().filter(status=True), empty_label="Doctor Name and Department", to_field_name="user_id")
    appointmentDate = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        label="Appointment Date and Time"
    )

    class Meta:
        model = models.Appointment
        fields = ['description', 'appointmentDate']
        widgets = {'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})}

class PatientRescheduleAppointmentForm(forms.ModelForm):
    appointmentDate = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        label="Appointment Date and Time"
    )

    class Meta:
        model = models.Appointment
        fields = ['description', 'appointmentDate']
        widgets = {'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.appointmentDate:
            self.initial['appointmentDate'] = self.instance.appointmentDate.strftime('%Y-%m-%dT%H:%M')

    def clean_appointmentDate(self):
        appointment_date = self.cleaned_data.get('appointmentDate')
        if appointment_date and appointment_date < timezone.now():
            raise forms.ValidationError("Appointment date must be in the future.")
        if appointment_date and not timezone.is_aware(appointment_date):
            appointment_date = timezone.make_aware(appointment_date)
        return appointment_date

class ContactusForm(forms.Form):
    Name = forms.CharField(max_length=30)
    Email = forms.EmailField()
    Message = forms.CharField(max_length=500, widget=forms.Textarea(attrs={'rows': 3, 'cols': 30}))

class PharmacyForm(forms.ModelForm):
    # Fields for the first medicine
    medicine_name_1 = forms.CharField(max_length=100, required=False, label="Medicine Name 1")
    quantity_1 = forms.IntegerField(min_value=0, required=False, label="Quantity 1", initial=0)
    price_1 = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False, label="Price 1", initial=0.00)

    # Fields for the second medicine
    medicine_name_2 = forms.CharField(max_length=100, required=False, label="Medicine Name 2")
    quantity_2 = forms.IntegerField(min_value=0, required=False, label="Quantity 2", initial=0)
    price_2 = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0, required=False, label="Price 2", initial=0.00)

    class Meta:
        model = models.Pharmacy
        fields = ['pharmacy_id', 'pharmacist', 'available_medicines']
        widgets = {
            'pharmacy_id': forms.TextInput(attrs={'class': 'form-control'}),
            'pharmacist': forms.Select(attrs={'class': 'form-control'}),
            'available_medicines': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        doctor_group = Group.objects.get(name='DOCTOR')
        self.fields['pharmacist'].queryset = User.objects.filter(groups=doctor_group)

        # If editing, prefill the medicine fields from available_medicines
        if self.instance and self.instance.available_medicines:
            medicines = list(self.instance.available_medicines.items())
            if len(medicines) > 0:
                self.fields['medicine_name_1'].initial = medicines[0][0]
                self.fields['quantity_1'].initial = medicines[0][1].get('quantity', 0)
                self.fields['price_1'].initial = medicines[0][1].get('price', 0.00)
            if len(medicines) > 1:
                self.fields['medicine_name_2'].initial = medicines[1][0]
                self.fields['quantity_2'].initial = medicines[1][1].get('quantity', 0)
                self.fields['price_2'].initial = medicines[1][1].get('price', 0.00)

    def clean(self):
        cleaned_data = super().clean()
        medicines = {}

        # Validate first medicine
        med_name_1 = cleaned_data.get('medicine_name_1')
        quantity_1 = cleaned_data.get('quantity_1')
        price_1 = cleaned_data.get('price_1')
        if med_name_1 or quantity_1 is not None or price_1 is not None:
            if not med_name_1:
                raise forms.ValidationError("Medicine name 1 is required if quantity or price is provided.")
            if quantity_1 is None:
                raise forms.ValidationError("Quantity 1 is required if medicine name or price is provided.")
            if price_1 is None:
                raise forms.ValidationError("Price 1 is required if medicine name or quantity is provided.")
            medicines[med_name_1] = {'quantity': quantity_1, 'price': float(price_1)}

        # Validate second medicine
        med_name_2 = cleaned_data.get('medicine_name_2')
        quantity_2 = cleaned_data.get('quantity_2')
        price_2 = cleaned_data.get('price_2')
        if med_name_2 or quantity_2 is not None or price_2 is not None:
            if not med_name_2:
                raise forms.ValidationError("Medicine name 2 is required if quantity or price is provided.")
            if quantity_2 is None:
                raise forms.ValidationError("Quantity 2 is required if medicine name or price is provided.")
            if price_2 is None:
                raise forms.ValidationError("Price 2 is required if medicine name or quantity is provided.")
            if med_name_2 in medicines:
                raise forms.ValidationError("Medicine names must be unique.")
            medicines[med_name_2] = {'quantity': quantity_2, 'price': float(price_2)}

        cleaned_data['available_medicines'] = medicines or None
        return cleaned_data

    def clean_available_medicines(self):
        data = self.cleaned_data['available_medicines']
        if data is None or (isinstance(data, dict) and not data):
            return None
        if not isinstance(data, dict):
            raise forms.ValidationError("Available medicines must be a dictionary.")
        for key, value in data.items():
            if not isinstance(value, dict) or 'quantity' not in value or 'price' not in value:
                raise forms.ValidationError("Each medicine must have a quantity and price.")
            if not isinstance(value['quantity'], int) or value['quantity'] < 0:
                raise forms.ValidationError("Medicine quantities must be non-negative integers.")
            if not isinstance(value['price'], (int, float)) or value['price'] < 0:
                raise forms.ValidationError("Medicine prices must be non-negative numbers.")
        return data

class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = models.MedicalRecord
        fields = ['record_id', 'patient', 'doctor', 'diagnosis', 'prescribed_treatment', 'test_results']
        widgets = {
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'prescribed_treatment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'test_results': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'JSON format, e.g., [{"test": "Blood Sugar", "result": "100"}]'}),
        }

    def clean_test_results(self):
        data = self.cleaned_data['test_results']
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            raise forms.ValidationError("Invalid JSON format for test results.")

# New form for doctors
class DoctorMedicalRecordForm(forms.ModelForm):
    prescribed_treatment = forms.MultipleChoiceField(
        choices=[],  # Will be populated dynamically
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),
        required=False,
        label="Prescribed Treatment (Select Medicines)"
    )
    treatment_quantities = forms.CharField(
        required=False,
        label="Quantities for Prescribed Medicines",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'e.g., [2, 1] (one number per selected medicine)'})
    )

    class Meta:
        model = models.MedicalRecord
        fields = ['diagnosis', 'prescribed_treatment', 'treatment_quantities']
        widgets = {
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        available_medicines = {}
        for pharmacy in models.Pharmacy.objects.all():
            if pharmacy.available_medicines:
                available_medicines.update({med.lower(): med for med in pharmacy.available_medicines.keys()})
        self.fields['prescribed_treatment'].choices = list(available_medicines.items())
        if self.instance.pk and self.instance.prescribed_treatment:
            try:
                initial_medicines = json.loads(self.instance.prescribed_treatment)
                self.fields['prescribed_treatment'].initial = initial_medicines
            except (json.JSONDecodeError, TypeError):
                self.fields['prescribed_treatment'].initial = []
        if self.instance.pk:
            if self.instance.treatment_quantities:
                try:
                    initial_quantities = json.loads(self.instance.treatment_quantities)
                    if not isinstance(initial_quantities, list):
                        initial_quantities = []
                    self.fields['treatment_quantities'].initial = json.dumps(initial_quantities)
                except (json.JSONDecodeError, TypeError):
                    self.fields['treatment_quantities'].initial = '[]'
            else:
                self.fields['treatment_quantities'].initial = '[]'

    def clean(self):
        cleaned_data = super().clean()
        medicines = cleaned_data.get('prescribed_treatment', [])
        quantities_input = cleaned_data.get('treatment_quantities')

        if quantities_input is None or quantities_input == '':
            quantities_input = '[]'
        else:
            quantities_input = str(quantities_input)

        if medicines and not quantities_input.strip():
            raise forms.ValidationError("Please specify quantities for the prescribed medicines.")

        try:
            quantities_list = json.loads(quantities_input)
            if not isinstance(quantities_list, list):
                raise ValueError("Quantities must be a JSON list of numbers.")
            if len(medicines) != len(quantities_list):
                raise ValueError(f"Number of quantities ({len(quantities_list)}) must match number of medicines ({len(medicines)}).")
            for qty in quantities_list:
                if not isinstance(qty, (int, float)) or qty <= 0:
                    raise ValueError(f"Invalid quantity: must be a positive number, got {qty}")
            formatted_quantities = ", ".join([ f"{med.title()}: {qty}" for med, qty in zip(medicines, quantities_list)]) 
            cleaned_data['treatment_quantities'] = formatted_quantities
        except (json.JSONDecodeError, ValueError) as e:
            raise forms.ValidationError(f"Invalid quantities format. Use a JSON list like [2, 1]. Error: {str(e)}")

        cleaned_data['prescribed_treatment'] = ", ".join([med.title() for med in medicines]) if medicines else None
        return cleaned_data
        
class TestResultForm(forms.Form):
    test = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Blood Sugar'}))
    result = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 100'}))

TestResultFormSet = formset_factory(TestResultForm, extra=1)

# Billing and discharge
class BillingForm(forms.ModelForm):
    class Meta:
        model = models.Billing
        fields = ['bill_id', 'patient', 'treatment_cost', 'medicine_cost', 'payment_status']

class DischargeForm(forms.Form):
    roomCharge = forms.DecimalField(
        label="Room Charge per Day (in EGP)",
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=True,
        help_text="Enter the room charge per day."
    )
    doctorFee = forms.DecimalField(
        label="Doctor Fee (in EGP)",
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=True,
        help_text="Enter the doctor fee."
    )
    OtherCharge = forms.DecimalField(
        label="Other Charges (in EGP)",
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=True,
        help_text="Enter any other charges."
    )
    medicineCost = forms.DecimalField(
        label="Medicine Fee (in EGP)",
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=True,
        help_text="Enter the total cost of medicines."
    )
        
# Room

class WardRoomForm(forms.ModelForm):
    class Meta:
        model = models.WardRoom
        fields = ['room_id', 'type', 'ward', 'availability']

class RoomAssignmentForm(forms.Form):
    patient = forms.ModelChoiceField(
        queryset=models.Patient.objects.filter(assigned_room__isnull=True),
        label="Select Patient",
        help_text="Choose a patient not currently assigned to a room"
    )
    room = forms.ModelChoiceField(
        queryset=models.WardRoom.objects.filter(availability=True),
        label="Select Room",
        help_text="Choose an available room"
    )

class RoomDischargeForm(forms.Form):
    room = forms.ModelChoiceField(
        queryset=models.WardRoom.objects.filter(availability=False),
        label="Select Room to Discharge",
        help_text="Choose an occupied room to discharge the patient"
    )


# Departments
class DepartmentForm(forms.ModelForm):
    class Meta:
        model = models.Department
        fields = ['department_id', 'name', 'head_of_department', 'services_offered']
        widgets = {
            'services_offered': forms.Textarea(attrs={'rows': 3, 'placeholder': 'e.g., Heart Surgery, ECG, Consultations'}),
        }
        help_texts = {
            'department_id': 'Enter a unique ID for the department (e.g., DPT001). Must be unique.',
            'name': 'Select the department name from the list (e.g., Cardiologist). Must be unique.',
            'head_of_department': 'Choose the doctor who will lead this department. Only active doctors are listed.',
            'services_offered': 'Enter a comma-separated list of services offered by the department (e.g., Heart Surgery, ECG, Consultations).',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['head_of_department'].queryset = models.Doctor.objects.filter(status=True)