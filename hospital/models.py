import django
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import JSONField
import json
from django.core.exceptions import ValidationError
from multipledispatch import dispatch

departments = [
    ('Cardiologist', 'Cardiologist'),
    ('Dermatologists', 'Dermatologists'),
    ('Emergency Medicine Specialists', 'Emergency Medicine Specialists'),
    ('Allergists/Immunologists', 'Allergists/Immunologists'),
    ('Anesthesiologists', 'Anesthesiologists'),
    ('Colon and Rectal Surgeons', 'Colon and Rectal Surgeons')
]

# Concept: Abstraction - Abstract base class using Django's abstract model
class HospitalEntity(models.Model):
    class Meta:
        abstract = True

    # Abstract methods (to be overridden by subclasses)
    def get_info(self):
        raise NotImplementedError("Subclasses must implement get_info()")

    def update_status(self):
        raise NotImplementedError("Subclasses must implement update_status()")

# Concept: Inheritance - Doctor inherits from HospitalEntity
class Doctor(HospitalEntity):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_pic = models.ImageField(upload_to='profile_pic/DoctorProfilePic/', null=True, blank=True)
    address = models.CharField(max_length=40)
    mobile = models.CharField(max_length=20, null=True)
    department = models.CharField(max_length=50, choices=departments, default='Cardiologist')
    status = models.BooleanField(default=False)

    @property
    def get_name(self):
        return self.user.first_name + " " + self.user.last_name

    @property
    def get_id(self):
        return self.user.id

    # Concept: Method Overriding - Implementing abstract method
    def get_info(self):
        return {"id": self.get_id, "name": self.get_name, "department": self.department}

    def update_status(self):
        self.status = not self.status
        self.save()

    def diagnose_patient(self, patient, diagnosis):
        record = MedicalRecord.objects.create(
            record_id=f"REC{timezone.now().strftime('%Y%m%d%H%M%S')}",
            patient=patient,
            doctor=self,
            diagnosis=diagnosis
        )
        return record

    def prescribe_medication(self, patient, medications):
        record = self.diagnose_patient(patient, "Prescription Update")
        record.prescribed_treatment = ", ".join(medications)
        record.save()
        return record

    def view_patient_records(self, patient):
        return MedicalRecord.objects.filter(patient=patient, doctor=self)

    def __str__(self):
        return "{} ({})".format(self.user.first_name, self.department)

# Concept: Inheritance - Patient inherits from HospitalEntity
class Patient(HospitalEntity):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_pic = models.ImageField(upload_to='profile_pic/PatientProfilePic/', null=False, blank=False)
    address = models.CharField(max_length=40)
    mobile = models.CharField(max_length=20, null=False)
    email = models.EmailField(max_length=100, blank=True, null=True)
    symptoms = models.CharField(max_length=100, null=False)
    assignedDoctorId = models.PositiveIntegerField(null=True)
    admitDate = models.DateField(auto_now=True)
    status = models.BooleanField(default=False)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')],
        null=True,
        blank=True
    )

    @property
    def get_name(self):
        return self.user.first_name + " " + self.user.last_name

    @property
    def get_id(self):
        return self.user.id

    # Concept: Method Overriding - Implementing abstract method
    def get_info(self):
        return {
            "id": self.id,
            "name": self.get_name,
            "age": self.age,
            "gender": self.gender,
            "address": self.address,
            "mobile": self.mobile,
            "email": self.email,
            "symptoms": self.symptoms,
            "assigned_doctor": self.assignedDoctorId and Doctor.objects.get(user_id=self.assignedDoctorId).get_name
        }

    def update_status(self):
        self.status = not self.status
        self.save()

    def book_appointment(self, doctor, date, description):
        appointment = Appointment.objects.create(
            patientId=self.user.id,
            doctorId=doctor.user.id,
            patientName=self.get_name,
            doctorName=doctor.get_name,
            appointmentDate=date,
            description=description,
            status="Pending"
        )
        return appointment

    def view_medical_history(self):
        return MedicalRecord.objects.filter(patient=self)

    def __str__(self):
        return self.user.first_name + " (" + self.symptoms + ")"

