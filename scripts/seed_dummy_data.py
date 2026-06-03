import sys
import os
from datetime import datetime
import logging

# Fix Unicode encoding on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging to see WhatsApp messages
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("urllib3").setLevel(logging.WARNING)

from app.db.database import SessionLocal
from app.db.models import User, Vehicle, VehicleStatus, Problem, Solution
from app.services.alert_service import detect_alerts



def normalize_phone_number(phone: str) -> str:
    phone = (phone or "").strip()
    if not phone.startswith("+"):
        phone = "+" + phone.lstrip("+")
    return phone


def get_or_create_user(db, phone: str, name: str = None, role: str = "manager") -> User:
    phone = normalize_phone_number(phone)
    user = db.query(User).filter(User.phone_number == phone).first()
    if user:
        user.name = name or user.name
        user.role = role or user.role
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    user = User(name=name, phone_number=phone, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_vehicle(db, vehicle_number: str, manager_id: int, driver_id: int) -> Vehicle:
    vehicle = db.query(Vehicle).filter(Vehicle.vehicle_number == vehicle_number).first()
    if vehicle:
        vehicle.manager_id = manager_id
        vehicle.driver_id = driver_id
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)
        return vehicle

    vehicle = Vehicle(
        vehicle_number=vehicle_number,
        manager_id=manager_id,
        driver_id=driver_id,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def create_or_update_vehicle_status(
    db,
    vehicle_id: int,
    ign_state: str,
    mode: str,
    location: str,
    last_gps_time: datetime,
):
    status = db.query(VehicleStatus).filter(VehicleStatus.vehicle_id == vehicle_id).first()
    if status:
        status.ign_state = ign_state
        status.mode = mode
        status.location = location
        status.last_gps_time = last_gps_time
        db.add(status)
    else:
        status = VehicleStatus(
            vehicle_id=vehicle_id,
            ign_state=ign_state,
            mode=mode,
            location=location,
            last_gps_time=last_gps_time,
        )
        db.add(status)
    db.commit()
    db.refresh(status)
    return status


def create_problems_and_solutions(db):
    """Create common vehicle problems and their solutions."""
    
    # Problem 1: GPS Device Not Working
    problem1 = db.query(Problem).filter(Problem.title == "GPS Device Not Working").first()
    if not problem1:
        problem1 = Problem(
            title="GPS Device Not Working",
            description="Vehicle GPS tracking device is showing as not working or offline",
            severity="High",
            machine_model="GPS-Tracker-V1"
        )
        db.add(problem1)
        db.commit()
        db.refresh(problem1)
        
        # Add solutions for problem 1
        solutions_p1 = [
            Solution(problem_id=problem1.id, step_number=1, description="Check vehicle power supply - Ignition should be ON"),
            Solution(problem_id=problem1.id, step_number=2, description="Check Power LED - should be RED or GREEN"),
            Solution(problem_id=problem1.id, step_number=3, description="Check GSM LED - should be blinking or GREEN"),
            Solution(problem_id=problem1.id, step_number=4, description="Check GPS LED - should be acquiring signal"),
            Solution(problem_id=problem1.id, step_number=5, description="If GPS LED is OFF, move vehicle to open area for better sky visibility"),
            Solution(problem_id=problem1.id, step_number=6, description="Verify GPS antenna is properly connected"),
            Solution(problem_id=problem1.id, step_number=7, description="If still not working, restart device by turning ignition OFF/ON"),
        ]
        db.add_all(solutions_p1)
        db.commit()
    
    # Problem 2: No Network Connectivity
    problem2 = db.query(Problem).filter(Problem.title == "No Network Connectivity").first()
    if not problem2:
        problem2 = Problem(
            title="No Network Connectivity",
            description="Device cannot connect to network or SIM card issue",
            severity="High",
            machine_model="GPS-Tracker-V1"
        )
        db.add(problem2)
        db.commit()
        db.refresh(problem2)
        
        solutions_p2 = [
            Solution(problem_id=problem2.id, step_number=1, description="Check GSM LED on device - must be RED or GREEN"),
            Solution(problem_id=problem2.id, step_number=2, description="Verify SIM card is properly inserted and activated"),
            Solution(problem_id=problem2.id, step_number=3, description="Check mobile data balance in SIM card account"),
            Solution(problem_id=problem2.id, step_number=4, description="Ensure network coverage is available at current location"),
            Solution(problem_id=problem2.id, step_number=5, description="Restart device by turning ignition OFF for 10 seconds"),
            Solution(problem_id=problem2.id, step_number=6, description="Remove and reinsert SIM card carefully"),
            Solution(problem_id=problem2.id, step_number=7, description="Contact network provider to check account status"),
        ]
        db.add_all(solutions_p2)
        db.commit()
    
    # Problem 3: Power Supply Issue
    problem3 = db.query(Problem).filter(Problem.title == "Power Supply Issue").first()
    if not problem3:
        problem3 = Problem(
            title="Power Supply Issue",
            description="Device power LED is OFF or not responding",
            severity="Critical",
            machine_model="GPS-Tracker-V1"
        )
        db.add(problem3)
        db.commit()
        db.refresh(problem3)
        
        solutions_p3 = [
            Solution(problem_id=problem3.id, step_number=1, description="Check vehicle battery voltage - should be minimum 9V"),
            Solution(problem_id=problem3.id, step_number=2, description="Check fuse - look for any blown fuse in the fuse box"),
            Solution(problem_id=problem3.id, step_number=3, description="Inspect power wiring for damage or loose connections"),
            Solution(problem_id=problem3.id, step_number=4, description="Check ground connection - must be tight and corrosion-free"),
            Solution(problem_id=problem3.id, step_number=5, description="Clean battery terminals with dry cloth"),
            Solution(problem_id=problem3.id, step_number=6, description="Reconnect power cables firmly"),
            Solution(problem_id=problem3.id, step_number=7, description="If issue persists, contact service center"),
        ]
        db.add_all(solutions_p3)
        db.commit()
    
    # Problem 4: Vehicle Engine Overheating
    problem4 = db.query(Problem).filter(Problem.title == "Vehicle Engine Overheating").first()
    if not problem4:
        problem4 = Problem(
            title="Vehicle Engine Overheating",
            description="Vehicle engine temperature is rising abnormally",
            severity="High",
            machine_model="Heavy-Truck-Series"
        )
        db.add(problem4)
        db.commit()
        db.refresh(problem4)
        
        solutions_p4 = [
            Solution(problem_id=problem4.id, step_number=1, description="Reduce engine load and find a safe location to stop"),
            Solution(problem_id=problem4.id, step_number=2, description="Wait for engine to cool down (15-20 minutes)"),
            Solution(problem_id=problem4.id, step_number=3, description="Check radiator coolant level when engine is cool"),
            Solution(problem_id=problem4.id, step_number=4, description="Clean radiator fins to remove dust and debris"),
            Solution(problem_id=problem4.id, step_number=5, description="Check for any coolant leaks under the vehicle"),
            Solution(problem_id=problem4.id, step_number=6, description="Verify thermostat is functioning properly"),
            Solution(problem_id=problem4.id, step_number=7, description="Check cooling fan operation"),
            Solution(problem_id=problem4.id, step_number=8, description="If overheating persists, call for mechanical support"),
        ]
        db.add_all(solutions_p4)
        db.commit()
    
    # Problem 5: Brake System Warning
    problem5 = db.query(Problem).filter(Problem.title == "Brake System Warning").first()
    if not problem5:
        problem5 = Problem(
            title="Brake System Warning",
            description="Brake warning light is on in vehicle dashboard",
            severity="Critical",
            machine_model="Heavy-Truck-Series"
        )
        db.add(problem5)
        db.commit()
        db.refresh(problem5)
        
        solutions_p5 = [
            Solution(problem_id=problem5.id, step_number=1, description="Check brake fluid level immediately"),
            Solution(problem_id=problem5.id, step_number=2, description="Inspect all brake lines for leaks"),
            Solution(problem_id=problem5.id, step_number=3, description="STOP driving - go to nearest service station"),
            Solution(problem_id=problem5.id, step_number=4, description="Do not ignore brake warning"),
            Solution(problem_id=problem5.id, step_number=5, description="Check brake pad wear"),
            Solution(problem_id=problem5.id, step_number=6, description="Inspect brake cylinder for damage"),
            Solution(problem_id=problem5.id, step_number=7, description="Professional mechanical inspection required"),
        ]
        db.add_all(solutions_p5)
        db.commit()
    
    print("✓ Problems and solutions seeded successfully")


def main():
    db = SessionLocal()
    try:
        print("🧹 Cleaning up old data...")
        
        # Close all open alerts to allow fresh alerts to be created
        from app.db.models import Alert
        open_alerts = db.query(Alert).filter(Alert.status == "OPEN").all()
        for alert in open_alerts:
            alert.status = "CLOSED"
            db.add(alert)
        if open_alerts:
            db.commit()
            print(f"  ✓ Closed {len(open_alerts)} open alert(s)")
        else:
            print(f"  ✓ No open alerts to close")
        
        # Create test users
        print("\n📌 Creating test users...")
        manager = get_or_create_user(
            db,
            phone="+918882374849",
            name="Manager Raj",
            role="manager",
        )
        driver1 = get_or_create_user(
            db,
            phone="+918290323758",
            name="Driver Amit",
            role="customer",
        )
        driver2 = get_or_create_user(
            db,
            phone="+919876543210",
            name="Driver Vikram",
            role="customer",
        )
        contact_person = get_or_create_user(
            db,
            phone="+919988776655",
            name="Contact Priya",
            role="manager",
        )
        
        print(f"✓ Created manager: {manager.phone_number} ({manager.name})")
        print(f"✓ Created driver 1: {driver1.phone_number} ({driver1.name})")
        print(f"✓ Created driver 2: {driver2.phone_number} ({driver2.name})")
        print(f"✓ Created contact: {contact_person.phone_number} ({contact_person.name})")

        # Create test vehicles
        print("\n🚗 Creating test vehicles...")
        vehicle1 = get_or_create_vehicle(
            db,
            vehicle_number="DL-01-AB-1234",
            manager_id=manager.id,
            driver_id=driver1.id,
        )
        vehicle2 = get_or_create_vehicle(
            db,
            vehicle_number="DL-02-CD-5678",
            manager_id=manager.id,
            driver_id=driver2.id,
        )
        
        print(f"✓ Created vehicle 1: {vehicle1.vehicle_number}")
        print(f"✓ Created vehicle 2: {vehicle2.vehicle_number}")

        # Create vehicle status (one working, one not working)
        print("\n🔧 Creating vehicle status...")
        status1 = create_or_update_vehicle_status(
            db,
            vehicle_id=vehicle1.id,
            ign_state="off",
            mode="not working",
            location="Noida Depot",
            last_gps_time=datetime.utcnow(),
        )
        status2 = create_or_update_vehicle_status(
            db,
            vehicle_id=vehicle2.id,
            ign_state="on",
            mode="working",
            location="Highway NH-1 Near Gurugram",
            last_gps_time=datetime.utcnow(),
        )
        
        print(f"✓ Vehicle 1 status: {status1.ign_state} / {status1.mode} at {status1.location}")
        print(f"✓ Vehicle 2 status: {status2.ign_state} / {status2.mode} at {status2.location}")

        # Create problems and solutions
        print("\n🎓 Creating problems and solutions...")
        create_problems_and_solutions(db)

        # Debug: Check what vehicle statuses exist
        print("\n🔍 DEBUG: Checking vehicle statuses in database...")
        all_statuses = db.query(VehicleStatus).all()
        for status in all_statuses:
            print(f"  Vehicle {status.vehicle_id}: ign_state='{status.ign_state}', mode='{status.mode}'")

        # Detect alerts
        print("\n🚨 Detecting alerts...")
        created_alerts = detect_alerts(db=db)
        print(f"✓ Detected and created {len(created_alerts)} alert(s)")
        
        for alert in created_alerts:
            print(f"  → Alert ID: {alert.id} for Vehicle: {alert.vehicle.vehicle_number}")

        # Summary
        print("\n" + "="*60)
        print("📊 DATA SEEDING COMPLETE")
        print("="*60)
        print("\n📋 Test Data Summary:")
        print(f"  • Managers: 2 (manager, contact)")
        print(f"  • Drivers: 2")
        print(f"  • Vehicles: 2 (1 NOT WORKING, 1 WORKING)")
        print(f"  • Alerts Created: {len(created_alerts)}")
        print(f"  • Problems: 5")
        print(f"  • Solutions: 34+")
        
        print("\n👤 Test Accounts:")
        print(f"  Manager: {manager.phone_number} ({manager.name})")
        print(f"  Driver 1: {driver1.phone_number} ({driver1.name})")
        print(f"  Driver 2: {driver2.phone_number} ({driver2.name})")
        print(f"  Contact: {contact_person.phone_number} ({contact_person.name})")
        
        print("\n🚗 Test Vehicles:")
        print(f"  Vehicle 1: {vehicle1.vehicle_number} (NOT WORKING - ALERT)")
        print(f"  Vehicle 2: {vehicle2.vehicle_number} (WORKING)")
        
        print("\n📞 WhatsApp Testing:")
        print(f"  • Alert will be sent to Manager: {manager.phone_number}")
        print(f"  • Manager can respond with: 1 (Handle), 2 (Transfer), or 3 (Contact Driver)")
        print(f"  • If option 3, driver will receive alert: {driver1.phone_number}")
        
        print("\n🔄 Full Flow Testing:")
        print(f"  1. Send message to {manager.phone_number} on WhatsApp")
        print(f"  2. System will ask: Handle, Transfer, or Contact Driver?")
        print(f"  3. If Contact Driver, {driver1.phone_number} will get alert")
        print(f"  4. Driver will be asked: Why is vehicle stopped?")
        print(f"  5. Collect location, mechanic need, restart time")
        print(f"  6. Generate investigation summary")
        print(f"  7. Follow-up: Is issue resolved?")
        
        print("\n" + "="*60)

    finally:
        db.close()


if __name__ == "__main__":
    main()

