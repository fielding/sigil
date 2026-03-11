"""Catalog service — serves the book inventory."""
from dataclasses import dataclass


@dataclass
class Book:
    id: str
    title: str
    author: str
    price_cents: int
    isbn: str
    in_stock: bool = True


# In-memory store for demo purposes
BOOKS: dict[str, Book] = {
    "b-001": Book("b-001", "Designing Data-Intensive Applications", "Martin Kleppmann", 4500, "978-1449373320"),
    "b-002": Book("b-002", "A Philosophy of Software Design", "John Ousterhout", 2800, "978-1732102200"),
    "b-003": Book("b-003", "The Pragmatic Programmer", "David Thomas & Andrew Hunt", 4999, "978-0135957059"),
}


def list_books() -> list[Book]:
    return [b for b in BOOKS.values() if b.in_stock]


def get_book(book_id: str) -> Book | None:
    return BOOKS.get(book_id)


def search_books(query: str) -> list[Book]:
    q = query.lower()
    return [b for b in BOOKS.values() if q in b.title.lower() or q in b.author.lower()]
