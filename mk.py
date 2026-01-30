import hashlib
password = "Bich@123"  # Thay bằng password bạn muốn (ví dụ: MinhChau2024!)
hashed = hashlib.sha256(str.encode(password)).hexdigest()
print(hashed)