# New Model: Nurse
# Concept: Inheritance - Nurse inherits from HospitalEntity
class Nurse(HospitalEntity):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_pic = models.ImageField(upload_to='profile_pic/NurseProfilePic/', null=True, blank=True)
    mobile = models.CharField(max_length=20, null=False)
    assignedWard = models.CharField(max_length=100, null=True)
    status = models.BooleanField(default=True)

    @property
    def get_name(self):
        return self.user.first_name + " " + self.user.last_name

    @property
    def get_id(self):
        return self.user.id

    # Concept: Method Overriding - Implementing abstract method
    def get_info(self):
        return {"id": self.get_id, "name": self.get_name, "assigned_ward": self.assignedWard}

    def update_status(self):
        self.status = not self.status
        self.save()

    def __str__(self):
        return "{} (Nurse)".format(self.user.first_name)

# Appointments
class Appointment(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed'),
    )

    patientId = models.PositiveIntegerField(null=True)
    doctorId = models.PositiveIntegerField(null=True)
    patientName = models.CharField(max_length=40, null=True)
    doctorName = models.CharField(max_length=40, null=True)
    appointmentDate = models.DateTimeField(null=True, blank=True)
    description = models.TextField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def schedule_appointment(self):
        if self.status == "Pending":
            self.status = "Approved"
            self.save()

    def cancel_appointment(self):
        if self.status not in ['Cancelled', 'Completed']:
            self.status = "Cancelled"
            self.save()

    def reschedule_appointment(self, new_date):
        if self.status not in ['Cancelled', 'Completed']:
            self.appointmentDate = new_date
            self.status = "Pending"
            self.save()

    def __str__(self):
        return f"Appointment: {self.patientName} with {self.doctorName} on {self.appointmentDate}"

# Proxy Design Pattern for Appointment
class AppointmentProxy:
    def __init__(self, appointment, user_type="patient"):
        """
        Initialize the proxy with an Appointment instance and user type.
        user_type can be 'patient', 'doctor', or 'admin'.
        """
        self._appointment = appointment
        self._user_type = user_type

    def get_details(self):
        """Allow all users to view appointment details."""
        return {
            "patientName": self._appointment.patientName,
            "doctorName": self._appointment.doctorName,
            "appointmentDate": self._appointment.appointmentDate,
            "status": self._appointment.status,
            "description": self._appointment.description
        }

    def schedule_appointment(self):
        """Only doctors or admins can approve an appointment."""
        if self._user_type in ["doctor", "admin"]:
            self._appointment.schedule_appointment()
        else:
            raise PermissionError("Only doctors or admins can approve appointments.")

    def cancel_appointment(self):
        """Patients, doctors, or admins can cancel an appointment."""
        self._appointment.cancel_appointment()

    def reschedule_appointment(self, new_date):
        """Only doctors or admins can reschedule an appointment."""
        if self._user_type in ["doctor", "admin"]:
            self._appointment.reschedule_appointment(new_date)
        else:
            raise PermissionError("Only doctors or admins can reschedule appointments.")

# Patient Discharge and Billing
class PatientDischargeDetails(models.Model):
    patientId = models.PositiveIntegerField(null=True)
    patientName = models.CharField(max_length=40)
    assignedDoctorName = models.CharField(max_length=40)
    address = models.CharField(max_length=40)
    mobile = models.CharField(max_length=20, null=True)
    symptoms = models.CharField(max_length=100, null=True)
    admitDate = models.DateField(null=False)
    releaseDate = models.DateField(null=False)
    daySpent = models.PositiveIntegerField(null=False)
    roomCharge = models.PositiveIntegerField(null=False)
    medicineCost = models.PositiveIntegerField(null=False)
    doctorFee = models.PositiveIntegerField(null=False)
    OtherCharge = models.PositiveIntegerField(null=False)
    total = models.PositiveIntegerField(null=False)

# Departments
class Department(models.Model):
    department_id = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50, choices=departments, unique=True)
    head_of_department = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, related_name='head_of')
    doctors_list = models.ManyToManyField(Doctor, related_name='departments')
    services_offered = models.TextField(max_length=500, blank=True)

    def get_department_info(self):
        return {"id": self.department_id, "name": self.name}

    def list_doctors(self):
        return self.doctors_list.filter(status=True)

    def list_services(self):
        return self.services_offered.split(",") if self.services_offered else []

    def __str__(self):
        return self.name

