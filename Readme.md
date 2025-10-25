# Hospital Management System API

## Authentication
All endpoints require authentication. Include this header in all requests:
```
Authorization: Token <your-token-here>
Content-Type: application/json
```

## Base URL: `http://localhost:8000/api/`

## 👤 User Profile

### `GET /my-info`
**What it does:** Get your profile information  
**Who can use:** Everyone  
**How to use:** Just send GET request  

### `GET /patients`
**What it does:** Get list of patients in your department  
**Who can use:** Doctors, nurses  
**How to use:** Send GET request, optionally add `?department=cardiology`  

### `GET /doctors`
**What it does:** Get list of all doctors  
**Who can use:** Everyone  
**How to use:** Just send GET request

## 📅 Appointments

### `POST /patient-book-appointment`
**What it does:** Book an appointment with a doctor  
**Who can use:** Patients only  
**How to use:** Send POST with `{"doctor_id": 2, "appointment_date": "2024-01-15T10:00:00Z", "reason": "checkup"}`  

### `GET /patient-appointments`
**What it does:** Get your appointments  
**Who can use:** Patients only  
**How to use:** Send GET request, add `?status=pending` to filter  

### `GET /doctor-appointments`
**What it does:** Get appointments for you as a doctor  
**Who can use:** Doctors only  
**How to use:** Send GET request, add `?from=01-01-2024&to=31-01-2024` to filter dates  

### `GET /doctor-appointments-today`
**What it does:** Get today's appointments  
**Who can use:** Doctors only  
**How to use:** Just send GET request  

### `GET /doctor-appointments-not-today`
**What it does:** Get all appointments except today's  
**Who can use:** Doctors only  
**How to use:** Just send GET request  

### `PATCH /doctor-confirm-appointment/<appointment_id>`
**What it does:** Confirm a pending appointment  
**Who can use:** Doctors only  
**How to use:** Send PATCH to `/doctor-confirm-appointment/123`  

### `PATCH /doctor-cancel-appointment/<appointment_id>`
**What it does:** Cancel an appointment  
**Who can use:** Doctors only  
**How to use:** Send PATCH to `/doctor-cancel-appointment/123`  

### `GET /nurse-department-appointments`
**What it does:** Get appointments in your department  
**Who can use:** Nurses only  
**How to use:** Just send GET request

## 📋 Medical Records

### `GET /get-patient-emr`
**What it does:** Get your medical record  
**Who can use:** Patients (own record only)  
**How to use:** Just send GET request  

### `GET /doc-get-patient-emr/<patient_id>`
**What it does:** Get a patient's medical record  
**Who can use:** Doctors, medical staff  
**How to use:** Send GET to `/doc-get-patient-emr/123`  

### `POST /doc-create-patient-emr`
**What it does:** Create medical record for a patient  
**Who can use:** Doctors only  
**How to use:** Send POST with patient details like `{"patient_id": 1, "blood_group": "O+", "height": 165}`  

### `PATCH /patient-emr-update/<patient_id>`
**What it does:** Update patient's medical record  
**Who can use:** Doctors only  
**How to use:** Send PATCH to `/patient-emr-update/123` with updated data  

## 🩺 Patient Vitals

### `POST /create-patient-vital`
**What it does:** Record vital signs for a patient  
**Who can use:** Doctors, nurses (not patients)  
**How to use:** Send POST with `{"patient_id": 1, "blood_pressure_systolic": 120, "heart_rate": 72}`  

### `PATCH /update-patient-vital/<vital_id>`
**What it does:** Update existing vital signs  
**Who can use:** Original recorder or admin  
**How to use:** Send PATCH to `/update-patient-vital/123` with new data  

## 🧪 Lab Tests

### `POST /doctor-test-request`
**What it does:** Request lab test for patient  
**Who can use:** Doctors only  
**How to use:** Send POST with `{"patient_id": 1, "test_name": "Blood Test", "test_code": "BT001"}`  

### `PATCH /update-test/<test_id>`
**What it does:** Update test results  
**Who can use:** Lab technicians only  
**How to use:** Send PATCH to `/update-test/123` with results  

### `GET /get-all-test-result`
**What it does:** Get all test results  
**Who can use:** Everyone  
**How to use:** Just send GET request  

### `GET /get-specific-test-result/<test_id>`
**What it does:** Get specific test result  
**Who can use:** Everyone  
**How to use:** Send GET to `/get-specific-test-result/123`  

## 💊 Drug Inventory

### `GET /get-all-drugs`
**What it does:** Get list of all drugs in inventory  
**Who can use:** Everyone  
**How to use:** Just send GET request  

### `GET /get-specific-drug/<drug_id>`
**What it does:** Get details of specific drug  
**Who can use:** Everyone  
**How to use:** Send GET to `/get-specific-drug/123`  

### `PATCH /update-a-specific-drug/<drug_id>`
**What it does:** Update drug information  
**Who can use:** Pharmacists and admins  
**How to use:** Send PATCH to `/update-a-specific-drug/123` with new data

