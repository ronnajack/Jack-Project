from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

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
_next_booking_id = 1


def get_next_booking_id() -> int:
    global _next_booking_id
    bid = _next_booking_id
    _next_booking_id += 1
    return bid


# ---------- Routes ----------

@app.get("/")
async def home(request: Request):
    # หน้าแรก แสดงห้องทั้งหมด
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "rooms": rooms}
    )


@app.get("/room/{room_id}")
async def room_page(room_id: int, request: Request):
    # หาห้องจาก list rooms
    room = next((r for r in rooms if r["id"] == room_id), None)
    if not room:
        # ถ้าไม่เจอห้อง กลับไปหน้าแรก
        return RedirectResponse("/", status_code=303)

    # ดึงเฉพาะ booking ของห้องนี้
    room_bookings = [b for b in bookings if b["room_id"] == room_id]

    return templates.TemplateResponse(
        "room.html",
        {"request": request, "room": room, "bookings": room_bookings}
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

    # สร้าง booking ใหม่ (เก็บเป็น string ก็ได้ ยังไม่ต้องแปลงเป็น time object)
    booking = {
        "id": get_next_booking_id(),
        "room_id": room_id,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "person_name": person_name,
        "person_email": person_email,
    }
    bookings.append(booking)

    # จองเสร็จ -> กลับไปหน้าห้องเดิม
    return RedirectResponse(f"/room/{room_id}", status_code=303)


@app.get("/bookings")
async def all_bookings(request: Request):
    # รวม booking + ชื่อห้อง
    enriched = []
    for b in bookings:
        room = next((r for r in rooms if r["id"] == b["room_id"]), None)
        enriched.append({
            **b,
            "room_name": room["name"] if room else "ไม่ทราบห้อง",
        })

    return templates.TemplateResponse(
        "bookings.html",
        {"request": request, "bookings": enriched}
    )