# Concept: Singleton Design Pattern - Ensure only one BillingManager instance exists
class BillingManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BillingManager, cls).__new__(cls)
        return cls._instance

    def create_bill(self, patient, medical_record, treatment_cost, medicine_cost):
        bill = Billing.objects.create(
            bill_id=f"BILL{timezone.now().strftime('%Y%m%d%H%M%S')}",
            patient=patient,
            medical_record=medical_record,
            treatment_cost=treatment_cost,
            medicine_cost=medicine_cost,
            total_amount=treatment_cost + medicine_cost
        )
        return bill

class Billing(models.Model):
    PAYMENT_STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Paid', 'Paid'),
        ('Partial', 'Partial'),
    )

    bill_id = models.CharField(max_length=10, unique=True)
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE)
    medical_record = models.ForeignKey('MedicalRecord', on_delete=models.CASCADE, null=True)
    treatment_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    medicine_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def generate_bill(self, treatment_cost=0, medicine_cost=0):
        self.treatment_cost += treatment_cost
        self.medicine_cost += medicine_cost
        self.total_amount = self.treatment_cost + self.medicine_cost
        self.save()

    def process_payment(self, amount):
        if amount >= self.total_amount:
            self.payment_status = 'Paid'
        elif amount > 0:
            self.payment_status = 'Partial'
        self.save()
        return self.payment_status == 'Paid'

    def view_bill_details(self):
        return {
            "bill_id": self.bill_id,
            "patient": self.patient.get_name,
            "treatment_cost": self.treatment_cost,
            "medicine_cost": self.medicine_cost,
            "total": self.total_amount,
            "status": self.payment_status,
            "created_at": self.created_at
        }

    def __str__(self):
        return f"Bill {self.bill_id} for {self.patient.get_name}"

# Pharmacy
class Pharmacy(models.Model):
    pharmacy_id = models.CharField(max_length=10, unique=True)
    pharmacist = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    available_medicines = models.JSONField(default=dict, blank=True, null=True)
    prescriptions_list = models.ManyToManyField('MedicalRecord', blank=True)

    # Concept: Exception Handling - Handle errors during medication dispensing
    def dispense_medication(self, prescription):
        try:
            if prescription.prescribed_treatment and prescription.prescribed_treatment.startswith('['):
                medicines = json.loads(prescription.prescribed_treatment)
                if not isinstance(medicines, list):
                    raise ValidationError("Invalid prescribed_treatment format: must be a list")
                medicines = [med.strip() for med in medicines if isinstance(med, str)]
            else:
                medicines = [med.strip() for med in prescription.prescribed_treatment.split(",")] if prescription.prescribed_treatment else []

            quantities_dict = {}
            if prescription.treatment_quantities:
                for item in prescription.treatment_quantities.split(","):
                    if not item.strip():
                        continue
                    parts = [x.strip() for x in item.split(":")]
                    if len(parts) != 2 or not parts[1].isdigit():
                        raise ValidationError(f"Invalid format for treatment quantity: {item}")
                    med, qty = parts
                    quantities_dict[med.lower()] = int(qty)
            quantities = [quantities_dict.get(med.lower(), 0) for med in medicines]

            if not medicines or not quantities:
                raise ValidationError("No medicines or quantities provided")
            if len(medicines) != len(quantities):
                raise ValidationError("Mismatch between number of medicines and quantities")

        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            return False, {"error": str(e)}

        available_meds = {k.lower(): v for k, v in (self.available_medicines or {}).items()}
        dispensed_items = []

        for med, qty in zip(medicines, quantities):
            med_lower = med.lower()
            if med_lower not in available_meds:
                return False, {"error": f"Medicine {med} not found in pharmacy stock"}
            stock_quantity = available_meds[med_lower].get('quantity', 0)
            if stock_quantity < qty:
                return False, {"error": f"Insufficient stock for {med}: required {qty}, available {stock_quantity}"}

            original_key = next((k for k in self.available_medicines.keys() if k.lower() == med_lower), None)
            if not original_key:
                return False, {"error": f"Could not find original key for {med}"}
            price = self.available_medicines[original_key]['price']
            self.available_medicines[original_key]['quantity'] -= qty
            if self.available_medicines[original_key]['quantity'] <= 0:
                del self.available_medicines[original_key]
            dispensed_items.append({
                "name": med,
                "quantity": qty,
                "price": price
            })

        self.save()
        return True, dispensed_items

    def check_stock(self, medicine):
        return self.available_medicines.get(medicine, {"quantity": 0}).get("quantity", 0)

    def update_medicine_list(self, medicine, quantity, price):
        if quantity < 0:
            return False
        if not self.available_medicines:
            self.available_medicines = {}
        self.available_medicines[medicine] = {"quantity": quantity, "price": float(price)}
        self.save()
        return True

    def __str__(self):
        return f"Pharmacy {self.pharmacy_id}"

