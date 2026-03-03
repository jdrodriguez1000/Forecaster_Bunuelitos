
import psycopg2
import sys
import os
from dotenv import load_dotenv

def run_migration():
    load_dotenv()
    
    # Supabase Connection Info
    project_ref = "hglnaotitdfsobxmqwuu"
    db_password = "3i6RCgn6axGzh6ql"
    
    # Connection strings to try
    configs = [
        {
            "host": f"aws-0-us-east-1.pooler.supabase.com",
            "user": f"postgres.{project_ref}",
            "port": "5432"
        },
        {
            "host": f"db.{project_ref}.supabase.co",
            "user": "postgres",
            "port": "5432"
        },
        # Port 6543 is for transaction pooler
        {
            "host": f"aws-0-us-east-1.pooler.supabase.com",
            "user": f"postgres.{project_ref}",
            "port": "6543"
        }
    ]
    
    success = False
    for config in configs:
        try:
            print(f"Attempting to connect to host: {config['host']} via user: {config['user']} on port {config['port']}...")
            conn = psycopg2.connect(
                host=config['host'],
                port=config['port'],
                database="postgres",
                user=config['user'],
                password=db_password,
                connect_timeout=10
            )
            print(f"Connected successfully!")
            cur = conn.cursor()
            
            # Migration
            print("Running migration: Adding 'processing_type' column...")
            sql = """
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 
                    FROM information_schema.columns 
                    WHERE table_name='pipeline_execution_status' AND column_name='processing_type'
                ) THEN
                    ALTER TABLE pipeline_execution_status ADD COLUMN processing_type TEXT;
                    COMMENT ON COLUMN pipeline_execution_status.processing_type IS 'Type of processing: FULL, INCREMENTAL, or NO NEW DATA';
                END IF;
            END $$;
            """
            cur.execute(sql)
            conn.commit()
            print("Migration completed successfully.")
            
            cur.close()
            conn.close()
            success = True
            break
        except Exception as e:
            print(f"Failed: {e}")
    
    return success

if __name__ == "__main__":
    if run_migration():
        print("--- Migration Success ---")
        sys.exit(0)
    else:
        print("--- Migration Failed ---")
        sys.exit(1)
