"""
Script to add book-author relationships to existing books and authors
"""

from database import get_db, engine
from models import Book, Author, BookAuthor
from sqlalchemy.orm import Session
import random
import sys
import io

# Set UTF-8 encoding for console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def add_book_authors():
    """Add relationships between books and authors"""
    db = next(get_db())
    
    try:
        # Get all books and authors
        books = db.query(Book).all()
        authors = db.query(Author).all()
        
        if not books:
            print("[ERROR] No books found in database")
            return
        
        if not authors:
            print("[ERROR] No authors found in database")
            return
        
        print(f"[INFO] Found {len(books)} books and {len(authors)} authors")
        
        # Clear existing relationships
        deleted = db.query(BookAuthor).delete()
        print(f"[INFO] Cleared {deleted} existing book-author relationships")
        
        # Assign authors to books
        relationships_created = 0
        
        for book in books:
            # Randomly assign 1-2 authors to each book
            num_authors = random.randint(1, min(2, len(authors)))
            selected_authors = random.sample(authors, num_authors)
            
            for i, author in enumerate(selected_authors):
                # First author is main author, others are co-authors
                role = 'author' if i == 0 else 'co-author'
                
                book_author = BookAuthor(
                    book_id=book.id,
                    author_id=author.id,
                    role=role
                )
                db.add(book_author)
                relationships_created += 1
                # Use safe printing for Vietnamese characters
                try:
                    print(f"[OK] Added author ID {author.id} as {role} for book ID {book.id}")
                except:
                    print(f"[OK] Added author as {role} for book")
        
        db.commit()
        print(f"\n[SUCCESS] Successfully created {relationships_created} book-author relationships")
        
        # Verify by checking some authors' books
        print("\n[INFO] Verification - Books per author:")
        for author in authors[:5]:  # Check first 5 authors
            book_count = db.query(BookAuthor).filter(
                BookAuthor.author_id == author.id
            ).count()
            try:
                print(f"  - Author ID {author.id}: {book_count} books")
            except:
                print(f"  - Author: {book_count} books")
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    print("[START] Starting to add book-author relationships...")
    add_book_authors()
    print("[DONE] Done!")