#Medical Records
class MedicalRecord(models.Model):
    record_id = models.CharField(max_length=15, unique=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_history')
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL, null=True, blank=True)
    diagnosis = models.TextField(max_length=500)
    prescribed_treatment = models.CharField(max_length=200)
    treatment_quantities = models.CharField(max_length=200)
    test_results = models.JSONField(default=list)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, default='pending')
    dispensed_items = models.JSONField(null=True, blank=True)

    # Overloaded update_record methods using multipledispatch
    @dispatch(str)
    def update_record(self, diagnosis):
        """Update record with a single diagnosis string."""
        self.diagnosis = diagnosis
        self.save()

    @dispatch(list)
    def update_record(self, treatment):
        """Update record with a list of prescribed treatments."""
        self.prescribed_treatment = ", ".join(treatment)
        self.save()

    @dispatch(dict)
    def update_record(self, data):
        """Update record with a dictionary containing multiple fields."""
        if 'diagnosis' in data:
            self.diagnosis = data['diagnosis']
        if 'treatment' in data:
            self.prescribed_treatment = ", ".join(data['treatment']) if isinstance(data['treatment'], list) else data['treatment']
        if 'treatment_quantities' in data:
            self.treatment_quantities = data['treatment_quantities']
        if 'test_results' in data:
            self.test_results = data['test_results']
        self.save()

    @dispatch(object, object, object, object)
    def update_record(self, diagnosis=None, treatment=None, treatment_quantities=None, test_results=None):
        """Original method to update with optional individual parameters."""
        if diagnosis:
            self.diagnosis = diagnosis
        if treatment:
            self.prescribed_treatment = treatment
        if treatment_quantities:
            self.treatment_quantities = treatment_quantities
        if test_results:
            self.test_results = test_results
        self.save()

    def view_record(self):
        return {
            "record_id": self.record_id,
            "patient": self.patient.get_name,
            "doctor": self.doctor.get_name if self.doctor else "N/A",
            "diagnosis": self.diagnosis,
            "treatment": self.prescribed_treatment,
            "tests": self.test_results,
            "created_at": self.created_at
        }

    def __str__(self):
        return f"Record {self.record_id} for {self.patient.get_name}"

# Room
class WardRoom(models.Model):
    ROOM_TYPE_CHOICES = (
        ('ICU', 'ICU'),
        ('General', 'General'),
        ('Private', 'Private'),
    )

    room_id = models.CharField(max_length=10, unique=True)
    type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES)
    availability = models.BooleanField(default=True)
    assigned_patient = models.OneToOneField('Patient', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_room')
    ward = models.CharField(max_length=100, blank=True)

    def assign_room(self, patient):
        if self.availability:
            self.assigned_patient = patient
            self.availability = False
            self.save()
            return True
        return False

    def discharge_patient(self):
        if self.assigned_patient:
            self.assigned_patient = None
            self.availability = True
            self.save()
        else:
            raise ValueError(f"Room {self.room_id} has no assigned patient to discharge.")

    def check_availability(self):
        return self.availability

    def __str__(self):
        return f"Room {self.room_id} ({self.type}) - {'Available' if self.availability else 'Occupied'}"