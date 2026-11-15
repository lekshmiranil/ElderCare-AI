"""Demo data. Entirely fictional; safe to reset at any time."""
from datetime import datetime, timedelta

from .connection import get_connection
from .schema import TABLES, init_db


def reset_demo_data(db_path) -> None:
    """Drop all rows and re-insert fictional sample data."""
    init_db(db_path)
    now = datetime.now()
    today = now.date()
    with get_connection(db_path) as conn:
        for table in TABLES:
            conn.execute(f"DELETE FROM {table}")
        conn.execute("DELETE FROM sqlite_sequence")

        conn.execute("INSERT INTO people (role,name,age,phone,relationship) VALUES "
                     "('elder','Lekshmi',78,'+91 90000 00001','Self')")
        conn.execute("INSERT INTO people (role,name,age,phone,relationship) VALUES "
                     "('caregiver','Daniel Thomas',45,'+91 90000 00002','Son')")

        meds = [("Metformin (sample)", "Once daily, after breakfast", "08:00"),
                ("Amlodipine (sample)", "Once daily, morning", "09:00"),
                ("Vitamin D (sample)", "Once daily, after lunch", "13:30"),
                ("Atorvastatin (sample)", "Once daily, at bedtime", "21:00")]
        conn.executemany("INSERT INTO medications (elder_id,name,schedule_text,reminder_time) "
                         "VALUES (1,?,?,?)", meds)

        # Seven days of history: mostly taken, a few skipped or missed
        for i in range(1, 8):
            d = (today - timedelta(days=i)).isoformat()
            for med_id in (1, 2, 4):
                status = "taken"
                if (i + med_id) % 6 == 0:
                    status = "missed"
                elif (i + med_id) % 7 == 0:
                    status = "skipped"
                conn.execute("INSERT INTO medication_logs (medication_id,log_date,status,logged_at) "
                             "VALUES (?,?,?,?)", (med_id, d, status, f"{d}T20:00:00"))

        conn.execute("INSERT INTO appointments (elder_id,title,appt_datetime,location) VALUES "
                     "(1,'Routine check-up',?,'City Clinic (sample)')",
                     ((now + timedelta(days=3)).replace(hour=10, minute=30).isoformat(timespec="minutes"),))
        conn.execute("INSERT INTO appointments (elder_id,title,appt_datetime,location) VALUES "
                     "(1,'Eye examination',?,'Vision Care Centre (sample)')",
                     ((now + timedelta(days=10)).replace(hour=15, minute=0).isoformat(timespec="minutes"),))

        moods = [(4, 4, 3), (4, 3, 3), (3, 3, 2), (4, 4, 3), (3, 2, 2), (2, 2, 1), (3, 3, 2)]
        for i, (m, w, a) in enumerate(moods, start=1):
            d = (today - timedelta(days=8 - i)).isoformat()
            conn.execute("INSERT INTO wellness_checkins (elder_id,checkin_date,mood,wellbeing,activity,notes) "
                         "VALUES (1,?,?,?,?,'')", (d, m, w, a))

        ts = (now - timedelta(days=2)).isoformat(timespec="seconds")
        conn.execute("INSERT INTO emergency_events (elder_id,triggered_at,alert_sent,delivery_note) "
                     "VALUES (1,?,0,'Demo mode: caregiver notification simulated, nothing was sent')", (ts,))
        conn.execute("INSERT INTO fall_events (elder_id,detected_at,peak_g,threshold_g,simulated) "
                     "VALUES (1,?,3.4,2.5,1)", ((now - timedelta(days=4)).isoformat(timespec="seconds"),))
        conn.execute("INSERT INTO notifications (created_at,category,message,simulated) VALUES "
                     "(?,'medication','Missed medication reminder (sample data)',1)", (ts,))
        conn.execute("INSERT INTO app_settings (key,value) VALUES ('ai_enabled','false')")
