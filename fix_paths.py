import re

with open('backend/main.py', 'r') as f:
    content = f.read()

# Fix occurrences like:
# os.makedirs("../frontend/static/uploads", exist_ok=True)
# file_location = f"static/uploads/{image.filename}"
# with open(file_location, "wb") as f:
#     shutil.copyfileobj(image.file, f)
# update.image_url = f"/{file_location}"

content = re.sub(
    r'file_location = f"static/uploads/\{image\.filename\}"\n\s+with open\(file_location, "wb"\) as f:\n\s+shutil\.copyfileobj\(image\.file, f\)\n\s+update\.image_url = f"/\{file_location\}"',
    r'file_location = f"../frontend/static/uploads/{image.filename}"\n        with open(file_location, "wb") as f:\n            shutil.copyfileobj(image.file, f)\n        update.image_url = f"/static/uploads/{image.filename}"',
    content
)

content = re.sub(
    r'file_path = f"static/uploads/\{image\.filename\}"\n\s+with open\(file_path, "wb"\) as buffer:\n\s+shutil\.copyfileobj\(image\.file, buffer\)\n\s+file_url = f"/\{file_path\}"',
    r'file_path = f"../frontend/static/uploads/{image.filename}"\n        with open(file_path, "wb") as buffer:\n            shutil.copyfileobj(image.file, buffer)\n        file_url = f"/static/uploads/{image.filename}"',
    content
)

content = re.sub(
    r'file_path = f"\{upload_dir\}/\{file\.filename\}"\n\s+with open\(file_path, "wb"\) as buffer:\n\s+shutil\.copyfileobj\(file\.file, buffer\)\n\s+file_url = f"/\{file_path\}"',
    r'file_path = f"{upload_dir}/{file.filename}"\n        with open(file_path, "wb") as buffer:\n            shutil.copyfileobj(file.file, buffer)\n        file_url = f"/static/uploads/{file.filename}"',
    content
)

# And line 2267:
# filepath = f"static/uploads/{filename}"
# if os.path.exists(filepath):
content = content.replace('filepath = f"static/uploads/{filename}"', 'filepath = f"../frontend/static/uploads/{filename}"')

with open('backend/main.py', 'w') as f:
    f.write(content)
print("Fixed file paths")
