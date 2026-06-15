-- Insert a test vehicle
INSERT INTO vehicles (vehicle_number, company_name) 
VALUES ('MH12AB1234', 'Test Transport Company');

-- Get the vehicle ID (you'll need to check this after running the above)
-- Let's assume the vehicle ID is 1 for this example

-- Insert vehicle status showing it's broken/inactive
-- The system checks for vehicles where is_running = 0 or power_state != 'ON'
INSERT INTO vehicle_statuses (
    vehicle_id,
    is_running,
    power_state,
    latitude,
    longitude,
    speed,
    timestamp
) VALUES (
    1,  -- Replace with actual vehicle ID
    0,  -- Not running
    'OFF',  -- Power off
    19.0760,  -- Mumbai latitude
    72.8777,  -- Mumbai longitude
    0.0,
    datetime('now', '-3 hours')  -- Last updated 3 hours ago
);

-- Insert vehicle contact for alerts
INSERT INTO vehicle_contacts (
    vehicle_id,
    name,
    phone_number,
    contact_type
) VALUES (
    1,  -- Replace with actual vehicle ID
    'Test Driver',
    '+918290323758',  -- Your test phone number
    'driver'
);
