import pytest
from app.core.input_validation import HealthcareValidators

def test_unicode_names():
    # Names should be successfully validated and returned
    valid_names = [
        "John Doe",
        "Jöhn Dôe",
        "María-José",
        "O'Connor",
        "Patient 0",
        "محمد", # Arabic
        "山田太郎", # Kanji
        "Иван", # Cyrillic
        "अमिताभ", # Hindi
    ]

    for name in valid_names:
        assert HealthcareValidators.validate_person_name(name) == name

def test_invalid_names():
    # Names with invalid characters
    invalid_names = [
        "<script>alert(1)</script>",
        "Name_With_Underscore",
        "Name!",
        "Name@Provider",
    ]

    for name in invalid_names:
        with pytest.raises(ValueError):
            HealthcareValidators.validate_person_name(name)

def test_unicode_emergency_messages():
    valid_msgs = [
        "Help! I am here.",
        "Need ambulance at 123 Main St.",
        "مساعدة! أحتاج إسعاف", # Arabic
        "助けて！", # Japanese
        "Помогите!", # Cyrillic
    ]

    for msg in valid_msgs:
        assert HealthcareValidators.validate_emergency_message(msg) == msg
