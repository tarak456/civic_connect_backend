from django.core.management.base import BaseCommand
from accounts.models import User
from issues.models import Department, Issue, Notification


class Command(BaseCommand):
    help = "Seeds initial municipal departments, test user accounts across all 3 roles, and demo civic issues."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Civic Connect database..."))

        # 1. Departments
        departments = [
            "Roads Department",
            "Sanitation Department",
            "Electrical & Lighting Department",
            "Drainage & Sewerage Department",
            "Water Works Department",
            "Public Works Department",
        ]
        dept_objs = {}
        for name in departments:
            d, created = Department.objects.get_or_create(name=name)
            dept_objs[name] = d
            if created:
                self.stdout.write(f"Created Department: {name}")

        # 2. Demo Users (Citizen, Government Admin, Maintainer)
        # Citizen
        citizen, c_created = User.objects.get_or_create(
            username="citizen",
            defaults={
                "email": "citizen@civicconnect.org",
                "role": User.Role.CITIZEN,
                "is_verified": True,
            },
        )
        citizen.set_password("password123")
        citizen.role = User.Role.CITIZEN
        citizen.is_verified = True
        citizen.save()
        if c_created:
            self.stdout.write("Created Citizen: citizen / password123")

        # Government Admin
        admin, a_created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@civicconnect.org",
                "role": User.Role.GOVERNMENT,
                "employee_id": "EMP-GOV-001",
                "is_verified": True,
                "is_staff": True,
            },
        )
        admin.set_password("password123")
        admin.role = User.Role.GOVERNMENT
        admin.is_verified = True
        admin.employee_id = "EMP-GOV-001"
        admin.save()
        if a_created:
            self.stdout.write("Created Government Admin: admin / password123")

        # Field Maintainer
        maintainer, m_created = User.objects.get_or_create(
            username="maintainer",
            defaults={
                "email": "maintainer@civicconnect.org",
                "role": User.Role.MAINTAINER,
                "employee_id": "EMP-MNT-101",
                "is_verified": True,
            },
        )
        maintainer.set_password("password123")
        maintainer.role = User.Role.MAINTAINER
        maintainer.is_verified = True
        maintainer.employee_id = "EMP-MNT-101"
        maintainer.save()
        if m_created:
            self.stdout.write("Created Maintainer: maintainer / password123")

        # 3. Seed Sample Issues if few exist
        if Issue.objects.count() < 4:
            issues_data = [
                {
                    "title": "Severe Pothole on Main Avenue",
                    "description": "Deep asphalt depression causing vehicular swerving near 5th cross junction.",
                    "category": Issue.Category.POTHOLE,
                    "severity": Issue.Severity.HIGH,
                    "status": Issue.Status.IN_PROGRESS,
                    "department": dept_objs["Roads Department"],
                    "assigned_maintainer": maintainer,
                    "latitude": 12.9716,
                    "longitude": 77.5946,
                    "address_text": "5th Cross, Main Avenue, Sector 4",
                    "ai_confidence": 0.94,
                    "ai_detected_category": "POTHOLE",
                },
                {
                    "title": "Overflowing Public Dumpster",
                    "description": "Garbage spilling onto sidewalk, stray dogs gathering and foul odor.",
                    "category": Issue.Category.GARBAGE,
                    "severity": Issue.Severity.MEDIUM,
                    "status": Issue.Status.REPORTED,
                    "department": dept_objs["Sanitation Department"],
                    "assigned_maintainer": None,
                    "latitude": 12.9725,
                    "longitude": 77.5955,
                    "address_text": "Near Central Market Gate 2",
                    "ai_confidence": 0.91,
                    "ai_detected_category": "GARBAGE",
                },
                {
                    "title": "Flickering Streetlight Cluster",
                    "description": "Three consecutive streetlights are out, making the corner unsafe at night.",
                    "category": Issue.Category.STREETLIGHT,
                    "severity": Issue.Severity.HIGH,
                    "status": Issue.Status.ASSIGNED,
                    "department": dept_objs["Electrical & Lighting Department"],
                    "assigned_maintainer": maintainer,
                    "latitude": 12.9740,
                    "longitude": 77.5930,
                    "address_text": "Oak Street, 7th Block",
                    "ai_confidence": 0.95,
                    "ai_detected_category": "STREETLIGHT",
                },
                {
                    "title": "Clogged Stormwater Drain",
                    "description": "Monsoon drain is choked with plastic and silt causing minor street waterlogging.",
                    "category": Issue.Category.DRAINAGE,
                    "severity": Issue.Severity.MEDIUM,
                    "status": Issue.Status.RESOLVED,
                    "department": dept_objs["Drainage & Sewerage Department"],
                    "assigned_maintainer": maintainer,
                    "latitude": 12.9705,
                    "longitude": 77.5910,
                    "address_text": "Park Road, Opposite City Library",
                    "ai_confidence": 0.89,
                    "ai_detected_category": "DRAINAGE",
                    "resolution_notes": "De-silted culvert and cleared plastic blockage. Water flow restored.",
                },
                {
                    "title": "High-Pressure Pipeline Leakage",
                    "description": "Clean water pipe leaking continuously onto roadway for two days.",
                    "category": Issue.Category.WATER_LEAKAGE,
                    "severity": Issue.Severity.HIGH,
                    "status": Issue.Status.CLOSED,
                    "department": dept_objs["Water Works Department"],
                    "assigned_maintainer": maintainer,
                    "latitude": 12.9732,
                    "longitude": 77.5980,
                    "address_text": "Ring Road Service Lane, Ward 12",
                    "ai_confidence": 0.92,
                    "ai_detected_category": "WATER_LEAKAGE",
                    "resolution_notes": "Replaced cracked gasket on municipal pipeline feed.",
                    "feedback_rating": 5,
                    "feedback_comment": "Very quick response from the municipal team, great work!",
                },
            ]

            for item in issues_data:
                iss = Issue.objects.create(citizen=citizen, **item)
                # Create corresponding notification
                Notification.objects.create(
                    recipient=citizen,
                    issue=iss,
                    title=f"Update: {iss.title}",
                    message=f"Status is now {iss.get_status_display()} under {iss.department.name if iss.department else 'review'}.",
                    notification_type=Notification.NotificationType.STATUS_UPDATE,
                )
            self.stdout.write("Created 5 sample civic issues with realistic workflows.")

        self.stdout.write(self.style.SUCCESS("Database seeding completed successfully!"))
