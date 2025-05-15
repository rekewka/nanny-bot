import bcrypt
from contextlib import contextmanager
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from bot.config import DB_URI


pg_pool = pool.SimpleConnectionPool(minconn=1, maxconn=10, dsn=DB_URI)

@contextmanager
def get_cursor(dict_cursor: bool = False):
    conn = pg_pool.getconn()
    try:
        with conn:  
            with conn.cursor(cursor_factory=RealDictCursor if dict_cursor else None) as cur:
                yield cur
    finally:
        pg_pool.putconn(conn)



def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def _check_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def init_db():
    with get_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(100),
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nannies (
                user_id BIGINT PRIMARY KEY REFERENCES users(user_id),
                username VARCHAR(100) UNIQUE,
                name VARCHAR(100) NOT NULL,
                city VARCHAR(100) NOT NULL,
                experience INTEGER NOT NULL CHECK (experience >= 0),
                pet_types TEXT[] DEFAULT '{}',
                description TEXT,
                hourly_rate NUMERIC(10, 2),
                available BOOLEAN DEFAULT TRUE,
                rating NUMERIC(3, 2) DEFAULT 0.0,
                password VARCHAR(200) NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id SERIAL PRIMARY KEY,
                nanny_id BIGINT REFERENCES nannies(user_id),
                reviewer_id BIGINT REFERENCES users(user_id),
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id SERIAL PRIMARY KEY,
                owner_id BIGINT REFERENCES users(user_id),
                nanny_id BIGINT REFERENCES nannies(user_id),
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                status VARCHAR(20) DEFAULT 'pending',
                pet_details TEXT,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT valid_times CHECK (end_time > start_time)
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nannies_city ON nannies (LOWER(city));")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_nannies_rating ON nannies (rating DESC);")
        cur.execute("""
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'nannies' AND column_name = 'username'
    ) THEN
        ALTER TABLE nannies ADD COLUMN username VARCHAR(100) UNIQUE;
    END IF;
END$$;
""")


def add_user(user_id: int, username: str | None):
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO users (user_id, username)
                   VALUES (%s, %s)
                   ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username""",
            (user_id, username),
        )

def add_nanny(user_id: int, nanny_data: dict):
    """Create or update nanny profile. Expects raw password in nanny_data['password']."""
    add_user(user_id, nanny_data.get("username") or nanny_data.get("name"))

    password_hash = _hash_password(nanny_data["password"])

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO nannies (
                user_id, username, name, city, experience, pet_types,
                description, hourly_rate, password
            )
            VALUES (%(user_id)s, %(username)s, %(name)s, %(city)s, %(experience)s, %(pet_types)s,
                    %(description)s, %(hourly_rate)s, %(password)s)
            ON CONFLICT (user_id) DO UPDATE SET
                username     = EXCLUDED.username,
                name         = EXCLUDED.name,
                city         = EXCLUDED.city,
                experience   = EXCLUDED.experience,
                pet_types    = EXCLUDED.pet_types,
                description  = EXCLUDED.description,
                hourly_rate  = EXCLUDED.hourly_rate,
                password     = EXCLUDED.password
            """,
            {
                "user_id": user_id,
                "username": nanny_data.get("username"),
                "name": nanny_data["name"],
                "city": nanny_data["city"],
                "experience": nanny_data["experience"],
                "pet_types": nanny_data.get("pet_types", []),
                "description": nanny_data.get("description", ""),
                "hourly_rate": nanny_data.get("hourly_rate", 0),
                "password": password_hash,
            },
        )

def get_nanny(user_id: int):
    with get_cursor(True) as cur:
        cur.execute("SELECT * FROM nannies WHERE user_id = %s", (user_id,))
        return cur.fetchone()


def get_all_nannies(city: str | None = None, pet_type: str | None = None, min_rating: float | None = None):
    with get_cursor(True) as cur:
        query = "SELECT * FROM nannies WHERE available = TRUE"
        params: list = []
        if city:
            query += " AND LOWER(city) = LOWER(%s)";
            params.append(city)
        if pet_type:
            query += " AND %s = ANY(pet_types)";
            params.append(pet_type)
        if min_rating is not None:
            query += " AND rating >= %s";
            params.append(min_rating)
        query += " ORDER BY rating DESC, experience DESC"
        cur.execute(query, params)
        return cur.fetchall()



def add_booking(owner_id: int, nanny_id: int, start_time, end_time, pet_details: str, address: str) -> int:
    with get_cursor(True) as cur:
        cur.execute(
            """
            INSERT INTO bookings (owner_id, nanny_id, start_time, end_time, pet_details, address)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (owner_id, nanny_id, start_time, end_time, pet_details, address),
        )
        return cur.fetchone()["id"]

def update_booking_status(booking_id: int, status: str):
    with get_cursor() as cur:
        cur.execute("UPDATE bookings SET status=%s WHERE id=%s", (status, booking_id))

def add_review(nanny_id: int, reviewer_id: int, rating: int, comment: str | None):
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO reviews (nanny_id, reviewer_id, rating, comment) VALUES (%s,%s,%s,%s)",
            (nanny_id, reviewer_id, rating, comment),
        )
        cur.execute(
            "UPDATE nannies SET rating = (SELECT AVG(rating) FROM reviews WHERE nanny_id=%s) WHERE user_id=%s",
            (nanny_id, nanny_id),
        )


def verify_login(username: str, password: str):
    with get_cursor(True) as cur:
        cur.execute("SELECT user_id, password FROM nannies WHERE username = %s", (username,))
        row = cur.fetchone()
        if row and _check_password(password, row["password"]):
            return row["user_id"]
        return None



def get_nanny_bookings(nanny_id: int, status: str | None = None):
    with get_cursor(True) as cur:
        query = (
            "SELECT b.*, u.username AS owner_name FROM bookings b "
            "JOIN users u ON b.owner_id = u.user_id WHERE b.nanny_id = %s"
        )
        params = [nanny_id]
        if status:
            query += " AND b.status = %s"; params.append(status)
        query += " ORDER BY b.start_time"
        cur.execute(query, params)
        return cur.fetchall()

def get_owner_bookings(owner_id: int, status: str | None = None):
    with get_cursor(True) as cur:
        query = (
            "SELECT b.*, n.name AS nanny_name FROM bookings b "
            "JOIN nannies n ON b.nanny_id = n.user_id WHERE b.owner_id = %s"
        )
        params = [owner_id]
        if status:
            query += " AND b.status = %s"; params.append(status)
        query += " ORDER BY b.start_time"
        cur.execute(query, params)
        return cur.fetchall()



def delete_nanny(user_id: int):
    with get_cursor() as cur:
        cur.execute("DELETE FROM bookings WHERE nanny_id = %s", (user_id,))
        cur.execute("DELETE FROM nannies  WHERE user_id  = %s", (user_id,))

def update_user_type(user_id: int, user_type: str):
    """Update user type in the database (owner or nanny)"""
    with get_cursor() as cur:
        cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'user_type'
            ) THEN
                ALTER TABLE users ADD COLUMN user_type VARCHAR(20) DEFAULT 'owner';
            END IF;
        END$$;
        """)
        
        cur.execute(
            "UPDATE users SET user_type = %s WHERE user_id = %s",
            (user_type, user_id)
        )