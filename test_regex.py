import re

# Name pattern
NAME_PATTERN = re.compile(r'^(?:[^\W_]|[\s\'\-\.]){1,100}$')

test_names = [
    "John Doe",
    "Jöhn Dôe",
    "María-José",
    "O'Connor",
    "Patient 0",
    "محمد", # Arabic
    "山田太郎", # Kanji
    "Иван", # Cyrillic
    "अमिताभ", # Hindi
    "Test_Name", # Should fail
    "<script>", # Should fail
]

print("NAME:")
for n in test_names:
    print(f"{n}: {bool(NAME_PATTERN.match(n))}")

# Medical text pattern
MED_PATTERN = re.compile(r'^(?:[^\W_]|[\s\,\.\-\(\)\/\:\+\%\&]){0,500}$')

print("\nMED_TEXT:")
print(f"Normal: {bool(MED_PATTERN.match('Hello 123 + %'))}")
print(f"Script: {bool(MED_PATTERN.match('<script>'))}")

# Emergency message
EMERGENCY_PATTERN = re.compile(r'^(?:[^\W_]|[\s\,\.\-\(\)\/\:\+\%\&\!\?\'\"]){0,1000}$')
print("\nEMERGENCY:")
print(f"Normal: {bool(EMERGENCY_PATTERN.match('Help! I am here.'))}")
print(f"Script: {bool(EMERGENCY_PATTERN.match('<script>'))}")

