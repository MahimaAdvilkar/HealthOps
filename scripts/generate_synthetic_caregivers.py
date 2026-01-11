import csv
import random
from datetime import date, timedelta

NUM_CAREGIVERS = 300

genders = ["Female", "Male", "Other"]
languages = ["English", "Spanish", "Mandarin", "Hindi", "Tagalog"]
skills = ["Personal Care", "ECM", "Home Health", "Behavioral Support"]
employment_types = ["Full-Time", "Part-Time", "Contract"]
availability = ["Weekdays", "Weekends", "Evenings", "Flexible"]
cities = ["San Francisco", "Oakland", "San Jose", "Fremont", "Dublin"]

def random_dob():
    start = date(1960, 1, 1)
    end = date(2000, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))

rows = []

for i in range(1, NUM_CAREGIVERS + 1):
    caregiver_id = f"CG-{1000+i}"
    dob = random_dob()
    age = date.today().year - dob.year

    rows.append({
        "caregiver_id": caregiver_id,
        "gender": random.choice(genders),
        "date_of_birth": dob.isoformat(),
        "age": age,
        "primary_language": random.choice(languages),
        "skills": random.choice(skills),
        "employment_type": random.choice(employment_types),
        "availability": random.choice(availability),
        "city": random.choice(cities),
        "active": random.choice(["Y", "Y", "Y", "N"])  # mostly active
    })

output_path = "data/caregivers_synthetic.csv"

with open(output_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {NUM_CAREGIVERS} caregivers → {output_path}")


