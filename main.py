from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import itertools # สำหรับใช้ในการสร้าง ID

app = FastAPI()

# ชี้โฟลเดอร์ template + static
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------- ข้อมูลจำลองในหน่วยความจำ (ไม่ใช้ฐานข้อมูล) ----------

# ห้องซ้อมแบบ fix ไว้ก่อน
rooms = [
    {"id": 1, "name": "ห้องซ้อม 1", "description": "ห้องเล็ก สำหรับซ้อมเดี่ยว/ดูโอ", "capacity": 2},
    {"id": 2, "name": "ห้องซ้อม 2", "description": "ห้องกลาง สำหรับวงเล็ก", "capacity": 4},
    {"id": 3, "name": "ห้องซ้อม 3", "description": "ห้องใหญ่ สำหรับวงเต็มวง", "capacity": 6},
]

# เก็บการจองทั้งหมดไว้ใน list
bookings = []  # แต่ละรายการเป็น dict
booking_id_counter = itertools.count(1) # ใช้ counter เพื่อสร้าง ID

# -------------------- ฟังก์ชันช่วย --------------------

def is_conflict(new_start: datetime, new_end: datetime, existing_start: datetime, existing_end: datetime) -> bool:
    """ตรวจสอบว่าช่วงเวลาใหม่ซ้อนทับกับช่วงเวลาที่มีอยู่หรือไม่"""
    # จะไม่ซ้ำซ้อน ถ้า [New End <= Existing Start] หรือ [New Start >= Existing End]
    # ถ้าไม่ใช่เงื่อนไขข้างต้น ถือว่าซ้ำซ้อน
    return not (new_end <= existing_start or new_start >= existing_end)


# ---------- Routes ----------

@app.get("/")
async def home(request: Request):
    # หน้าแรก แสดงห้องทั้งหมด
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "rooms": rooms}
    )


@app.get("/room/{room_id}")
async def room_page(room_id: int, request: Request, error_message: str = None):
    # หาห้องจาก list rooms
    room = next((r for r in rooms if r["id"] == room_id), None)
    if not room:
        # ถ้าไม่เจอห้อง กลับไปหน้าแรก
        return RedirectResponse("/", status_code=303)

    # ดึงเฉพาะ booking ของห้องนี้
    room_bookings = []
    for b in bookings:
        if b["room_id"] == room_id:
            # ใช้ strftime เพื่อจัดรูปแบบเวลาให้สวยงาม
            start_str = b["start_dt"].strftime("%H:%M")
            end_str = b["end_dt"].strftime("%H:%M")
            date_str = b["start_dt"].strftime("%Y-%m-%d")
            room_bookings.append({
                "id": b["id"],
                "date": date_str,
                "time": f"{start_str} - {end_str}",
                "person_name": b["person_name"],
                "person_email": b["person_email"],
            })

    # ส่ง error_message ไปด้วย (ถ้ามี)
    return templates.TemplateResponse(
        "room.html",
        {"request": request, "room": room, "bookings": room_bookings, "error": error_message}
    )


@app.post("/book/{room_id}")
async def book_room(
    room_id: int,
    request: Request,
    date: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    person_name: str = Form(...),
    person_email: str = Form(...),
):
    # หาห้อง
    room = next((r for r in rooms if r["id"] == room_id), None)
    if not room:
        return RedirectResponse("/", status_code=303)

    # 1. แปลงวันที่และเวลาจาก Form เป็น datetime object
    try:
        new_start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        new_end_dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        # ถ้า format ไม่ถูกต้อง ให้ส่ง error message กลับไป
        error_msg = "รูปแบบวันที่หรือเวลาไม่ถูกต้อง กรุณาลองอีกครั้ง"
        return RedirectResponse(f"/room/{room_id}?error_message={error_msg}", status_code=303)

    # 2. ตรวจสอบความสมเหตุสมผลของเวลา
    if new_end_dt <= new_start_dt:
        error_msg = "เวลาสิ้นสุดต้องอยู่หลังเวลาเริ่มต้น"
        return RedirectResponse(f"/room/{room_id}?error_message={error_msg}", status_code=303)

    # 3. ตรวจสอบความซ้ำซ้อนของการจอง (Booking Conflict Check)
    for existing_booking in bookings:
        if existing_booking["room_id"] == room_id:
            existing_start_dt = existing_booking["start_dt"]
            existing_end_dt = existing_booking["end_dt"]

            if is_conflict(new_start_dt, new_end_dt, existing_start_dt, existing_end_dt):
                error_msg = f"การจองซ้ำซ้อน: ห้อง {room['name']} ถูกจองในช่วงเวลานั้นแล้ว"
                return RedirectResponse(f"/room/{room_id}?error_message={error_msg}", status_code=303)

    # 4. ถ้าไม่มี Conflict -> สร้าง booking ใหม่
    booking = {
        "id": next(booking_id_counter),
        "room_id": room_id,
        "start_dt": new_start_dt,
        "end_dt": new_end_dt,
        "person_name": person_name,
        "person_email": person_email,
    }
    bookings.append(booking)

    # จองเสร็จ -> กลับไปหน้าห้องเดิม
    return RedirectResponse(f"/room/{room_id}", status_code=303)


@app.get("/bookings")
async def all_bookings(request: Request):
    # รวม booking + ชื่อห้อง + ปรับปรุงการแสดงผลเวลา
    enriched = []
    for b in bookings:
        room = next((r for r in rooms if r["id"] == b["room_id"]), None)

        # จัดรูปแบบเวลาจาก datetime object
        date_str = b["start_dt"].strftime("%Y-%m-%d")
        start_str = b["start_dt"].strftime("%H:%M")
        end_str = b["end_dt"].strftime("%H:%M")

        enriched.append({
            "id": b["id"],
            "date": date_str,
            "time": f"{start_str} - {end_str}",
            "person_name": b["person_name"],
            "person_email": b["person_email"],
            "room_name": room["name"] if room else "ไม่ทราบห้อง",
        })

    return templates.TemplateResponse(
        "bookings.html",
        {"request": request, "bookings": enriched}
    )