## 💉 Prescriptions

### `POST /create-prescription`
**What it does:** Create prescription for patient  
**Who can use:** Doctors only  
**How to use:** Send POST with `{"patient_id": 1, "medications": [1,2,3], "instructions": "Take twice daily"}`  

### `GET /get-all-prescriptions`
**What it does:** Get prescriptions (filtered by your role)  
**Who can use:** Everyone  
**How to use:** Send GET request, add `?dispensed=true` or `?patient_id=123` to filter  

### `GET /get-patient-prescription/<patient_email>`
**What it does:** Get prescriptions for specific patient  
**Who can use:** Patients (own), medical staff (any patient)  
**How to use:** Send GET to `/get-patient-prescription/patient@email.com`  

### `PATCH /update-prescription/<prescription_id>`
**What it does:** Update prescription details  
**Who can use:** Doctors (own), pharmacists, admins  
**How to use:** Send PATCH to `/update-prescription/123` with new data  

### `POST /pharmacist-dispense-prescription/<prescription_id>`
**What it does:** Mark prescription as dispensed  
**Who can use:** Pharmacists only  
**How to use:** Send POST to `/pharmacist-dispense-prescription/123`  

### `POST /patient-collected-prescription/<prescription_id>`
**What it does:** Confirm you collected prescription  
**Who can use:** Patients only  
**How to use:** Send POST to `/patient-collected-prescription/123`

## 🏥 Wards & Rooms

### `GET /ward-room-bed-overview`
**What it does:** Get overview of all wards, rooms and beds  
**Who can use:** Everyone  
**How to use:** Just send GET request  

### `POST /create-ward`
**What it does:** Create a new ward  
**Who can use:** Admins only  
**How to use:** Send POST with `{"name": "ICU", "description": "Intensive Care"}`  

### `PUT /update-ward/<ward_id>`
**What it does:** Update ward information  
**Who can use:** Admins only  
**How to use:** Send PUT to `/update-ward/123` with new data  

### `DELETE /delete-ward/<ward_id>`
**What it does:** Delete a ward  
**Who can use:** Admins only  
**How to use:** Send DELETE to `/delete-ward/123`  

### `POST /create-room`
**What it does:** Create room in a ward  
**Who can use:** Admins only  
**How to use:** Send POST with `{"ward_id": 1, "number": "R001", "bed_count": 4}`  

### `PUT /update-room/<room_id>`
**What it does:** Update room information  
**Who can use:** Admins only  
**How to use:** Send PUT to `/update-room/123` with new data  

### `DELETE /delete-room/<room_id>`
**What it does:** Delete a room  
**Who can use:** Admins only  
**How to use:** Send DELETE to `/delete-room/123`  

## 🛏️ Bed Allocation

### `POST /allocate-bed`
**What it does:** Assign bed to patient  
**Who can use:** Doctors, nurses  
**How to use:** Send POST with `{"room_id": 1, "bed_number": "B1", "allocated_to_id": 123}`  

## 🤖 AI Assistant

### `POST /ai`
**What it does:** Chat with AI medical assistant  
**Who can use:** Doctors only  
**How to use:** Send POST with `{"message": "What are symptoms of fever?"}`

## 🔧 Admin Endpoints
*All admin endpoints require superuser access*

### User Management
- `GET/POST /admin/users/` - List all users or create new user
- `GET/PUT/DELETE /admin/users/<user_id>/` - Get, update, or deactivate user

### Department Management  
- `GET/POST /admin/departments/` - List or create departments
- `GET/PUT/DELETE /admin/departments/<dept_id>/` - Manage specific department

### Analytics
- `GET /admin/analytics/overview/` - Get system statistics
- `GET /admin/analytics/patients/` - Get patient analytics  
- `GET /admin/analytics/appointments/` - Get appointment analytics

### Drug Management
- `GET/POST /admin/drugs/` - List or create drugs
- `GET/PUT/DELETE /admin/drugs/<drug_id>/` - Manage specific drug
- `GET /admin/drugs/low-stock/` - Get low stock drugs

### System Overview
- `GET /admin/prescriptions/` - All prescriptions with filters
- `GET /admin/test-results/` - All test results  
- `GET /admin/appointments/` - All appointments with filters
- `GET /admin/wards/` - All wards with details
- `GET /admin/rooms/` - All rooms with details
- `GET /admin/beds/` - All beds with filters
- `GET /admin/roles/` - All user roles

## 📝 Quick Notes
- All endpoints need `Authorization: Token <your-token>` header
- Use `Content-Type: application/json` for POST/PUT requests
- Add `?` followed by parameters for filtering (e.g., `?status=pending`)
- Replace `<id>` in URLs with actual numbers (e.g., `/users/123/`)
- Dates should be in format: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SSZ`

## 🔐 Common Error Codes
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (need authentication)  
- `403` - Forbidden (no permission)
- `404` - Not Found (doesn't exist)
- `500` - Server Error