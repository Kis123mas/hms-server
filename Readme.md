# Hospital Management System (HMS)

A comprehensive Hospital Management System built with Django and Django REST Framework, designed to streamline hospital operations including patient management, appointments, medical records, pharmacy operations, and financial accounting.

## 🏥 Features

### Core Medical Management
- **Patient Management**: Complete patient profiles with medical history
- **Appointments**: Doctor-patient appointment scheduling and management
- **Medical Records**: Comprehensive electronic health records (EHR)
- **Vital Signs**: Tracking and monitoring patient vitals
- **Treatments**: Medical treatment plans and procedures
- **Surgery Management**: Surgical procedure scheduling and tracking

### Hospital Operations
- **Department Management**: Organize hospital departments and specialties
- **Admission Management**: Patient admission, bed allocation, and discharge
- **Ward & Room Management**: Hospital infrastructure management
- **Bed Management**: Real-time bed occupancy tracking

### Pharmacy & Laboratory
- **Pharmacy Operations**: Drug inventory, prescriptions, and dispensing
- **Laboratory Services**: Test requests, results, and reporting
- **Referral System**: Inter-departmental referrals for pharmacy and lab services

### Financial Management
- **Accounting Module**: Income and expense tracking
- **Payment Processing**: Multiple payment methods and transaction management
- **Billing System**: Automated billing for services and treatments

### Communication & Real-time Features
- **WebSocket Integration**: Real-time notifications and updates
- **Notifications**: System-wide notification management
- **Doctor Visits**: Track doctor-patient interactions

## 🛠️ Technology Stack

### Backend
- **Framework**: Django 5.2.3
- **API**: Django REST Framework 3.16.0
- **Real-time**: Django Channels 4.1.0 with WebSocket support
- **Authentication**: Django REST Knox 5.0.2
- **Database**: SQLite (development), PostgreSQL (production recommended)
- **CORS**: django-cors-headers 4.7.0

### Frontend Integration
- **WebSocket Client**: Real-time communication support
- **API Endpoints**: RESTful API design

## 📁 Project Structure

```
hms-server/
├── healthManagement/          # Main application module
│   ├── models.py             # Database models (Patient, Appointment, etc.)
│   ├── views.py              # API views and business logic
│   ├── serializers.py        # Data serialization
│   ├── consumers.py          # WebSocket consumers
│   ├── urls.py               # URL routing
│   └── migrations/           # Database migrations
├── accounts/                  # User authentication and profiles
├── accountant/               # Financial management module
├── hmsServer/                # Django project settings
│   ├── settings.py           # Project configuration
│   ├── urls.py               # Main URL routing
│   ├── asgi.py               # ASGI application for WebSockets
│   └── wsgi.py               # WSGI application
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
└── db.sqlite3               # SQLite database (development)
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd hms-server
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Unix/MacOS
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   - Copy `hmsServer/settings.py` and update:
     - `SECRET_KEY`: Generate a new secure key
     - `DATABASES`: Configure your database settings
     - Email settings for notifications

5. **Run database migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

8. **Start WebSocket server** (for real-time features)
   ```bash
   daphne hmsServer.asgi:application -p 8000
   ```

## 📊 Database Models

### Core Entities
- **Profile**: User profiles with roles (Doctor, Nurse, Patient, Admin)
- **Patient**: Patient information and medical history
- **Appointment**: Appointment scheduling and management
- **MedicalRecord**: Comprehensive patient medical records
- **VitalSign**: Patient vital signs monitoring
- **Treatment**: Medical treatments and procedures
- **Department**: Hospital departments and specialties

### Hospital Infrastructure
- **Ward**: Hospital wards organization
- **Room**: Rooms within wards
- **Bed**: Individual bed management
- **Admission**: Patient admission records
- **SurgeryPlacement**: Surgical scheduling

### Pharmacy & Laboratory
- **Drug**: Medication inventory
- **PharmacyReferral**: Pharmacy referral system
- **TestRequest**: Laboratory test requests
- **TestResult**: Test results and reports

### Financial
- **AdmissionCharges**: Admission billing
- **DrugSale**: Pharmacy sales transactions
- **ExpenseTransaction**: Expense tracking
- **IncomeTransaction**: Revenue tracking

## 🔌 API Endpoints

The system provides RESTful API endpoints for all major operations:

### Authentication
- `/api/auth/login/` - User login
- `/api/auth/logout/` - User logout
- `/api/auth/register/` - User registration

### Patient Management
- `/api/patients/` - Patient CRUD operations
- `/api/appointments/` - Appointment management
- `/api/medical-records/` - Medical record access

### Hospital Operations
- `/api/admissions/` - Patient admissions
- `/api/departments/` - Department management
- `/api/beds/` - Bed management

### Pharmacy & Lab
- `/api/pharmacy/` - Pharmacy operations
- `/api/laboratory/` - Laboratory services

### Financial
- `/api/accounting/` - Financial operations

## 🔄 WebSocket Events

Real-time features are implemented using Django Channels:

### Connection Endpoints
- `ws/notifications/` - Real-time notifications
- `ws/appointments/` - Appointment updates
- `ws/admissions/` - Admission status changes

### Events
- New appointment notifications
- Admission status updates
- Laboratory result notifications
- Pharmacy refill alerts

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the project root:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Database Configuration
For production, configure PostgreSQL in `hmsServer/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'hms_db',
        'USER': 'hms_user',
        'PASSWORD': 'your-password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test healthManagement
python manage.py test accounts
python manage.py test accountant
```

## 📝 Development Guidelines

### Code Style
- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Maintain proper indentation and spacing

### API Design
- Use RESTful principles
- Implement proper HTTP status codes
- Validate input data using serializers
- Handle errors gracefully

### Database
- Use Django migrations for schema changes
- Add indexes for frequently queried fields
- Optimize queries to prevent N+1 problems

## 🚀 Deployment

### Production Setup
1. Set `DEBUG=False` in settings
2. Configure production database
3. Set up static files serving
4. Configure domain and SSL
5. Set up environment variables
6. Run migrations and collect static files

### Docker Deployment
```dockerfile
# Dockerfile example
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["daphne", "hmsServer.asgi:application", "-p", "8000"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation

## 🔄 Version History

- **v1.0.0** - Initial release with core HMS functionality
- **v1.1.0** - Added WebSocket real-time features
- **v1.2.0** - Enhanced pharmacy and laboratory modules
- **v1.3.0** - Improved accounting and billing system

## 📈 Future Enhancements

- Mobile application support
- Advanced analytics and reporting
- Integration with medical devices
- Telemedicine capabilities
- AI-powered diagnostics assistance
- Multi-hospital support
- Enhanced security features

---

**Built with ❤️ for healthcare professionals**
