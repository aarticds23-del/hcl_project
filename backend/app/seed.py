
from .db import init_db, conn
from .config import DOCS
from .rag import index_document

from datetime import date
import csv


# -------------------- Configuration --------------------

TOTAL_STUDENTS = 30
FIRST_STUDENT_ID = 1001
TOTAL_CLASSES = 28

FAILING_STUDENTS = {1, 5, 12}

ATTENDANCE_BY_STUDENT = {
    1: 22,
    2: 21,
    3: 20,
}

DOCS_DATA = [
    (
        "ACAD-REG-2023",
        "Academic Regulations for B.Tech (Synthetic Demo)",
        "Office of Dean (Academics)",
        1,
        "regulation",
        "2.0",
        "2023-07-01",
        "2024-06-30",
        "",
        "ALL",
        "2023+",
        "Academic regulation: Students require a minimum attendance "
        "of 70% for end-semester examination. This synthetic document "
        "expired on 2024-06-30.",
    ),
    (
        "ACAD-REG-2024",
        "Academic Regulations for B.Tech (Synthetic Demo)",
        "Office of Dean (Academics)",
        1,
        "regulation",
        "3.1",
        "2024-07-01",
        "",
        "ACAD-REG-2023#7.2",
        "ALL",
        "2023+",
        "Section 7.2 Attendance: A student must maintain at least "
        "75% attendance in each registered course to appear in the "
        "end-semester examination. This is a synthetic demo regulation.",
    ),
    (
        "EXAM-RULES-2024",
        "Examination and Supplementary Rules (Synthetic Demo)",
        "Controller of Examinations",
        1,
        "regulation",
        "1.0",
        "2024-07-01",
        "",
        "",
        "ALL",
        "2023+",
        "Section 5 Supplementary examination: A student who receives "
        "FAIL in a course may apply for supplementary examination, "
        "provided the student has attendance of at least 75% in that "
        "course. Apply through the examination portal within seven "
        "days of result publication. This is synthetic demo content.",
    ),
    (
        "ATT-CIRCULAR-2024",
        "Attendance Circular (Synthetic Demo)",
        "Academic Office",
        2,
        "circular",
        "1.0",
        "2024-08-01",
        "",
        "",
        "ALL",
        "2023+",
        "The Academic Office recommends 80% attendance. This circular "
        "does not supersede Academic Regulations and cannot override "
        "the regulation.",
    ),
    (
        "CSE-NOTICE-2024",
        "CSE Department Notice (Synthetic Demo)",
        "CSE Department",
        3,
        "notice",
        "1.0",
        "2024-07-01",
        "",
        "",
        "BTECH_CSE",
        "2024+",
        "CSE students should consult advisors for attendance support. "
        "This notice is informational only.",
    ),
]


COURSES = [
    ("CS201", "Data Structures", "BTECH_CSE", 3, 4),
    ("CS202", "Algorithms", "BTECH_CSE", 4, 4),
    ("EC201", "Signals and Systems", "BTECH_ECE", 3, 4),
    ("EC202", "Digital Systems", "BTECH_ECE", 4, 4),
    ("HS201", "Technical Communication", "BTECH_CSE", 3, 2),
    ("MA201", "Discrete Mathematics", "BTECH_ECE", 3, 4),
]


RULES = [
    (
        "ATT-MIN-01",
        "Minimum attendance for end semester",
        "attendance_percentage",
        ">=",
        "75",
        "ALL",
        "2023+",
        "2024-07-01",
        "",
        "ACAD-REG-2024",
        "7.2",
    ),
    (
        "SUPP-01",
        "Supplementary eligibility",
        "result",
        "=",
        "FAIL",
        "ALL",
        "2023+",
        "2024-07-01",
        "",
        "EXAM-RULES-2024",
        "5",
    ),
]


# -------------------- Data generation --------------------

def generate_students():
    """Generate the synthetic student records."""

    students = []

    for i in range(1, TOTAL_STUDENTS + 1):
        student_id = f"S{FIRST_STUDENT_ID + i - 1}"

        programme = (
            "BTECH_CSE" if i <= 15 else "BTECH_ECE"
        )

        batch = 2023 if i % 2 else 2024
        semester = 4
        cgpa = round(6.5 + i * 0.1, 2)
        backlogs = 1 if i in FAILING_STUDENTS else 0

        students.append(
            (
                student_id,
                f"Demo Student {i:02d}",
                programme,
                batch,
                semester,
                cgpa,
                backlogs,
            )
        )

    return students


