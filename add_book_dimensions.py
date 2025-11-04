"""
Script to add dimensions and weight columns to books table
Run this to update existing database
"""

from sqlalchemy import create_engine, text
from database import DATABASE_URL
import sys

def add_dimensions_columns():
    """Add subtitle, dimensions and weight columns to books table"""
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as conn:
            # Check if columns already exist
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='books' AND column_name IN ('subtitle', 'length', 'width', 'thickness', 'weight')
            """))
            existing_columns = [row[0] for row in result]
            
            # Add subtitle if not exists
            if 'subtitle' not in existing_columns:
                print("Adding subtitle column...")
                conn.execute(text("ALTER TABLE books ADD COLUMN subtitle VARCHAR(200)"))
                conn.commit()
                print("[OK] Added subtitle column")
            else:
                print("[SKIP] subtitle column already exists")
            
            # Add length if not exists
            if 'length' not in existing_columns:
                print("Adding length column...")
                conn.execute(text("ALTER TABLE books ADD COLUMN length DECIMAL(5, 2)"))
                conn.commit()
                print("[OK] Added length column")
            else:
                print("[SKIP] length column already exists")
            
            # Add width if not exists
            if 'width' not in existing_columns:
                print("Adding width column...")
                conn.execute(text("ALTER TABLE books ADD COLUMN width DECIMAL(5, 2)"))
                conn.commit()
                print("[OK] Added width column")
            else:
                print("[SKIP] width column already exists")
            
            # Add thickness if not exists
            if 'thickness' not in existing_columns:
                print("Adding thickness column...")
                conn.execute(text("ALTER TABLE books ADD COLUMN thickness DECIMAL(5, 2)"))
                conn.commit()
                print("[OK] Added thickness column")
            else:
                print("[SKIP] thickness column already exists")
            
            # Add weight if not exists
            if 'weight' not in existing_columns:
                print("Adding weight column...")
                conn.execute(text("ALTER TABLE books ADD COLUMN weight INTEGER"))
                conn.commit()
                print("[OK] Added weight column")
            else:
                print("[SKIP] weight column already exists")
            
            print("\n[SUCCESS] Database migration completed successfully!")
            print("New columns: subtitle, length, width, thickness, weight")
            
    except Exception as e:
        print(f"[ERROR] Error during migration: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        engine.dispose()

if __name__ == "__main__":
    print("Starting database migration...")
    print("Adding dimensions and weight columns to books table\n")
    add_dimensions_columns()

