-- Migration: Add latitude, longitude and power_state to vehicle_statuses table
-- Run this SQL script against your PostgreSQL database

-- Check if columns already exist before adding them
DO $$
BEGIN
    -- Add latitude column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'vehicle_statuses' 
        AND column_name = 'latitude'
    ) THEN
        ALTER TABLE vehicle_statuses ADD COLUMN latitude FLOAT;
        RAISE NOTICE 'Added latitude column to vehicle_statuses';
    ELSE
        RAISE NOTICE 'Column latitude already exists in vehicle_statuses';
    END IF;

    -- Add longitude column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'vehicle_statuses' 
        AND column_name = 'longitude'
    ) THEN
        ALTER TABLE vehicle_statuses ADD COLUMN longitude FLOAT;
        RAISE NOTICE 'Added longitude column to vehicle_statuses';
    ELSE
        RAISE NOTICE 'Column longitude already exists in vehicle_statuses';
    END IF;

    -- Add power_state column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'vehicle_statuses' 
        AND column_name = 'power_state'
    ) THEN
        ALTER TABLE vehicle_statuses ADD COLUMN power_state VARCHAR(20);
        RAISE NOTICE 'Added power_state column to vehicle_statuses';
        
        -- Update existing records with default power state values
        UPDATE vehicle_statuses 
        SET power_state = CASE 
            WHEN ign_state = 'on' THEN 'on'
            WHEN ign_state = 'off' THEN 'off'
            ELSE 'unknown'
        END
        WHERE power_state IS NULL;
        
        RAISE NOTICE 'Updated existing records with default power state values';
    ELSE
        RAISE NOTICE 'Column power_state already exists in vehicle_statuses';
    END IF;
END $$;

-- Verify the changes
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'vehicle_statuses' 
AND column_name IN ('latitude', 'longitude', 'power_state')
ORDER BY column_name;