# -------------------- Database seeding --------------------

def seed():
    """Initialize the database and insert missing demo records."""

    init_db()
    DOCS.mkdir(parents=True, exist_ok=True)

    today = str(date.today())
    documents_to_index = []

    with conn() as c:

        # 1. Insert students without duplicating existing records.
        c.executemany(
            "INSERT OR IGNORE INTO students VALUES (?, ?, ?, ?, ?, ?, ?)",
            generate_students(),
        )

        # 2. Insert courses.
        c.executemany(
            "INSERT OR IGNORE INTO courses VALUES (?, ?, ?, ?, ?)",
            COURSES,
        )

        # 3. Insert attendance and examination results.
        for i in range(1, TOTAL_STUDENTS + 1):
            student_id = f"S{FIRST_STUDENT_ID + i - 1}"

            course_code = "CS201" if i <= 15 else "EC201"

            attended = ATTENDANCE_BY_STUDENT.get(i, 25)

            c.execute(
                """
                INSERT OR IGNORE INTO attendance
                VALUES (?, ?, ?, ?)
                """,
                (
                    student_id,
                    course_code,
                    TOTAL_CLASSES,
                    attended,
                ),
            )

            total_marks = 42 if i in FAILING_STUDENTS else 70
            internal_marks = 20
            external_marks = total_marks - internal_marks

            result = (
                "FAIL" if total_marks < 50 else "PASS"
            )

            c.execute(
                """
                INSERT OR IGNORE INTO results
                (
                    student_id,
                    course_code,
                    exam_session,
                    internal_marks,
                    external_marks,
                    total_marks,
                    max_marks,
                    result
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    student_id,
                    course_code,
                    "2024-DEC",
                    internal_marks,
                    external_marks,
                    total_marks,
                    100,
                    result,
                ),
            )

        # 4. Insert policy metadata and document text.
        for doc in DOCS_DATA:
            doc_id = doc[0]
            title = doc[1]
            metadata_values = doc[:11]
            text = doc[11]

            # Check whether the document text already exists.
            existing_doc = c.execute(
                "SELECT 1 FROM documents WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()

            c.execute(
                """
                INSERT OR IGNORE INTO source_register
                (
                    doc_id,
                    title,
                    issuer,
                    authority_level,
                    doc_type,
                    version,
                    effective_from,
                    effective_to,
                    supersedes,
                    scope_programme,
                    scope_batches,
                    provenance,
                    retrieved_on,
                    synthetic
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    *metadata_values,
                    "https://example.edu/synthetic",
                    today,
                    "Y",
                ),
            )

            c.execute(
                """
                INSERT OR IGNORE INTO documents (doc_id, text)
                VALUES (?, ?)
                """,
                (doc_id, text),
            )

            # Save a Markdown copy of each policy document.
            (DOCS / f"{doc_id}.md").write_text(
                f"# {title}\n\n{text}",
                encoding="utf-8",
            )

            # Queue only newly inserted documents for vector indexing.
            if existing_doc is None:
                source_row = c.execute(
                    """
                    SELECT * FROM source_register
                    WHERE doc_id = ?
                    """,
                    (doc_id,),
                ).fetchone()

                documents_to_index.append(
                    (doc_id, text, dict(source_row))
                )

        # 5. Insert deterministic eligibility rules.
        c.executemany(
            """
            INSERT OR IGNORE INTO rule_registry
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            RULES,
        )

    # 6. Index documents after the SQLite transaction has completed.
    for doc_id, text, metadata in documents_to_index:
        index_document(doc_id, text, metadata)

    # 7. Export the source register to CSV.
    with conn() as c:
        source_rows = c.execute(
            "SELECT * FROM source_register ORDER BY doc_id"
        ).fetchall()

    csv_path = DOCS.parent / "source_register.csv"

    with open(
        csv_path,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)

        writer.writerow(
            [
                "doc_id",
                "title",
                "issuer",
                "authority_level",
                "doc_type",
                "version",
                "effective_from",
                "effective_to",
                "supersedes",
                "scope_programme",
                "scope_batches",
                "provenance",
                "retrieved_on",
                "synthetic",
            ]
        )

        writer.writerows(source_rows)

    print("Database seeding completed successfully.")


if __name__ == "__main__":
    seed()
