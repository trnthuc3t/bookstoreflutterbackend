#!/usr/bin/env python3
"""Update image URLs in database to use public dev tunnels URL"""
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import BookImage

# Database URL
DB_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://openpg:18102004@localhost:5432/bookstore_online'
)

# New base URL - CHANGE THIS when you get a new dev tunnels URL
# Or set environment variable: export NEW_BASE_URL="new_url"
NEW_BASE_URL = os.getenv('NEW_BASE_URL', 'https://xrjssx4r-8000.asse.devtunnels.ms')
print(f"Updating image URLs to: {NEW_BASE_URL}")

def update_image_urls():
    """Update all image URLs to use new base URL"""
    try:
        engine = create_engine(DB_URL)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Get all images
        images = db.query(BookImage).all()
        updated_count = 0
        
        for img in images:
            old_url = img.image_url
            if old_url:
                # Check if URL has backslashes (Windows path issue)
                if '\\' in old_url:
                    # Has backslashes, need to fix
                    fixed_url = old_url.replace('\\', '/')
                    img.image_url = fixed_url
                    updated_count += 1
                    print(f"Fixed backslashes: {old_url} -> {fixed_url}")
                elif not old_url.startswith('http://') and not old_url.startswith('https://'):
                    # No protocol, assume it's a relative path
                    new_url = f"{NEW_BASE_URL}/{old_url}"
                    img.image_url = new_url
                    updated_count += 1
                    print(f"Added base URL: {old_url} -> {new_url}")
                else:
                    # Already has correct URL
                    pass
        
        if updated_count > 0:
            db.commit()
            print(f"\nUpdated {updated_count} image URLs successfully")
        else:
            print("\nNo URLs to update")
        
        db.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    update_image_urls()
