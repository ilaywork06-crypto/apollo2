
# ----- Classes ----- #


class UserProfile:
    def __init__(
        self,
        user_id,
        username,
        email,
        ):
        self.user_id = user_id
        self.username = normalize_username(username)
        self.email = email

    def display_name(self):
        return self.username.replace("_", " ").title()


class HealthRecord:
    def __init__(
        self,
        patient_id,
        weight,
        height,
        age,
        notes,
        ):
        self.patient_id = patient_id
        self.weight = weight
        self.height = height
        self.age = age
        self.notes = notes

    def bmi(self):
        return calculate_bmi(self.weight, self.height)

    def bmi_category(self):
        b = self.bmi()
        if b < 18.5:
            return "underweight"
        elif b < 25:
            return "normal"
        elif b < 30:
            return "overweight"
        return "obese"


class Location:
    def __init__(
        self,
        name,
        latitude,
        longitude,
        country_code,
        ):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.country_code = country_code

    def distance_to(self, other):
        return distance_km(
            self.latitude,
            self.longitude,
            other.latitude,
            other.longitude,
        )

    def formatted(self):
        return f"{self.name} ({self.country_code})"


class PaginatedResponse:
    def __init__(
        self,
        items,
        total,
        page,
        page_size,
        ):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size

    def has_next(self):
        return self.page * self.page_size < self.total

    def has_prev(self):
        return self.page > 1


class DataTable:
    def __init__(
        self,
        columns,
        rows,
        title,
        ):
        self.columns = columns
        self.rows = rows
        self.title = title

    def filter_rows(
        self,
        column,
        value,
        ):
        idx = self.columns.index(column)
        return [row for row in self.rows if row[idx] == value]

    def to_csv(self):
        lines = [",".join(self.columns)]
        for row in self.rows:
            lines.append(",".join(str(c) for c in row))
        return "\n".join(lines)

# ----- Functions ----- #


def normalize_username(username):
    return username.strip().lower().replace(" ", "_")


def get_full_name(first, last):
    return f"{first} {last}"


def calculate_bmi(weight_kg, height_m):
    return weight_kg / (height_m**2)


def format_address(
    street,
    city,
    state,
    zip_code,
    ):
    return f"{street}, {city}, {state} {zip_code}"


def distance_km(
    lat1,
    lon1,
    lat2,
    lon2,
    ):
    import math

    r = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.asin(math.sqrt(a))


def paginate(
    items,
    page,
    page_size,
    ):
    start = (page - 1) * page_size
    return items[start : start + page_size]


def sort_by_field(
    records,
    field,
    reverse,
    ):
    return sorted(
        records,
        key=lambda r: r.get(field),
        reverse=reverse,
    )


def group_by(records, key_field):
    result = {}
    for record in records:
        k = record.get(key_field)
        result.setdefault(k, []).append(record)
    return result
