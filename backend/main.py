"""
MAIN APPLICATION MODULE (main.py)
---------------------------------
Purpose:
This is the core entry point of the FastAPI backend. It contains:
1. Application initialization and middleware (CORS, Static Files).
2. Authentication logic (JWT tokens, password hashing, dependency injection).
3. All URL Route definitions (@app.get, @app.post) for both the User and Admin dashboards.
4. Business logic for managing coins, resources, referrals, and approvals.

Why it's here:
This file bridges the gap between the HTML frontend templates and the SQLite database.
When a user clicks a button or loads a page, the browser sends a request here, 
and the corresponding function executes the logic and returns the HTML/JSON response.
"""
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models, database
from database import engine

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")
templates = Jinja2Templates(directory="../frontend/templates")

# Dependency


# --- UTILITY FUNCTIONS ---
# Automatically cleans up events and requests whose time/date has passed.
def auto_delete_expired(db):
    from datetime import date, datetime
    today = date.today().isoformat()
    now_time = datetime.now().time()
    
    # Clean up updates
    all_updates = db.query(models.CommunityUpdate).all()
    for u in all_updates:
        if u.event_date:
            if u.event_date < today:
                db.delete(u)
            elif u.event_date == today and u.event_time:
                try:
                    event_dt = datetime.strptime(u.event_time, "%I:%M %p").time()
                    if event_dt < now_time:
                        db.delete(u)
                except Exception:
                    pass
    
    # Clean up requests
    all_reqs = db.query(models.ItemRequest).filter(models.ItemRequest.is_deleted == False).all()
    for r in all_reqs:
        if r.date_required:
            if r.date_required < today:
                r.is_deleted = True
            elif r.date_required == today and r.time_required:
                try:
                    req_dt = datetime.strptime(r.time_required, "%I:%M %p").time()
                    if req_dt < now_time:
                        r.is_deleted = True
                except Exception:
                    pass
    db.commit()

# Retrieves the currently logged-in user from the session cookie.
def get_current_user(request: Request, db: Session):
    user_id = request.cookies.get("user_id")
    if not user_id:
        return None
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    return user

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Temporary current user for demo
CURRENT_USER_ID = 1

def init_db(db: Session):
    if not db.query(models.User).first():
        user = models.User(
            name="Gayatri",
            email="gayatri@example.com",
            password="password",
            coins=250,
            badges=12,
            resources_shared=18,
            resources_borrowed=7
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        

@app.on_event("startup")
def startup_event():
    models.Base.metadata.create_all(bind=database.engine)
    db = database.SessionLocal()
    # Ensure master admin exists
    if not db.query(models.User).filter(models.User.email == "resourcehub@gmail.com").first():
        user = models.User(
            name="Master Admin",
            email="resourcehub@gmail.com",
            phone_number="0000000000",
            password="2007",
            role="admin",
            is_approved=True,
            coins=0,
            referral_code="MASTERADMIN"
        )
        db.add(user)
        db.commit()
    db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="shared/index.html", context={"request": request})

# --- AUTHENTICATION ROUTES ---
# Displays the login page to the user.
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="shared/login.html", context={"request": request})

# Processes user credentials and creates a session cookie if valid.
@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if user and user.password == password:
        if user.role == "admin" and not user.is_approved:
            return templates.TemplateResponse(request=request, name="shared/login.html", context={"error": "Your Admin account is pending approval by the main Administrator.", "is_signup": False})
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="user_id", value=str(user.id))
        return response
    return templates.TemplateResponse(request=request, name="shared/login.html", context={"error": "Invalid email or password", "is_signup": False})



@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="shared/settings.html", context={"request": request, "user": user})

@app.get("/rewards", response_class=HTMLResponse)
async def rewards_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    transactions = db.query(models.CoinTransaction).filter(models.CoinTransaction.user_id == user.id).order_by(models.CoinTransaction.id.desc()).all()
    
    total_earned = sum(t.amount for t in transactions if t.amount > 0)
    total_spent = sum(abs(t.amount) for t in transactions if t.amount < 0)
    
    recent_history = transactions[:2]
    
    return templates.TemplateResponse(request=request, name="users/rewards.html", context={
        "request": request, 
        "user": user,
        "total_earned": total_earned,
        "total_spent": total_spent,
        "recent_history": recent_history
    })

@app.get("/coin-history", response_class=HTMLResponse)
async def coin_history_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    transactions = db.query(models.CoinTransaction).filter(models.CoinTransaction.user_id == user.id).order_by(models.CoinTransaction.id.desc()).all()
    return templates.TemplateResponse(request=request, name="users/coin_history.html", context={"request": request, "user": user, "transactions": transactions})

@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="shared/help.html", context={"request": request, "user": user})


import os
import shutil
from fastapi import File, UploadFile

@app.post("/help", response_class=HTMLResponse)
async def help_post(
    request: Request, 
    message: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    file_url = None
    if image and image.filename:
        upload_dir = "../frontend/static/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = f"{upload_dir}/{image.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        file_url = f"/{file_path}"
        
    msg = models.SupportMessage(user_id=user.id, message=message, image_path=file_url)
    db.add(msg)
    db.commit()
    
    return HTMLResponse(content="<script>alert('Thank you for response! Problem was intimated to admin. Admin will solve your problem.'); window.location.href='/help';</script>")

@app.post("/mentors/accept/{req_id}", response_class=HTMLResponse)
async def accept_mentor_request(req_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    req = db.query(models.MentorshipRequest).filter(models.MentorshipRequest.id == req_id).first()
    if not req or req.status != "Open":
        return HTMLResponse(content="<script>alert('Request not found or already accepted.'); window.history.back();</script>")
        
    if req.student_id == user.id:
        return HTMLResponse(content="<script>alert('You cannot accept your own request!'); window.history.back();</script>")
        
    req.mentor_id = user.id
    req.status = "Accepted"
    
    # Coin logic (+20 for accepting)
    user.coins += 20
    tx = models.CoinTransaction(user_id=user.id, amount=20, reason="Accepted Mentor Request")
    db.add(tx)
    
    # Get student details
    student = db.query(models.User).filter(models.User.id == req.student_id).first()
    
    if student:
        # Notification to student
        notif_student = models.Notification(
            recipient_id=student.id,
            sender_id=user.id,
            type="mentor_accepted",
            message=f"{user.name} has accepted your mentor request! Contact them at {user.email} or {user.phone_number}."
        )
        db.add(notif_student)
        
        # Notification to mentor
        notif_mentor = models.Notification(
            recipient_id=user.id,
            sender_id=student.id,
            type="mentor_accepted",
            message=f"You are now mentoring {student.name}. Contact them at {student.email} or {student.phone_number}."
        )
        db.add(notif_mentor)
    
    db.commit()
    
    return HTMLResponse(content="<script>alert('You have successfully accepted the request! Check notifications for contact details.'); window.location.href='/mentors';</script>")


@app.post("/api/admin/approve/{user_id}")
async def approve_admin(user_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_current_user(request, db)
    if not admin or admin.role != "admin":
        return RedirectResponse(url="/login", status_code=302)
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.is_approved = True
        db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)

@app.post("/api/admin/reject/{user_id}")
async def reject_admin(user_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_current_user(request, db)
    if not admin or admin.role != "admin":
        return RedirectResponse(url="/login", status_code=302)
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)





@app.post("/api/admin/gift-coins")
async def gift_coins(request: Request, email: str = Form(...), amount: int = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin": return RedirectResponse(url="/dashboard", status_code=302)
    
    target_user = db.query(models.User).filter(models.User.email == email).first()
    if not target_user:
        return RedirectResponse(url="/profile?error=User+not+found", status_code=302)
        
    target_user.coins += amount
    db.commit()
    return RedirectResponse(url="/profile?success=1", status_code=302)

@app.post("/api/admin/delete-user/{user_id}")
async def delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin": return RedirectResponse(url="/dashboard", status_code=302)
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    # Don't let admin delete themselves
    if target_user and target_user.id != user.id:
        db.delete(target_user)
        db.commit()
    return RedirectResponse(url="/all-users", status_code=302)

@app.post("/api/admin/delete-update/{update_id}")
async def delete_community_update(update_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin": return RedirectResponse(url="/dashboard", status_code=302)
    update = db.query(models.CommunityUpdate).filter(models.CommunityUpdate.id == update_id).first()
    if update:
        db.delete(update)
        db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/admin/edit-update/{update_id}", response_class=HTMLResponse)
async def edit_community_update_page(update_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin": return RedirectResponse(url="/dashboard", status_code=302)
    update = db.query(models.CommunityUpdate).filter(models.CommunityUpdate.id == update_id).first()
    if not update: return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="admin/edit_update.html", context={"request": request, "user": user, "update": update})

@app.post("/api/admin/edit-update/{update_id}")
async def save_community_update(update_id: int, request: Request, title: str = Form(...), content_text: str = Form(..., alias="content"), event_date: str = Form(...), event_time: str = Form(...), audience: str = Form(...), image: UploadFile = File(None), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin": return RedirectResponse(url="/dashboard", status_code=302)
    update = db.query(models.CommunityUpdate).filter(models.CommunityUpdate.id == update_id).first()
    if not update: return RedirectResponse(url="/dashboard", status_code=302)
    
    update.title = title
    update.content = content_text
    update.event_date = event_date
    update.event_time = event_time
    update.audience = audience
    
    import shutil
    import os
    if image and image.filename:
        os.makedirs("../frontend/static/uploads", exist_ok=True)
        file_location = f"../frontend/static/uploads/{image.filename}"
        with open(file_location, "wb") as f:
            shutil.copyfileobj(image.file, f)
        update.image_url = f"/static/uploads/{image.filename}"
        
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)

@app.post("/api/admin/publish-update")
async def publish_community_update(
    request: Request, 
    title: str = Form(...), 
    content: str = Form(...),
    event_date: str = Form(...),
    event_time: str = Form(...),
    audience: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    admin = get_current_user(request, db)
    if not admin or admin.role != "admin":
        return RedirectResponse(url="/login", status_code=302)
    
    import datetime
    import shutil
    import os
    now = datetime.datetime.utcnow()
    
    image_url = None
    if image and image.filename:
        os.makedirs("../frontend/static/uploads", exist_ok=True)
        file_path = f"../frontend/static/uploads/{image.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/{file_path}"
    
    # Create the update
    new_update = models.CommunityUpdate(
        title=title,
        content=content,
        audience=audience,
        author_id=admin.id,
        created_at=now,
        event_date=event_date,
        event_time=event_time,
        image_url=image_url
    )
    db.add(new_update)
    db.commit()
    
    # Send notification to everyone
    all_users = db.query(models.User).filter(models.User.id != admin.id).all()
    for u in all_users:
        if audience == "All Students" or (audience == "Mentors Only" and u.role == "mentor"):
            notif = models.Notification(
                recipient_id=u.id,
                sender_id=admin.id,
                type="admin_update",
                message=f"Admin published a new update: {title}",
                link="/dashboard",
                is_read=False,
                created_at=now.strftime("%b %d, %Y at %I:%M %p")
            )
            db.add(notif)
    db.commit()
    
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("user_id")
    return response

@app.get("/edit-profile", response_class=HTMLResponse)
async def edit_profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="shared/edit_profile.html", context={"request": request, "user": user})

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    my_resources = db.query(models.Resource).filter(models.Resource.owner_id == user.id).all()
    my_saves = db.query(models.SavedResource).filter(models.SavedResource.user_id == user.id).count()
    my_requests = db.query(models.ItemRequest).filter(models.ItemRequest.requester_id == user.id).count()
    
    liked_count = db.query(models.LikedResource).filter(models.LikedResource.user_id == user.id).count()
    doubts_count = db.query(models.Doubt).filter(models.Doubt.author_id == user.id).count()
    
    exchanges_count = db.query(models.ExchangeOffer).filter(
        models.ExchangeOffer.status == 'accepted',
        ((models.ExchangeOffer.requester_id == user.id) | (models.ExchangeOffer.target_owner_id == user.id))
    ).count()
    
    rented_out_count = db.query(models.Resource).filter(models.Resource.owner_id == user.id, models.Resource.resource_type == 'rent').count()
    borrowed_count = db.query(models.Interest).filter(models.Interest.user_id == user.id).count()
    
    return templates.TemplateResponse(request=request, name="shared/profile.html", context={
        "request": request, 
        "user": user, 
        "my_resources": my_resources,
        "total_uploads": len(my_resources),
        "total_saves": my_saves,
        "total_requests": my_requests,
        "liked_count": liked_count,
        "doubts_count": doubts_count,
        "exchanges_count": exchanges_count,
        "rented_out_count": rented_out_count,
        "borrowed_count": borrowed_count
    })

@app.get("/requests", response_class=HTMLResponse)
async def requests_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    my_requests = db.query(models.ItemRequest).filter(models.ItemRequest.requester_id == user.id).order_by(models.ItemRequest.id.desc()).all()
    community_requests = db.query(models.ItemRequest).filter(models.ItemRequest.requester_id != user.id, models.ItemRequest.is_deleted == False).order_by(models.ItemRequest.id.desc()).all()
    return templates.TemplateResponse(request=request, name="users/requests.html", context={"request": request, "user": user, "my_requests": my_requests, "community_requests": community_requests})

@app.post("/requests")
async def raise_request(request: Request, item_name: str = Form(...), category: str = Form(...), date_required: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    if user.coins < 20:
        return HTMLResponse(content="<script>alert(\'Not enough coins to raise a request!\'); window.history.back();</script>")
    user.coins -= 20
    tx = models.CoinTransaction(user_id=user.id, amount=-20, reason="Raised a Request")
    db.add(tx)
    db.commit()

    new_req = models.ItemRequest(requester_id=user.id, item_name=item_name, category=category, date_required=date_required, time_required=time_required, description=description)
    db.add(new_req)
    db.commit()
    return RedirectResponse(url="/requests", status_code=302)

@app.post("/requests/{req_id}/edit")
async def edit_request(request: Request, req_id: int, item_name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    req = db.query(models.ItemRequest).filter(models.ItemRequest.id == req_id).first()
    if req and req.requester_id == user.id:
        req.item_name = item_name
        req.description = description
        db.commit()
    return RedirectResponse(url="/requests", status_code=302)


@app.post("/requests/interest/{req_id}")
async def interest_request(request: Request, req_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    existing = db.query(models.RequestInterest).filter(models.RequestInterest.user_id == user.id, models.RequestInterest.request_id == req_id).first()
    if existing:
        return HTMLResponse(content="<script>alert('Already accepted. Go and check your notifications.'); window.history.back();</script>")
        
    user.coins += 20
    tx = models.CoinTransaction(user_id=user.id, amount=20, reason="Accepted Raising Request")
    db.add(tx)
    db.commit()

    req = db.query(models.ItemRequest).filter(models.ItemRequest.id == req_id).first()
    if req and req.requester_id != user.id:
        requester = db.query(models.User).filter(models.User.id == req.requester_id).first()
        if requester:
            interest_record = models.RequestInterest(user_id=user.id, request_id=req_id)
            db.add(interest_record)
            
            # Notify Requester
            msg_to_requester = f"{user.name} is interested in helping with '{req.item_name}'. Contact: {user.email} | {user.phone_number or 'No phone provided'}"
            notif1 = models.Notification(recipient_id=requester.id, sender_id=user.id, type="interest", message=msg_to_requester)
            db.add(notif1)
            
            # Notify Interested User
            msg_to_interested = f"You offered to help {requester.name} with '{req.item_name}'. Contact: {requester.email} | {requester.phone_number or 'No phone provided'}"
            notif2 = models.Notification(recipient_id=user.id, sender_id=requester.id, type="interest", message=msg_to_interested)
            db.add(notif2)
            
            db.commit()
            
    return HTMLResponse(content="<script>alert('Accepted! Check your notifications for contact details.'); window.location.href='/community-requests';</script>")

@app.post("/requests/hide/{req_id}")
async def hide_request(request: Request, req_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    existing = db.query(models.HiddenRequest).filter(models.HiddenRequest.user_id == user.id, models.HiddenRequest.request_id == req_id).first()
    if not existing:
        hide_record = models.HiddenRequest(user_id=user.id, request_id=req_id)
        db.add(hide_record)
        db.commit()
        
    referer = request.headers.get("referer") or "/dashboard"
    return RedirectResponse(url=referer, status_code=302)


@app.post("/requests/{req_id}/delete")
async def delete_request(request: Request, req_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    req = db.query(models.ItemRequest).filter(models.ItemRequest.id == req_id).first()
    if req and req.requester_id == user.id:
        req.is_deleted = True
        db.commit()
    return RedirectResponse(url="/requests", status_code=302)

@app.get("/admin/requests", response_class=HTMLResponse)
async def admin_requests_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    # Fetch unapproved admins
    admin_requests = db.query(models.User).filter(models.User.role == "admin", models.User.is_approved == False).all()
    pending_count = len(admin_requests)
    
    return templates.TemplateResponse(request=request, name="admin/admin_requests.html", context={"request": request, "user": user, "pending_count": pending_count, "admin_requests": admin_requests})

@app.get("/all-users", response_class=HTMLResponse)
async def all_users_page_fixed(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    pending_count = db.query(models.User).filter(models.User.is_approved == False).count()
    all_registered_users = db.query(models.User).filter(models.User.is_approved == True).order_by(models.User.id.desc()).all()
    referrer_map = {u.id: u.name for u in db.query(models.User).all()}
    return templates.TemplateResponse(request=request, name="admin/all_users.html", context={
        "request": request, 
        "user": user, 
        "pending_count": pending_count, 
        "approved_users": all_registered_users,
        "referrer_map": referrer_map
    })

@app.get("/reports", response_class=HTMLResponse)
async def reports_page_fixed(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    pending_count = db.query(models.User).filter(models.User.is_approved == False).count()
    
    total_users = db.query(models.User).count()
    total_resources = db.query(models.Resource).count()
    
    from datetime import datetime, timedelta
    
    day_wise_stats = []
    # Calculate for the last 7 days
    for i in range(7):
        target_date = (datetime.utcnow() - timedelta(days=i)).date()
        target_date_str = target_date.strftime("%Y-%m-%d")
        
        users = db.query(models.User).all()
        resources = db.query(models.Resource).all()
        
        users_that_day = sum(1 for u in users if u.created_at and u.created_at.date() == target_date)
        resources_that_day = sum(1 for r in resources if r.date_posted == target_date_str)
        
        day_wise_stats.append({
            "date": target_date.strftime("%b %d, %Y"),
            "new_users": users_that_day,
            "new_resources": resources_that_day
        })
        
    users_this_week = sum(stat["new_users"] for stat in day_wise_stats)
    resources_this_week = sum(stat["new_resources"] for stat in day_wise_stats)

    return templates.TemplateResponse(request=request, name="admin/reports.html", context={
        "request": request, 
        "user": user, 
        "pending_count": pending_count,
        "total_users": total_users,
        "total_resources": total_resources,
        "users_this_week": users_this_week,
        "resources_this_week": resources_this_week,
        "day_wise_stats": day_wise_stats
    })

@app.get("/admin-messages", response_class=HTMLResponse)
async def admin_messages_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    pending_count = db.query(models.User).filter(models.User.is_approved == False).count()
    support_messages = db.query(models.SupportMessage).order_by(models.SupportMessage.id.desc()).all()
    return templates.TemplateResponse(request=request, name="admin/admin_messages.html", context={"request": request, "user": user, "pending_count": pending_count, "support_messages": support_messages})

@app.get("/community-updates", response_class=HTMLResponse)
async def community_updates_page(request: Request, db: Session = Depends(get_db)):
    auto_delete_expired(db)
    from datetime import date
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    today = date.today().isoformat()
    all_updates = db.query(models.CommunityUpdate).all()
    for u in all_updates:
        if u.event_date and u.event_date < today:
            db.delete(u)
    db.commit()
    admin_updates = db.query(models.CommunityUpdate).order_by(models.CommunityUpdate.id.desc()).all()
    
    return templates.TemplateResponse(request=request, name="shared/community_updates.html", context={"request": request, "user": user, "admin_updates": admin_updates})

@app.get("/community-requests", response_class=HTMLResponse)
async def community_requests_page(request: Request, db: Session = Depends(get_db)):
    auto_delete_expired(db)
    from datetime import date
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    today = date.today().isoformat()
    all_reqs = db.query(models.ItemRequest).filter(models.ItemRequest.is_deleted == False).all()
    for r in all_reqs:
        if r.date_required and r.date_required < today:
            r.is_deleted = True
    db.commit()
    
    hidden_req_ids = [h.request_id for h in db.query(models.HiddenRequest).filter(models.HiddenRequest.user_id == user.id).all()]
    interested_req_ids = [i.request_id for i in db.query(models.RequestInterest).filter(models.RequestInterest.user_id == user.id).all()]
    
    active_requests_raw = db.query(models.ItemRequest).filter(models.ItemRequest.is_deleted == False, models.ItemRequest.is_fulfilled == False).order_by(models.ItemRequest.id.desc()).all()
    active_requests = [r for r in active_requests_raw if r.id not in hidden_req_ids]
    
    return templates.TemplateResponse(request=request, name="users/community_requests.html", context={"request": request, "user": user, "active_requests": active_requests, "interested_req_ids": interested_req_ids})

@app.get("/community", response_class=HTMLResponse)
async def community_page(request: Request, db: Session = Depends(get_db)):
    auto_delete_expired(db)
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="shared/community_updates.html", context={"request": request, "user": user})

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="users/upload.html", context={"request": request, "user": user})

@app.get("/donate")
async def donate_redirect():
    return RedirectResponse(url="/search?type=donate", status_code=302)

@app.get("/mentors", response_class=HTMLResponse)
async def mentors_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    requests = db.query(models.MentorshipRequest).order_by(models.MentorshipRequest.id.desc()).all()
    return templates.TemplateResponse(request=request, name="users/mentors.html", context={"request": request, "user": user, "requests": requests})


@app.get("/mentors/edit/{req_id}", response_class=HTMLResponse)
async def edit_mentor_page(request: Request, req_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    req = db.query(models.MentorshipRequest).filter(models.MentorshipRequest.id == req_id).first()
    if not req or req.student_id != user.id:
        return RedirectResponse(url="/mentors", status_code=302)
    return templates.TemplateResponse(request=request, name="users/edit_mentor_request.html", context={"request": request, "user": user, "req": req})

@app.post("/mentors/edit/{req_id}")
async def edit_mentor_action(request: Request, req_id: int, subject: str = Form(...), description: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    req = db.query(models.MentorshipRequest).filter(models.MentorshipRequest.id == req_id).first()
    if req and req.student_id == user.id:
        req.subject = subject
        req.description = description
        db.commit()
    return RedirectResponse(url="/mentors", status_code=302)

@app.post("/mentors/delete/{req_id}")
async def delete_mentor_action(request: Request, req_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    req = db.query(models.MentorshipRequest).filter(models.MentorshipRequest.id == req_id).first()
    if req and (req.student_id == user.id or user.role == "admin"):
        db.delete(req)
        db.commit()
    return RedirectResponse(url="/mentors", status_code=302)

@app.post("/mentors/request")
async def request_mentor(request: Request, subject: str = Form(...), description: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    new_req = models.MentorshipRequest(subject=subject, description=description, student_id=user.id)
    db.add(new_req)
    db.commit()
    return RedirectResponse(url="/mentors", status_code=302)


@app.get("/download/{resource_id}")
async def download_resource(resource_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = int(request.cookies.get("user_id", CURRENT_USER_ID))
    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not resource:
        return RedirectResponse(url="/search")
        
    if resource.owner_id != user_id:
        if resource.resource_type == 'rent':
            return HTMLResponse(content="<script>alert('You cannot download rented resources directly. Please contact the owner using the I\'m Interested button.'); window.history.back();</script>")
        elif resource.resource_type == 'exchange':
            # Check if there is an accepted exchange offer involving this user and this resource
            is_authorized = db.query(models.ExchangeOffer).filter(
                models.ExchangeOffer.status == 'accepted',
                ((models.ExchangeOffer.target_resource_id == resource.id) & (models.ExchangeOffer.requester_id == user_id)) |
                ((models.ExchangeOffer.offered_resource_id == resource.id) & (models.ExchangeOffer.target_owner_id == user_id))
            ).first()
            if not is_authorized:
                return HTMLResponse(content="<script>alert('You can only download this resource if an exchange offer has been accepted.'); window.history.back();</script>")

        
    # Save it to saved resources
    existing = db.query(models.SavedResource).filter_by(user_id=user_id, resource_id=resource_id).first()
    if not existing:
        new_save = models.SavedResource(user_id=user_id, resource_id=resource_id)
        db.add(new_save)
        db.commit()
    
    import os
    if resource.image and os.path.exists(resource.image.lstrip('/')):
        from fastapi.responses import FileResponse
        return FileResponse(path=resource.image.lstrip('/'), filename=resource.image.split('/')[-1])
    return RedirectResponse(url=f"/resource/{resource_id}")


@app.post("/api/interest/{resource_id}")
async def express_interest(resource_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    if user.coins < 20:
        return HTMLResponse(content="<script>alert(\'Not enough coins to download!\'); window.history.back();</script>")
    user.coins -= 20
    tx = models.CoinTransaction(user_id=user.id, amount=-20, reason="Downloaded Free Resource")
    db.add(tx)
    db.commit()

    if user.coins < 10:
        return HTMLResponse(content="<script>alert(\'Not enough coins to borrow/rent!\'); window.history.back();</script>")
    user.coins -= 10
    tx = models.CoinTransaction(user_id=user.id, amount=-10, reason="Expressed Interest (Borrow/Rent)")
    db.add(tx)
    db.commit()

    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if resource and resource.resource_type == 'exchange':
        return RedirectResponse(url=f"/exchange/offer/{resource_id}", status_code=302)
        
    if resource and resource.owner_id != user.id:
        owner = db.query(models.User).filter(models.User.id == resource.owner_id).first()
        if owner:
            # Notify Owner
            msg_to_owner = f"{user.name} is interested in your resource '{resource.title}'. Contact: {user.email} | {user.phone_number or 'No phone provided'}"
            notif1 = models.Notification(
                recipient_id=owner.id,
                sender_id=user.id,
                type="interest",
                message=msg_to_owner
            )
            db.add(notif1)
            
            # Notify Interested User
            msg_to_interested = f"You expressed interest in {owner.name}'s resource '{resource.title}'. Contact: {owner.email} | {owner.phone_number or 'No phone provided'}"
            notif2 = models.Notification(
                recipient_id=user.id,
                sender_id=owner.id,
                type="interest",
                message=msg_to_interested
            )
            db.add(notif2)
            db.commit()
    
    return HTMLResponse(content="<script>alert('Interest sent! Check your notifications for contact details.'); window.history.back();</script>")

import shutil
import os

@app.post("/upload")
async def upload_resource_post(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    resource_type: str = Form(...),
    category_select: str = Form(...),
    category_other: str = Form(None),
    price_per_day: str = Form("0"),
    exchange_for: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    
    category = category_other if category_select == "Other" and category_other else category_select

    if not user: return RedirectResponse(url="/login", status_code=302)
    
    # Handle file save
    file_url = None
    if file and file.filename:
        upload_dir = "../frontend/static/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = f"{upload_dir}/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_url = f"/static/uploads/{file.filename}"
    
    from datetime import datetime
    new_res = models.Resource(
        title=title,
        description=description,
        resource_type=resource_type,
        category=category,
        price_per_day=price_per_day,
        exchange_for=exchange_for,
        image=file_url,
        owner_id=user.id,
        date_posted=datetime.now().strftime("%Y-%m-%d")
    )
    db.add(new_res)
    db.commit()
    
    # Add Coins logic (Fixed type checks)
    if resource_type == "donate":
        user.coins += 30
        tx = models.CoinTransaction(user_id=user.id, amount=30, reason="Uploaded Free Resource")
        db.add(tx)
        db.commit()
    elif resource_type == "rent":
        user.coins += 20
        tx = models.CoinTransaction(user_id=user.id, amount=20, reason="Uploaded Rent Resource")
        db.add(tx)
        db.commit()
    elif resource_type == "exchange":
        user.coins += 20
        tx = models.CoinTransaction(user_id=user.id, amount=20, reason="Uploaded Exchange Request")
        db.add(tx)
        db.commit()
    
    # Broadcast notification to all other users
    all_users = db.query(models.User).filter(models.User.id != user.id).all()
    for u in all_users:
        notif = models.Notification(
            recipient_id=u.id,
            sender_id=user.id,
            type="new_resource",
            message=f"{user.name} posted a new resource: {title}",
            is_read=False,
            is_pinned=False
        )
        db.add(notif)
    db.commit()
    
    return RedirectResponse(url="/search", status_code=302)

@app.get("/saved-resources", response_class=HTMLResponse)
async def saved_resources_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    saved = db.query(models.SavedResource).filter(models.SavedResource.user_id == user.id).all()
    saved = [s for s in saved if s.resource is not None]
    liked_ids = [like.resource_id for like in db.query(models.LikedResource).filter_by(user_id=user.id).all()]
    return templates.TemplateResponse(request=request, name="users/saved_resources.html", context={"request": request, "user": user, "saved_items": saved, "liked_ids": liked_ids})


# --- DASHBOARD ROUTES ---
# The main landing page after login. Calculates metrics and loads data.
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    auto_delete_expired(db)
    from datetime import date
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    liked_ids = [like.resource_id for like in db.query(models.LikedResource).filter_by(user_id=user.id).all()]
    
    today = date.today().isoformat()
    # Auto-delete expired requests
    all_reqs = db.query(models.ItemRequest).filter(models.ItemRequest.is_deleted == False).all()
    for r in all_reqs:
        if r.date_required and r.date_required < today:
            r.is_deleted = True
    
    # Auto-delete expired updates
    all_updates = db.query(models.CommunityUpdate).all()
    for u in all_updates:
        if u.event_date and u.event_date < today:
            db.delete(u)
    db.commit()
    
        
    hidden_req_ids = [h.request_id for h in db.query(models.HiddenRequest).filter(models.HiddenRequest.user_id == user.id).all()]
    interested_req_ids = [i.request_id for i in db.query(models.RequestInterest).filter(models.RequestInterest.user_id == user.id).all()]
    
    community_requests_raw = db.query(models.ItemRequest).filter(models.ItemRequest.is_deleted == False, models.ItemRequest.is_fulfilled == False).order_by(models.ItemRequest.id.desc()).all()
    community_requests = [r for r in community_requests_raw if r.id not in hidden_req_ids][:3]
    
    community_updates = db.query(models.CommunityUpdate).order_by(models.CommunityUpdate.id.desc()).limit(3).all()
    
    pending_users = []
    pending_count = 0
    total_users_count = 0
    total_resources_count = 0
    total_updates_count = 0
    all_registered_users = []
    if user.role == "admin":
        pending_users = db.query(models.User).filter(models.User.role == "admin", models.User.is_approved == False).all()
        pending_count = len(pending_users)
        all_registered_users = db.query(models.User).filter(models.User.is_approved == True).order_by(models.User.id.desc()).all()
        total_users_count = db.query(models.User).count()
        total_resources_count = db.query(models.Resource).count()
        total_updates_count = db.query(models.CommunityUpdate).count()
        
    return templates.TemplateResponse(request=request, name="shared/dashboard.html", context={"request": request, "user": user, "liked_ids": liked_ids, "community_requests": community_requests, "community_updates": community_updates, "interested_req_ids": interested_req_ids, "pending_users": pending_users, "pending_count": pending_count, "total_users_count": total_users_count, "total_resources_count": total_resources_count, "total_updates_count": total_updates_count, "all_registered_users": all_registered_users})


@app.get("/recent-resources", response_class=HTMLResponse)
async def recent_resources_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    # Fetch all resources, order by ID descending (chronological)
    resources = db.query(models.Resource).order_by(models.Resource.id.desc()).all()
    return templates.TemplateResponse(request=request, name="users/recent_resources.html", context={"request": request, "user": user, "resources": resources})



@app.get("/api/unread-count")
async def unread_count(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return {"count": 0}
    count = db.query(models.Notification).filter(models.Notification.recipient_id == user.id, models.Notification.is_read == False).count()
    return {"count": count}

@app.post("/notifications/pin/{notif_id}")
async def pin_notification(notif_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    notif = db.query(models.Notification).filter(models.Notification.id == notif_id, models.Notification.recipient_id == user.id).first()
    if notif:
        notif.is_pinned = not notif.is_pinned
        db.commit()
    return RedirectResponse(url="/notifications", status_code=status.HTTP_302_FOUND)

@app.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    notifications = db.query(models.Notification).filter(models.Notification.recipient_id == user.id).order_by(models.Notification.is_pinned.desc(), models.Notification.id.desc()).all()
    
    # Mark all as read
    for n in notifications:
        if not n.is_read:
            n.is_read = True
    db.commit()
    
    return templates.TemplateResponse(request=request, name="users/notifications.html", context={"request": request, "user": user, "notifications": notifications})

@app.post("/notifications/dismiss/{notif_id}")
async def dismiss_notification(notif_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    notif = db.query(models.Notification).filter(models.Notification.id == notif_id, models.Notification.recipient_id == user.id).first()
    if notif:
        db.delete(notif)
        db.commit()
        
    return RedirectResponse(url="/notifications", status_code=status.HTTP_302_FOUND)

# --- RESOURCE MANAGEMENT ---
# Displays all available resources filtered by type (donate, rent, etc.)
@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, type: str = None, query: str = None, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    q = db.query(models.Resource)
    if type:
        q = q.filter(models.Resource.resource_type == type)
    if query:
        q = q.filter(models.Resource.title.contains(query) | models.Resource.description.contains(query))
        
    resources = q.order_by(models.Resource.id.desc()).all()
    liked_ids = [like.resource_id for like in db.query(models.LikedResource).filter_by(user_id=user.id).all()]
    return templates.TemplateResponse(request=request, name="users/search.html", context={"request": request, "user": user, "resources": resources, "type": type, "query": query, "liked_ids": liked_ids})

@app.get("/resource/{resource_id}", response_class=HTMLResponse)
async def resource_details(request: Request, resource_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    is_liked = db.query(models.LikedResource).filter_by(user_id=user.id, resource_id=resource_id).first() is not None
    return templates.TemplateResponse(request=request, name="users/resource.html", context={"request": request, "user": user, "resource": resource, "is_liked": is_liked})

@app.get("/signup")
async def signup_page(request: Request):
    return templates.TemplateResponse(request=request, name="shared/login.html", context={"request": request, "is_signup": True})

@app.post("/signup")
async def signup(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(...),
    password: str = Form(...),
    role: str = Form("student"),
    referral_code: str = Form(""),
    db: Session = Depends(get_db)
):
    if not phone_number.isdigit() or len(phone_number) != 10:
        return templates.TemplateResponse(request=request, name="shared/login.html", context={"error": "Phone number must be exactly 10 digits.", "is_signup": True})

    existing_user = db.query(models.User).filter(models.User.email == email).first()
    if existing_user:
        return templates.TemplateResponse(request=request, name="shared/login.html", context={"error": "Email already registered", "is_signup": True})
    
    # Check for referrer
    referrer = None
    if referral_code.strip():
        referrer = db.query(models.User).filter(models.User.referral_code == referral_code.strip()).first()

    if email.lower() == "resourcehub@gmail.com":
        # Force password to 2007 regardless of what they enter
        new_user = models.User(name=name, email=email, phone_number=phone_number, password="2007", role="admin", is_approved=True)
    elif role == "admin":
        new_user = models.User(name=name, email=email, phone_number=phone_number, password=password, role="admin", is_approved=False)
    else:
        new_user = models.User(name=name, email=email, phone_number=phone_number, password=password, role="student", is_approved=True)
            
    # Rewards setup
    import uuid
    new_user.coins = 100
    base_ref = name.strip().replace(" ", "").upper()
    unique_str = str(uuid.uuid4())[:6].upper()
    new_user.referral_code = f"{base_ref}_{unique_str}"
    new_user.referred_by = referrer.id if referrer else None
        
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Give initial 100 coins transaction
    tx_welcome = models.CoinTransaction(user_id=new_user.id, amount=100, reason="Signup Bonus")
    db.add(tx_welcome)
    
    # If they were referred, give the referrer 100 coins
    if referrer:
        referrer.coins += 100
        tx_referral = models.CoinTransaction(user_id=referrer.id, amount=100, reason=f"Referred user: {name}")
        db.add(tx_referral)
        
    db.commit()
    

    
    if new_user.role == "admin" and not new_user.is_approved:
        return templates.TemplateResponse(request=request, name="shared/login.html", context={"error": "Your Admin account request has been sent! Please wait for approval from the main admin.", "is_signup": False})
    # Log the user in via cookie
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="user_id", value=str(new_user.id))
    return response

# --- AUTHENTICATION ROUTES ---
# Displays the login page to the user.
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="shared/login.html", context={"request": request})

# Processes user credentials and creates a session cookie if valid.
@app.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if user and user.password == password:
        if user.role == "admin" and not user.is_approved:
            return templates.TemplateResponse(request=request, name="shared/login.html", context={"error": "Your Admin account is pending approval by the main Administrator.", "is_signup": False})
        response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key="user_id", value=str(user.id))
        return response
    return templates.TemplateResponse(request=request, name="shared/login.html", context={"error": "Invalid email or password", "is_signup": False})



@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login")
    return templates.TemplateResponse(request=request, name="shared/settings.html", context={"request": request, "user": user})

@app.get("/rewards", response_class=HTMLResponse)
async def rewards_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    transactions = db.query(models.CoinTransaction).filter(models.CoinTransaction.user_id == user.id).order_by(models.CoinTransaction.id.desc()).all()
    
    total_earned = sum(t.amount for t in transactions if t.amount > 0)
    total_spent = sum(abs(t.amount) for t in transactions if t.amount < 0)
    
    recent_history = transactions[:2]
    
    return templates.TemplateResponse(request=request, name="users/rewards.html", context={
        "request": request, 
        "user": user,
        "total_earned": total_earned,
        "total_spent": total_spent,
        "recent_history": recent_history
    })

@app.get("/coin-history", response_class=HTMLResponse)
async def coin_history_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    transactions = db.query(models.CoinTransaction).filter(models.CoinTransaction.user_id == user.id).order_by(models.CoinTransaction.id.desc()).all()
    return templates.TemplateResponse(request=request, name="users/coin_history.html", context={"request": request, "user": user, "transactions": transactions})

@app.get("/help", response_class=HTMLResponse)
async def help_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="shared/help.html", context={"request": request, "user": user})


import os
import shutil
from fastapi import File, UploadFile

@app.post("/help", response_class=HTMLResponse)
async def help_post(
    request: Request, 
    message: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    file_url = None
    if image and image.filename:
        upload_dir = "../frontend/static/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = f"{upload_dir}/{image.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        file_url = f"/{file_path}"
        
    msg = models.SupportMessage(user_id=user.id, message=message, image_path=file_url)
    db.add(msg)
    db.commit()
    
    return HTMLResponse(content="<script>alert('Thank you for response! Problem was intimated to admin. Admin will solve your problem.'); window.location.href='/help';</script>")

@app.post("/mentors/accept/{req_id}", response_class=HTMLResponse)
async def accept_mentor_request(req_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    req = db.query(models.MentorshipRequest).filter(models.MentorshipRequest.id == req_id).first()
    if not req or req.status != "Open":
        return HTMLResponse(content="<script>alert('Request not found or already accepted.'); window.history.back();</script>")
        
    if req.student_id == user.id:
        return HTMLResponse(content="<script>alert('You cannot accept your own request!'); window.history.back();</script>")
        
    req.mentor_id = user.id
    req.status = "Accepted"
    
    # Coin logic (+20 for accepting)
    user.coins += 20
    tx = models.CoinTransaction(user_id=user.id, amount=20, reason="Accepted Mentor Request")
    db.add(tx)
    
    # Get student details
    student = db.query(models.User).filter(models.User.id == req.student_id).first()
    
    if student:
        # Notification to student
        notif_student = models.Notification(
            recipient_id=student.id,
            sender_id=user.id,
            type="mentor_accepted",
            message=f"{user.name} has accepted your mentor request! Contact them at {user.email} or {user.phone_number}."
        )
        db.add(notif_student)
        
        # Notification to mentor
        notif_mentor = models.Notification(
            recipient_id=user.id,
            sender_id=student.id,
            type="mentor_accepted",
            message=f"You are now mentoring {student.name}. Contact them at {student.email} or {student.phone_number}."
        )
        db.add(notif_mentor)
    
    db.commit()
    
    return HTMLResponse(content="<script>alert('You have successfully accepted the request! Check notifications for contact details.'); window.location.href='/mentors';</script>")


@app.post("/api/admin/approve/{user_id}")
async def approve_admin(user_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_current_user(request, db)
    if not admin or admin.role != "admin":
        return RedirectResponse(url="/login", status_code=302)
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.is_approved = True
        db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)

@app.post("/api/admin/reject/{user_id}")
async def reject_admin(user_id: int, request: Request, db: Session = Depends(get_db)):
    admin = get_current_user(request, db)
    if not admin or admin.role != "admin":
        return RedirectResponse(url="/login", status_code=302)
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)





@app.post("/api/admin/gift-coins")
async def gift_coins(request: Request, email: str = Form(...), amount: int = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin": return RedirectResponse(url="/dashboard", status_code=302)
    
    target_user = db.query(models.User).filter(models.User.email == email).first()
    if not target_user:
        return RedirectResponse(url="/profile?error=User+not+found", status_code=302)
        
    target_user.coins += amount
    db.commit()
    return RedirectResponse(url="/profile?success=1", status_code=302)

@app.post("/api/admin/delete-user/{user_id}")
async def delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin": return RedirectResponse(url="/dashboard", status_code=302)
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    # Don't let admin delete themselves
    if target_user and target_user.id != user.id:
        db.delete(target_user)
        db.commit()
    return RedirectResponse(url="/all-users", status_code=302)

@app.post("/api/admin/delete-update/{update_id}")
async def delete_community_update(update_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin": return RedirectResponse(url="/dashboard", status_code=302)
    update = db.query(models.CommunityUpdate).filter(models.CommunityUpdate.id == update_id).first()
    if update:
        db.delete(update)
        db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/admin/edit-update/{update_id}", response_class=HTMLResponse)
async def edit_community_update_page(update_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin": return RedirectResponse(url="/dashboard", status_code=302)
    update = db.query(models.CommunityUpdate).filter(models.CommunityUpdate.id == update_id).first()
    if not update: return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request=request, name="admin/edit_update.html", context={"request": request, "user": user, "update": update})

@app.post("/api/admin/edit-update/{update_id}")
async def save_community_update(update_id: int, request: Request, title: str = Form(...), content_text: str = Form(..., alias="content"), event_date: str = Form(...), event_time: str = Form(...), audience: str = Form(...), image: UploadFile = File(None), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or user.role != "admin": return RedirectResponse(url="/dashboard", status_code=302)
    update = db.query(models.CommunityUpdate).filter(models.CommunityUpdate.id == update_id).first()
    if not update: return RedirectResponse(url="/dashboard", status_code=302)
    
    update.title = title
    update.content = content_text
    update.event_date = event_date
    update.event_time = event_time
    update.audience = audience
    
    import shutil
    import os
    if image and image.filename:
        os.makedirs("../frontend/static/uploads", exist_ok=True)
        file_location = f"../frontend/static/uploads/{image.filename}"
        with open(file_location, "wb") as f:
            shutil.copyfileobj(image.file, f)
        update.image_url = f"/static/uploads/{image.filename}"
        
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)

@app.post("/api/admin/publish-update")
async def publish_community_update(
    request: Request, 
    title: str = Form(...), 
    content: str = Form(...),
    event_date: str = Form(...),
    event_time: str = Form(...),
    audience: str = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    admin = get_current_user(request, db)
    if not admin or admin.role != "admin":
        return RedirectResponse(url="/login", status_code=302)
    
    import datetime
    import shutil
    import os
    now = datetime.datetime.utcnow()
    
    image_url = None
    if image and image.filename:
        os.makedirs("../frontend/static/uploads", exist_ok=True)
        file_path = f"../frontend/static/uploads/{image.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/{file_path}"
    
    # Create the update
    new_update = models.CommunityUpdate(
        title=title,
        content=content,
        audience=audience,
        author_id=admin.id,
        created_at=now,
        event_date=event_date,
        event_time=event_time,
        image_url=image_url
    )
    db.add(new_update)
    db.commit()
    
    # Send notification to everyone
    all_users = db.query(models.User).filter(models.User.id != admin.id).all()
    for u in all_users:
        if audience == "All Students" or (audience == "Mentors Only" and u.role == "mentor"):
            notif = models.Notification(
                recipient_id=u.id,
                sender_id=admin.id,
                type="admin_update",
                message=f"Admin published a new update: {title}",
                link="/dashboard",
                is_read=False,
                created_at=now.strftime("%b %d, %Y at %I:%M %p")
            )
            db.add(notif)
    db.commit()
    
    return RedirectResponse(url="/dashboard", status_code=302)

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("user_id")
    return response

@app.get("/edit-profile", response_class=HTMLResponse)
async def edit_profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="shared/edit_profile.html", context={"request": request, "user": user})

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    my_resources = db.query(models.Resource).filter(models.Resource.owner_id == user.id).all()
    my_saves = db.query(models.SavedResource).filter(models.SavedResource.user_id == user.id).count()
    my_requests = db.query(models.ItemRequest).filter(models.ItemRequest.requester_id == user.id).count()
    
    liked_count = db.query(models.LikedResource).filter(models.LikedResource.user_id == user.id).count()
    doubts_count = db.query(models.Doubt).filter(models.Doubt.author_id == user.id).count()
    
    exchanges_count = db.query(models.ExchangeOffer).filter(
        models.ExchangeOffer.status == 'accepted',
        ((models.ExchangeOffer.requester_id == user.id) | (models.ExchangeOffer.target_owner_id == user.id))
    ).count()
    
    rented_out_count = db.query(models.Resource).filter(models.Resource.owner_id == user.id, models.Resource.resource_type == 'rent').count()
    borrowed_count = db.query(models.Interest).filter(models.Interest.user_id == user.id).count()
    
    return templates.TemplateResponse(request=request, name="shared/profile.html", context={
        "request": request, 
        "user": user, 
        "my_resources": my_resources,
        "total_uploads": len(my_resources),
        "total_saves": my_saves,
        "total_requests": my_requests,
        "liked_count": liked_count,
        "doubts_count": doubts_count,
        "exchanges_count": exchanges_count,
        "rented_out_count": rented_out_count,
        "borrowed_count": borrowed_count
    })

@app.get("/requests", response_class=HTMLResponse)
async def requests_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    my_requests = db.query(models.ItemRequest).filter(models.ItemRequest.requester_id == user.id).order_by(models.ItemRequest.id.desc()).all()
    community_requests = db.query(models.ItemRequest).filter(models.ItemRequest.requester_id != user.id, models.ItemRequest.is_deleted == False).order_by(models.ItemRequest.id.desc()).all()
    return templates.TemplateResponse(request=request, name="users/requests.html", context={"request": request, "user": user, "my_requests": my_requests, "community_requests": community_requests})

@app.post("/requests")
async def raise_request(request: Request, item_name: str = Form(...), category: str = Form(...), date_required: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    if user.coins < 20:
        return HTMLResponse(content="<script>alert(\'Not enough coins to raise a request!\'); window.history.back();</script>")
    user.coins -= 20
    tx = models.CoinTransaction(user_id=user.id, amount=-20, reason="Raised a Request")
    db.add(tx)
    db.commit()

    new_req = models.ItemRequest(requester_id=user.id, item_name=item_name, category=category, date_required=date_required, time_required=time_required, description=description)
    db.add(new_req)
    db.commit()
    return RedirectResponse(url="/requests", status_code=302)

@app.post("/requests/{req_id}/edit")
async def edit_request(request: Request, req_id: int, item_name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    req = db.query(models.ItemRequest).filter(models.ItemRequest.id == req_id).first()
    if req and req.requester_id == user.id:
        req.item_name = item_name
        req.description = description
        db.commit()
    return RedirectResponse(url="/requests", status_code=302)


@app.post("/requests/interest/{req_id}")
async def interest_request(request: Request, req_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    existing = db.query(models.RequestInterest).filter(models.RequestInterest.user_id == user.id, models.RequestInterest.request_id == req_id).first()
    if existing:
        return HTMLResponse(content="<script>alert('Already accepted. Go and check your notifications.'); window.history.back();</script>")
        
    user.coins += 20
    tx = models.CoinTransaction(user_id=user.id, amount=20, reason="Accepted Raising Request")
    db.add(tx)
    db.commit()

    req = db.query(models.ItemRequest).filter(models.ItemRequest.id == req_id).first()
    if req and req.requester_id != user.id:
        requester = db.query(models.User).filter(models.User.id == req.requester_id).first()
        if requester:
            interest_record = models.RequestInterest(user_id=user.id, request_id=req_id)
            db.add(interest_record)
            
            # Notify Requester
            msg_to_requester = f"{user.name} is interested in helping with '{req.item_name}'. Contact: {user.email} | {user.phone_number or 'No phone provided'}"
            notif1 = models.Notification(recipient_id=requester.id, sender_id=user.id, type="interest", message=msg_to_requester)
            db.add(notif1)
            
            # Notify Interested User
            msg_to_interested = f"You offered to help {requester.name} with '{req.item_name}'. Contact: {requester.email} | {requester.phone_number or 'No phone provided'}"
            notif2 = models.Notification(recipient_id=user.id, sender_id=requester.id, type="interest", message=msg_to_interested)
            db.add(notif2)
            
            db.commit()
            
    return HTMLResponse(content="<script>alert('Accepted! Check your notifications for contact details.'); window.location.href='/community-requests';</script>")

@app.post("/requests/hide/{req_id}")
async def hide_request(request: Request, req_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    existing = db.query(models.HiddenRequest).filter(models.HiddenRequest.user_id == user.id, models.HiddenRequest.request_id == req_id).first()
    if not existing:
        hide_record = models.HiddenRequest(user_id=user.id, request_id=req_id)
        db.add(hide_record)
        db.commit()
        
    referer = request.headers.get("referer") or "/dashboard"
    return RedirectResponse(url=referer, status_code=302)


@app.post("/requests/{req_id}/delete")
async def delete_request(request: Request, req_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    req = db.query(models.ItemRequest).filter(models.ItemRequest.id == req_id).first()
    if req and req.requester_id == user.id:
        req.is_deleted = True
        db.commit()
    return RedirectResponse(url="/requests", status_code=302)

@app.get("/admin/requests", response_class=HTMLResponse)
async def admin_requests_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    # Fetch unapproved admins
    admin_requests = db.query(models.User).filter(models.User.role == "admin", models.User.is_approved == False).all()
    pending_count = len(admin_requests)
    
    return templates.TemplateResponse(request=request, name="admin/admin_requests.html", context={"request": request, "user": user, "pending_count": pending_count, "admin_requests": admin_requests})

@app.get("/all-users", response_class=HTMLResponse)
async def all_users_page_fixed(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    pending_count = db.query(models.User).filter(models.User.is_approved == False).count()
    all_registered_users = db.query(models.User).filter(models.User.is_approved == True).order_by(models.User.id.desc()).all()
    referrer_map = {u.id: u.name for u in db.query(models.User).all()}
    return templates.TemplateResponse(request=request, name="admin/all_users.html", context={
        "request": request, 
        "user": user, 
        "pending_count": pending_count, 
        "approved_users": all_registered_users,
        "referrer_map": referrer_map
    })

@app.get("/reports", response_class=HTMLResponse)
async def reports_page_fixed(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    pending_count = db.query(models.User).filter(models.User.is_approved == False).count()
    
    total_users = db.query(models.User).count()
    total_resources = db.query(models.Resource).count()
    
    from datetime import datetime, timedelta
    
    day_wise_stats = []
    # Calculate for the last 7 days
    for i in range(7):
        target_date = (datetime.utcnow() - timedelta(days=i)).date()
        target_date_str = target_date.strftime("%Y-%m-%d")
        
        users = db.query(models.User).all()
        resources = db.query(models.Resource).all()
        
        users_that_day = sum(1 for u in users if u.created_at and u.created_at.date() == target_date)
        resources_that_day = sum(1 for r in resources if r.date_posted == target_date_str)
        
        day_wise_stats.append({
            "date": target_date.strftime("%b %d, %Y"),
            "new_users": users_that_day,
            "new_resources": resources_that_day
        })
        
    users_this_week = sum(stat["new_users"] for stat in day_wise_stats)
    resources_this_week = sum(stat["new_resources"] for stat in day_wise_stats)

    return templates.TemplateResponse(request=request, name="admin/reports.html", context={
        "request": request, 
        "user": user, 
        "pending_count": pending_count,
        "total_users": total_users,
        "total_resources": total_resources,
        "users_this_week": users_this_week,
        "resources_this_week": resources_this_week,
        "day_wise_stats": day_wise_stats
    })

@app.get("/admin-messages", response_class=HTMLResponse)
async def admin_messages_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    pending_count = db.query(models.User).filter(models.User.is_approved == False).count()
    support_messages = db.query(models.SupportMessage).order_by(models.SupportMessage.id.desc()).all()
    return templates.TemplateResponse(request=request, name="admin/admin_messages.html", context={"request": request, "user": user, "pending_count": pending_count, "support_messages": support_messages})

@app.get("/community-updates", response_class=HTMLResponse)
async def community_updates_page(request: Request, db: Session = Depends(get_db)):
    auto_delete_expired(db)
    from datetime import date
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    today = date.today().isoformat()
    all_updates = db.query(models.CommunityUpdate).all()
    for u in all_updates:
        if u.event_date and u.event_date < today:
            db.delete(u)
    db.commit()
    admin_updates = db.query(models.CommunityUpdate).order_by(models.CommunityUpdate.id.desc()).all()
    
    return templates.TemplateResponse(request=request, name="shared/community_updates.html", context={"request": request, "user": user, "admin_updates": admin_updates})

@app.get("/community-requests", response_class=HTMLResponse)
async def community_requests_page(request: Request, db: Session = Depends(get_db)):
    auto_delete_expired(db)
    from datetime import date
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    today = date.today().isoformat()
    all_reqs = db.query(models.ItemRequest).filter(models.ItemRequest.is_deleted == False).all()
    for r in all_reqs:
        if r.date_required and r.date_required < today:
            r.is_deleted = True
    db.commit()
    active_requests = db.query(models.ItemRequest).filter(models.ItemRequest.is_deleted == False, models.ItemRequest.is_fulfilled == False).order_by(models.ItemRequest.id.desc()).all()
    
    return templates.TemplateResponse(request=request, name="users/community_requests.html", context={"request": request, "user": user, "active_requests": active_requests})

@app.get("/community", response_class=HTMLResponse)
async def community_page(request: Request, db: Session = Depends(get_db)):
    auto_delete_expired(db)
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="shared/community_updates.html", context={"request": request, "user": user})

@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="users/upload.html", context={"request": request, "user": user})

@app.get("/donate")
async def donate_redirect():
    return RedirectResponse(url="/search?type=donate", status_code=302)

@app.get("/mentors", response_class=HTMLResponse)
async def mentors_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    requests = db.query(models.MentorshipRequest).order_by(models.MentorshipRequest.id.desc()).all()
    return templates.TemplateResponse(request=request, name="users/mentors.html", context={"request": request, "user": user, "requests": requests})


@app.get("/mentors/edit/{req_id}", response_class=HTMLResponse)
async def edit_mentor_page(request: Request, req_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    req = db.query(models.MentorshipRequest).filter(models.MentorshipRequest.id == req_id).first()
    if not req or req.student_id != user.id:
        return RedirectResponse(url="/mentors", status_code=302)
    return templates.TemplateResponse(request=request, name="users/edit_mentor_request.html", context={"request": request, "user": user, "req": req})

@app.post("/mentors/edit/{req_id}")
async def edit_mentor_action(request: Request, req_id: int, subject: str = Form(...), description: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    req = db.query(models.MentorshipRequest).filter(models.MentorshipRequest.id == req_id).first()
    if req and req.student_id == user.id:
        req.subject = subject
        req.description = description
        db.commit()
    return RedirectResponse(url="/mentors", status_code=302)

@app.post("/mentors/delete/{req_id}")
async def delete_mentor_action(request: Request, req_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    req = db.query(models.MentorshipRequest).filter(models.MentorshipRequest.id == req_id).first()
    if req and (req.student_id == user.id or user.role == "admin"):
        db.delete(req)
        db.commit()
    return RedirectResponse(url="/mentors", status_code=302)

@app.post("/mentors/request")
async def request_mentor(request: Request, subject: str = Form(...), description: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    new_req = models.MentorshipRequest(subject=subject, description=description, student_id=user.id)
    db.add(new_req)
    db.commit()
    return RedirectResponse(url="/mentors", status_code=302)


@app.get("/download/{resource_id}")
async def download_resource(resource_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = int(request.cookies.get("user_id", CURRENT_USER_ID))
    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not resource:
        return RedirectResponse(url="/search")
        
    if resource.owner_id != user_id:
        if resource.resource_type == 'rent':
            return HTMLResponse(content="<script>alert('You cannot download rented resources directly. Please contact the owner using the I\'m Interested button.'); window.history.back();</script>")
        elif resource.resource_type == 'exchange':
            # Check if there is an accepted exchange offer involving this user and this resource
            is_authorized = db.query(models.ExchangeOffer).filter(
                models.ExchangeOffer.status == 'accepted',
                ((models.ExchangeOffer.target_resource_id == resource.id) & (models.ExchangeOffer.requester_id == user_id)) |
                ((models.ExchangeOffer.offered_resource_id == resource.id) & (models.ExchangeOffer.target_owner_id == user_id))
            ).first()
            if not is_authorized:
                return HTMLResponse(content="<script>alert('You can only download this resource if an exchange offer has been accepted.'); window.history.back();</script>")

        
    # Save it to saved resources
    existing = db.query(models.SavedResource).filter_by(user_id=user_id, resource_id=resource_id).first()
    if not existing:
        new_save = models.SavedResource(user_id=user_id, resource_id=resource_id)
        db.add(new_save)
        db.commit()
    
    import os
    if resource.image and os.path.exists(resource.image.lstrip('/')):
        from fastapi.responses import FileResponse
        return FileResponse(path=resource.image.lstrip('/'), filename=resource.image.split('/')[-1])
    return RedirectResponse(url=f"/resource/{resource_id}")


@app.post("/api/interest/{resource_id}")
async def express_interest(resource_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    if user.coins < 20:
        return HTMLResponse(content="<script>alert(\'Not enough coins to download!\'); window.history.back();</script>")
    user.coins -= 20
    tx = models.CoinTransaction(user_id=user.id, amount=-20, reason="Downloaded Free Resource")
    db.add(tx)
    db.commit()

    if user.coins < 10:
        return HTMLResponse(content="<script>alert(\'Not enough coins to borrow/rent!\'); window.history.back();</script>")
    user.coins -= 10
    tx = models.CoinTransaction(user_id=user.id, amount=-10, reason="Expressed Interest (Borrow/Rent)")
    db.add(tx)
    db.commit()

    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if resource and resource.resource_type == 'exchange':
        return RedirectResponse(url=f"/exchange/offer/{resource_id}", status_code=302)
        
    if resource and resource.owner_id != user.id:
        owner = db.query(models.User).filter(models.User.id == resource.owner_id).first()
        if owner:
            # Notify Owner
            msg_to_owner = f"{user.name} is interested in your resource '{resource.title}'. Contact: {user.email} | {user.phone_number or 'No phone provided'}"
            notif1 = models.Notification(
                recipient_id=owner.id,
                sender_id=user.id,
                type="interest",
                message=msg_to_owner
            )
            db.add(notif1)
            
            # Notify Interested User
            msg_to_interested = f"You expressed interest in {owner.name}'s resource '{resource.title}'. Contact: {owner.email} | {owner.phone_number or 'No phone provided'}"
            notif2 = models.Notification(
                recipient_id=user.id,
                sender_id=owner.id,
                type="interest",
                message=msg_to_interested
            )
            db.add(notif2)
            db.commit()
    
    return HTMLResponse(content="<script>alert('Interest sent! Check your notifications for contact details.'); window.history.back();</script>")

import shutil
import os

@app.post("/upload")
async def upload_resource_post(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    resource_type: str = Form(...),
    category_select: str = Form(...),
    category_other: str = Form(None),
    price_per_day: str = Form("0"),
    exchange_for: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    
    category = category_other if category_select == "Other" and category_other else category_select

    if not user: return RedirectResponse(url="/login", status_code=302)
    
    # Handle file save
    file_url = None
    if file and file.filename:
        upload_dir = "../frontend/static/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = f"{upload_dir}/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        file_url = f"/static/uploads/{file.filename}"
    
    from datetime import datetime
    new_res = models.Resource(
        title=title,
        description=description,
        resource_type=resource_type,
        category=category,
        price_per_day=price_per_day,
        exchange_for=exchange_for,
        image=file_url,
        owner_id=user.id,
        date_posted=datetime.now().strftime("%Y-%m-%d")
    )
    db.add(new_res)
    db.commit()
    
    # Add Coins logic (Fixed type checks)
    if resource_type == "donate":
        user.coins += 30
        tx = models.CoinTransaction(user_id=user.id, amount=30, reason="Uploaded Free Resource")
        db.add(tx)
        db.commit()
    elif resource_type == "rent":
        user.coins += 20
        tx = models.CoinTransaction(user_id=user.id, amount=20, reason="Uploaded Rent Resource")
        db.add(tx)
        db.commit()
    elif resource_type == "exchange":
        user.coins += 20
        tx = models.CoinTransaction(user_id=user.id, amount=20, reason="Uploaded Exchange Request")
        db.add(tx)
        db.commit()
    
    # Broadcast notification to all other users
    all_users = db.query(models.User).filter(models.User.id != user.id).all()
    for u in all_users:
        notif = models.Notification(
            recipient_id=u.id,
            sender_id=user.id,
            type="new_resource",
            message=f"{user.name} posted a new resource: {title}",
            is_read=False,
            is_pinned=False
        )
        db.add(notif)
    db.commit()
    
    return RedirectResponse(url="/search", status_code=302)

@app.get("/saved-resources", response_class=HTMLResponse)
async def saved_resources_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    saved = db.query(models.SavedResource).filter(models.SavedResource.user_id == user.id).all()
    saved = [s for s in saved if s.resource is not None]
    liked_ids = [like.resource_id for like in db.query(models.LikedResource).filter_by(user_id=user.id).all()]
    return templates.TemplateResponse(request=request, name="users/saved_resources.html", context={"request": request, "user": user, "saved_items": saved, "liked_ids": liked_ids})


# --- DASHBOARD ROUTES ---
# The main landing page after login. Calculates metrics and loads data.
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    auto_delete_expired(db)
    from datetime import date
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    liked_ids = [like.resource_id for like in db.query(models.LikedResource).filter_by(user_id=user.id).all()]
    
    today = date.today().isoformat()
    # Auto-delete expired requests
    all_reqs = db.query(models.ItemRequest).filter(models.ItemRequest.is_deleted == False).all()
    for r in all_reqs:
        if r.date_required and r.date_required < today:
            r.is_deleted = True
    
    # Auto-delete expired updates
    all_updates = db.query(models.CommunityUpdate).all()
    for u in all_updates:
        if u.event_date and u.event_date < today:
            db.delete(u)
    db.commit()
    
    community_requests = db.query(models.ItemRequest).filter(models.ItemRequest.is_deleted == False, models.ItemRequest.is_fulfilled == False).order_by(models.ItemRequest.id.desc()).limit(3).all()
    community_updates = db.query(models.CommunityUpdate).order_by(models.CommunityUpdate.id.desc()).limit(3).all()
    
    pending_users = []
    pending_count = 0
    total_users_count = 0
    total_resources_count = 0
    total_updates_count = 0
    all_registered_users = []
    if user.role == "admin":
        pending_users = db.query(models.User).filter(models.User.role == "admin", models.User.is_approved == False).all()
        pending_count = len(pending_users)
        all_registered_users = db.query(models.User).filter(models.User.is_approved == True).order_by(models.User.id.desc()).all()
        total_users_count = db.query(models.User).count()
        total_resources_count = db.query(models.Resource).count()
        total_updates_count = db.query(models.CommunityUpdate).count()
        
    return templates.TemplateResponse(request=request, name="shared/dashboard.html", context={"request": request, "user": user, "liked_ids": liked_ids, "community_requests": community_requests, "community_updates": community_updates, "interested_req_ids": interested_req_ids, "pending_users": pending_users, "pending_count": pending_count, "total_users_count": total_users_count, "total_resources_count": total_resources_count, "total_updates_count": total_updates_count, "all_registered_users": all_registered_users})


@app.get("/recent-resources", response_class=HTMLResponse)
async def recent_resources_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    # Fetch all resources, order by ID descending (chronological)
    resources = db.query(models.Resource).order_by(models.Resource.id.desc()).all()
    return templates.TemplateResponse(request=request, name="users/recent_resources.html", context={"request": request, "user": user, "resources": resources})



@app.get("/api/unread-count")
async def unread_count(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return {"count": 0}
    count = db.query(models.Notification).filter(models.Notification.recipient_id == user.id, models.Notification.is_read == False).count()
    return {"count": count}

@app.post("/notifications/pin/{notif_id}")
async def pin_notification(notif_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    notif = db.query(models.Notification).filter(models.Notification.id == notif_id, models.Notification.recipient_id == user.id).first()
    if notif:
        notif.is_pinned = not notif.is_pinned
        db.commit()
    return RedirectResponse(url="/notifications", status_code=status.HTTP_302_FOUND)

@app.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    notifications = db.query(models.Notification).filter(models.Notification.recipient_id == user.id).order_by(models.Notification.is_pinned.desc(), models.Notification.id.desc()).all()
    
    # Mark all as read
    for n in notifications:
        if not n.is_read:
            n.is_read = True
    db.commit()
    
    return templates.TemplateResponse(request=request, name="users/notifications.html", context={"request": request, "user": user, "notifications": notifications})

@app.post("/notifications/dismiss/{notif_id}")
async def dismiss_notification(notif_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    notif = db.query(models.Notification).filter(models.Notification.id == notif_id, models.Notification.recipient_id == user.id).first()
    if notif:
        db.delete(notif)
        db.commit()
        
    return RedirectResponse(url="/notifications", status_code=status.HTTP_302_FOUND)

# --- RESOURCE MANAGEMENT ---
# Displays all available resources filtered by type (donate, rent, etc.)
@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, type: str = None, query: str = None, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    q = db.query(models.Resource)
    if type:
        q = q.filter(models.Resource.resource_type == type)
    if query:
        q = q.filter(models.Resource.title.contains(query) | models.Resource.description.contains(query))
        
    resources = q.order_by(models.Resource.id.desc()).all()
    liked_ids = [like.resource_id for like in db.query(models.LikedResource).filter_by(user_id=user.id).all()]
    return templates.TemplateResponse(request=request, name="users/search.html", context={"request": request, "user": user, "resources": resources, "type": type, "query": query, "liked_ids": liked_ids})

@app.get("/resource/{resource_id}", response_class=HTMLResponse)
async def resource_details(request: Request, resource_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    is_liked = db.query(models.LikedResource).filter_by(user_id=user.id, resource_id=resource_id).first() is not None
    return templates.TemplateResponse(request=request, name="users/resource.html", context={"request": request, "user": user, "resource": resource, "is_liked": is_liked})

@app.get("/toggle-like/{resource_id}")
async def toggle_like(resource_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login")
    
    existing = db.query(models.LikedResource).filter_by(user_id=user.id, resource_id=resource_id).first()
    if existing:
        db.delete(existing)
    else:
        new_like = models.LikedResource(user_id=user.id, resource_id=resource_id)
        db.add(new_like)
    db.commit()
    
    # Redirect back to where they came from
    referer = request.headers.get("referer", "/dashboard")
    return RedirectResponse(url=referer, status_code=status.HTTP_302_FOUND)

@app.get("/liked-resources", response_class=HTMLResponse)
async def liked_resources_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login")
    
    likes = db.query(models.LikedResource).filter_by(user_id=user.id).all()
    liked_resources = [like.resource for like in likes if like.resource is not None]
    
    # We also need to pass liked_resource_ids to properly color the hearts
    liked_resource_ids = [r.id for r in liked_resources]
    
    return templates.TemplateResponse(request=request, name="users/liked_resources.html", context={"request": request, "user": user, "resources": liked_resources, "liked_ids": liked_resource_ids})


@app.get("/edit-resource/{resource_id}", response_class=HTMLResponse)
async def edit_resource_page(request: Request, resource_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not resource or resource.owner_id != user.id:
        return RedirectResponse(url="/search", status_code=302)
    return templates.TemplateResponse(request=request, name="users/edit_resource.html", context={"request": request, "user": user, "resource": resource})

@app.post("/edit-resource/{resource_id}")
async def update_resource(request: Request, resource_id: int, title: str = Form(...), description: str = Form(...), category_select: str = Form(...), category_other: str = Form(None), resource_type: str = Form(...), price_per_day: str = Form(None), exchange_for: str = Form(None), file: UploadFile = File(None), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    category = category_other if category_select == "Other" and category_other else category_select
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not resource or resource.owner_id != user.id:
        return RedirectResponse(url="/search", status_code=302)
        
    resource.title = title
    resource.description = description
    resource.category = category
    resource.resource_type = resource_type
    if price_per_day: resource.price_per_day = price_per_day
    if exchange_for: resource.exchange_for = exchange_for
    
    if file and file.filename:
        import os
        import shutil
        upload_dir = "../frontend/static/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = f"{upload_dir}/{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        resource.image = "/" + file_path
        
    db.commit()
    return RedirectResponse(url="/search", status_code=302)

@app.post("/delete-resource/{resource_id}")
async def delete_resource(resource_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login")
    
    resource = db.query(models.Resource).filter_by(id=resource_id, owner_id=user.id).first()
    if resource:
        db.delete(resource)
        db.commit()
        
    return RedirectResponse(url="/search", status_code=status.HTTP_302_FOUND)

@app.post("/edit_profile")
async def profile_update(request: Request, name: str = Form(...), phone_number: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    user.name = name
    user.phone_number = phone_number
    db.commit()
    return RedirectResponse(url="/profile", status_code=302)

@app.get("/ask_doubt", response_class=HTMLResponse)
async def ask_doubt_page(request: Request, query: str = None, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    q = db.query(models.Doubt)
    if query:
        q = q.filter(models.Doubt.title.contains(query) | models.Doubt.description.contains(query))
    all_doubts = q.order_by(models.Doubt.id.desc()).all()
    
    my_doubts = []
    answered_doubts = []
    unanswered_doubts = []
    
    for d in all_doubts:
        if d.author_id == user.id:
            my_doubts.append(d)
        if len(d.replies) >= 3:
            answered_doubts.append(d)
        else:
            unanswered_doubts.append(d)
            
    return templates.TemplateResponse(request=request, name="users/ask_doubt.html", context={
        "request": request,
        "user": user,
        "query": query,
        "community_doubts": all_doubts,
        "my_doubts": my_doubts,
        "answered_doubts": answered_doubts,
        "unanswered_doubts": unanswered_doubts
    })

@app.post("/ask_doubt")
async def post_doubt(request: Request, title: str = Form(...), description: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    from datetime import datetime
    new_doubt = models.Doubt(
        title=title,
        description=description,
        author_id=user.id,
        created_at=datetime.now().strftime("%Y-%m-%d %I:%M %p")
    )
    db.add(new_doubt)
    db.commit()
    return RedirectResponse(url="/ask_doubt", status_code=302)

@app.get("/doubt/{doubt_id}", response_class=HTMLResponse)
async def doubt_detail(request: Request, doubt_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    doubt = db.query(models.Doubt).filter(models.Doubt.id == doubt_id).first()
    if not doubt:
        return RedirectResponse(url="/ask_doubt", status_code=302)
        
    return templates.TemplateResponse(request=request, name="users/doubt_detail.html", context={
        "request": request,
        "user": user,
        "doubt": doubt
    })

@app.post("/doubt/{doubt_id}/answer")
async def answer_doubt(request: Request, doubt_id: int, content: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    from datetime import datetime
    new_reply = models.Reply(
        doubt_id=doubt_id,
        content=content,
        author_id=user.id,
        created_at=datetime.now().strftime("%Y-%m-%d %I:%M %p")
    )
    db.add(new_reply)
    db.commit()
    return RedirectResponse(url=f"/doubt/{doubt_id}", status_code=302)

@app.get("/reply/{reply_id}/vote")
async def vote_reply(request: Request, reply_id: int, type: str, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    reply = db.query(models.Reply).filter(models.Reply.id == reply_id).first()
    if reply:
        if type == 'like':
            reply.likes = (reply.likes or 0) + 1
        elif type == 'dislike':
            reply.dislikes = (reply.dislikes or 0) + 1
        db.commit()
    
    # redirect back to the doubt page
    if reply:
        return RedirectResponse(url=f"/doubt/{reply.doubt_id}", status_code=302)
    return RedirectResponse(url="/ask_doubt", status_code=302)


@app.get("/exchange/offer/{resource_id}")
async def exchange_offer_page(resource_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not resource: return RedirectResponse(url="/search")
    
    # Check if they already submitted an offer
    existing_offer = db.query(models.ExchangeOffer).filter(
        models.ExchangeOffer.requester_id == user.id,
        models.ExchangeOffer.target_resource_id == resource_id
    ).first()
    if existing_offer:
        return HTMLResponse(content="<script>alert('You have already submitted an exchange offer for this resource.'); window.history.back();</script>")
    
    return templates.TemplateResponse(request=request, name="users/exchange_offer.html", context={"request": request, "user": user, "resource": resource})

@app.post("/exchange/offer/{resource_id}")
async def process_exchange_offer(
    resource_id: int, 
    request: Request, 
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    target_res = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not target_res: return RedirectResponse(url="/search")
    
    # Check if they already submitted an offer
    existing_offer = db.query(models.ExchangeOffer).filter(
        models.ExchangeOffer.requester_id == user.id,
        models.ExchangeOffer.target_resource_id == resource_id
    ).first()
    if existing_offer:
        return HTMLResponse(content="<script>alert('You have already submitted an exchange offer for this resource.'); window.history.back();</script>")
    
    # Save the uploaded file as a new resource
    import uuid
    import shutil
    import os
    ext = file.filename.split('.')[-1] if '.' in file.filename else 'pdf'
    filename = f"exchange_{uuid.uuid4().hex}.{ext}"
    filepath = f"../frontend/static/uploads/{filename}"
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    offered_res = models.Resource(
        title=f"Exchange for {target_res.title}",
        description=f"Offered in exchange for {target_res.title}",
        resource_type="private_exchange", # Make it a standard resource but we'll link it
        category=target_res.category,
        owner_id=user.id,
        image=f"/{filepath}",
        date_posted="2026-09-23"
    )
    db.add(offered_res)
    db.commit()
    db.refresh(offered_res)
    
    # Create the offer
    offer = models.ExchangeOffer(
        target_resource_id=target_res.id,
        offered_resource_id=offered_res.id,
        requester_id=user.id,
        target_owner_id=target_res.owner_id,
        status="pending"
    )
    db.add(offer)
    db.commit()
    
    # Notify owner
    notif = models.Notification(
        recipient_id=target_res.owner_id,
        sender_id=user.id,
        type="exchange_offer",
        message=f"{user.name} has uploaded the requested resource in exchange for '{target_res.title}'. Click here to accept.",
        link=f"/exchange/review/{offer.id}"
    )
    db.add(notif)
    
    # Notify the requester that their offer was sent
    notif_requester = models.Notification(
        recipient_id=user.id,
        sender_id=user.id,
        type="exchange_offer_sent",
        message=f"Your exchange request for '{target_res.title}' has been sent to the owner. You will be notified when they accept it.",
        link="/my-exchanges"
    )
    db.add(notif_requester)
    db.commit()
    
    return HTMLResponse(content="<script>alert('Your resource was shared. It will appear in My Exchanges once the owner accepts it.'); window.location.href='/search';</script>")

@app.get("/exchange/review/{offer_id}")
async def review_exchange(offer_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    offer = db.query(models.ExchangeOffer).filter(models.ExchangeOffer.id == offer_id).first()
    if not offer or offer.target_owner_id != user.id:
        return RedirectResponse(url="/search")
        
    offered_res = db.query(models.Resource).filter(models.Resource.id == offer.offered_resource_id).first()
    target_res = db.query(models.Resource).filter(models.Resource.id == offer.target_resource_id).first()
    requester = db.query(models.User).filter(models.User.id == offer.requester_id).first()
    
    return templates.TemplateResponse(request=request, name="users/exchange_review.html", context={
        "request": request, 
        "user": user, 
        "offer": offer,
        "offered_res": offered_res,
        "target_res": target_res,
        "requester": requester
    })

@app.post("/exchange/accept/{offer_id}")
async def accept_exchange(offer_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    if user.coins < 10:
        return HTMLResponse(content="<script>alert(\'Not enough coins to accept exchange!\'); window.history.back();</script>")
    user.coins -= 10
    tx = models.CoinTransaction(user_id=user.id, amount=-10, reason="Accepted Exchange Request")
    db.add(tx)
    db.commit()

    offer = db.query(models.ExchangeOffer).filter(models.ExchangeOffer.id == offer_id).first()
    if not offer or offer.target_owner_id != user.id:
        return RedirectResponse(url="/search")
        
    offer.status = "accepted"
    
    target_res = db.query(models.Resource).filter(models.Resource.id == offer.target_resource_id).first()
    
    # Notify both users
    notif1 = models.Notification(
        recipient_id=offer.requester_id,
        sender_id=user.id,
        type="exchange_accepted",
        message=f"Your exchange for '{target_res.title}' was accepted! Click to Preview/Download.",
        link=f"/resource/{offer.target_resource_id}"
    )
    db.add(notif1)
    
    notif2 = models.Notification(
        recipient_id=user.id,
        sender_id=offer.requester_id,
        type="exchange_accepted",
        message=f"You accepted the exchange for '{target_res.title}'. Click to Preview/Download their resource.",
        link=f"/resource/{offer.offered_resource_id}"
    )
    db.add(notif2)
    db.commit()
    
    return HTMLResponse(content="<script>alert('Exchange accepted! Both parties can now download their resources.'); window.location.href='/search';</script>")



@app.get("/my-exchanges")
async def my_exchanges_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    
    offers = db.query(models.ExchangeOffer).filter(
        models.ExchangeOffer.status == 'accepted',
        ((models.ExchangeOffer.requester_id == user.id) | (models.ExchangeOffer.target_owner_id == user.id))
    ).all()
    
    resource_ids = []
    for offer in offers:
        if offer.requester_id == user.id:
            resource_ids.append(offer.target_resource_id)
        if offer.target_owner_id == user.id:
            resource_ids.append(offer.offered_resource_id)
            
    resources = db.query(models.Resource).filter(models.Resource.id.in_(resource_ids)).all()
    
    return templates.TemplateResponse(request=request, name="users/my_exchanges.html", context={"request": request, "user": user, "resources": resources})


# --- CHAT ROUTES ---
import os
import shutil
from fastapi import UploadFile, File, Form
from fastapi.responses import JSONResponse

# --- CHAT SYSTEM ---
# Renders the Global Community Chat UI.
@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(request=request, name="shared/chat.html", context={"request": request, "user": user})

# Fetches the last 50 global chat messages to display in real-time.
@app.get("/api/chat/messages")
async def get_chat_messages(db: Session = Depends(get_db)):
    # Fetch last 50 messages
    messages = db.query(models.ChatMessage).order_by(models.ChatMessage.id.desc()).limit(50).all()
    # Reverse to chronological order
    messages = list(reversed(messages))
    
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "user_name": msg.user.name,
            "user_id": msg.user_id,
            "message": msg.message,
            "image_url": msg.image_url,
            "created_at": msg.created_at
        })
    return JSONResponse(content=result)

@app.post("/api/chat/send")
async def send_chat_message(
    request: Request, 
    message: str = Form(None), 
    image: UploadFile = File(None), 
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    if not message and not image:
        return JSONResponse(status_code=400, content={"error": "Message or image is required"})

    image_url = None
    if image and image.filename:
        # Save image
        upload_dir = "../frontend/static/uploads/chat"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, image.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/static/uploads/chat/{image.filename}"

    new_msg = models.ChatMessage(
        user_id=user.id,
        message=message,
        image_url=image_url
    )
    db.add(new_msg)
    db.commit()
    return JSONResponse(content={"status": "success"})


# --- FRIENDS & PRIVATE CHAT ROUTES ---
from sqlalchemy import or_, and_

@app.get("/user/{user_id}", response_class=HTMLResponse)
async def public_profile(request: Request, user_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user: return RedirectResponse(url="/login", status_code=302)
    
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        return RedirectResponse(url="/dashboard", status_code=302)
        
    # Check friendship status
    friend_req = db.query(models.FriendRequest).filter(
        or_(
            and_(models.FriendRequest.sender_id == current_user.id, models.FriendRequest.receiver_id == user_id),
            and_(models.FriendRequest.sender_id == user_id, models.FriendRequest.receiver_id == current_user.id)
        )
    ).first()
    
    friendship_status = "none"
    if friend_req:
        if friend_req.status == "accepted":
            friendship_status = "friends"
        elif friend_req.status == "pending":
            if friend_req.sender_id == current_user.id:
                friendship_status = "pending_sent"
            else:
                friendship_status = "pending_received"
                
    return templates.TemplateResponse(request=request, name="shared/public_profile.html", context={
        "request": request,
        "user": current_user,
        "target_user": target_user,
        "friendship_status": friendship_status,
        "friend_req": friend_req
    })

@app.post("/api/friends/request/{user_id}")
async def send_friend_request(request: Request, user_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user: return RedirectResponse(url="/login", status_code=302)
    
    existing_req = db.query(models.FriendRequest).filter(
        or_(
            and_(models.FriendRequest.sender_id == current_user.id, models.FriendRequest.receiver_id == user_id),
            and_(models.FriendRequest.sender_id == user_id, models.FriendRequest.receiver_id == current_user.id)
        )
    ).first()
    
    if not existing_req:
        new_req = models.FriendRequest(sender_id=current_user.id, receiver_id=user_id)
        db.add(new_req)
        
        # Add Notification
        notif = models.Notification(
            recipient_id=user_id,
            sender_id=current_user.id,
            type="friend_request",
            message=f"{current_user.name} sent you a friend request.",
            link="/my-friends"
        )
        db.add(notif)
        db.commit()
        
    return RedirectResponse(url=f"/user/{user_id}", status_code=302)

@app.post("/api/friends/accept/{request_id}")
async def accept_friend_request(request: Request, request_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user: return RedirectResponse(url="/login", status_code=302)
    
    req = db.query(models.FriendRequest).filter(models.FriendRequest.id == request_id, models.FriendRequest.receiver_id == current_user.id).first()
    if req:
        req.status = "accepted"
        
        # Add Notification
        notif = models.Notification(
            recipient_id=req.sender_id,
            sender_id=current_user.id,
            type="friend_accept",
            message=f"{current_user.name} accepted your friend request!",
            link=f"/my-friends?chat={current_user.id}"
        )
        db.add(notif)
        db.commit()
    return RedirectResponse(url="/my-friends", status_code=302)

@app.get("/my-friends", response_class=HTMLResponse)
async def my_friends(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user: return RedirectResponse(url="/login", status_code=302)
    
    pending_requests = db.query(models.FriendRequest).filter(
        models.FriendRequest.receiver_id == current_user.id,
        models.FriendRequest.status == "pending"
    ).all()
    
    accepted_friendships = db.query(models.FriendRequest).filter(
        models.FriendRequest.status == "accepted",
        or_(models.FriendRequest.sender_id == current_user.id, models.FriendRequest.receiver_id == current_user.id)
    ).all()
    
    friends = []
    for f in accepted_friendships:
        if f.sender_id == current_user.id:
            friends.append(f.receiver)
        else:
            friends.append(f.sender)
            
    return templates.TemplateResponse(request=request, name="shared/friends.html", context={
        "request": request,
        "user": current_user,
        "pending_requests": pending_requests,
        "friends": friends
    })

@app.get("/api/private-chat/{friend_id}")
async def get_private_messages(request: Request, friend_id: int, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    if not current_user: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    messages = db.query(models.PrivateMessage).filter(
        or_(
            and_(models.PrivateMessage.sender_id == current_user.id, models.PrivateMessage.receiver_id == friend_id),
            and_(models.PrivateMessage.sender_id == friend_id, models.PrivateMessage.receiver_id == current_user.id)
        )
    ).order_by(models.PrivateMessage.id.asc()).all()
    
    result = []
    for msg in messages:
        result.append({
            "id": msg.id,
            "sender_id": msg.sender_id,
            "message": msg.message,
            "image_url": getattr(msg, "image_url", None),
            "created_at": msg.created_at
        })
    return JSONResponse(content=result)

# Sends a 1-on-1 private message and processes image attachments.
@app.post("/api/private-chat/{friend_id}")
async def send_private_message(
    request: Request, 
    friend_id: int, 
    message: str = Form(None), 
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if not current_user: return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    
    if not message and not image:
        return JSONResponse(status_code=400, content={"error": "Message or image is required"})

    image_url = None
    if image and image.filename:
        # Save image
        upload_dir = "../frontend/static/uploads/chat"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, image.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/static/uploads/chat/{image.filename}"

    new_msg = models.PrivateMessage(
        sender_id=current_user.id,
        receiver_id=friend_id,
        message=message,
        image_url=image_url
    )
    db.add(new_msg)
    
    # Check if a notification already exists from this user to avoid spamming
    # but for private messages, usually you notify. Let's just create a notification if we want.
    notif = models.Notification(
        recipient_id=friend_id,
        sender_id=current_user.id,
        type="new_message",
        message=f"New message from {current_user.name}",
        link=f"/my-friends?chat={current_user.id}"
    )
    db.add(notif)
    db.commit()
    return JSONResponse(content={"status": "success"})



@app.delete('/api/private-chat/message/{message_id}')
async def delete_private_message(request: Request, message_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return JSONResponse(status_code=401, content={'error': 'Unauthorized'})
    
    msg = db.query(models.PrivateMessage).filter(models.PrivateMessage.id == message_id, models.PrivateMessage.sender_id == user.id).first()
    if not msg:
        return JSONResponse(status_code=404, content={'error': 'Not found or unauthorized'})
    
    db.delete(msg)
    db.commit()
    return JSONResponse(content={'status': 'success'})

@app.put('/api/private-chat/message/{message_id}')
async def edit_private_message(request: Request, message_id: int, new_message: str = Form(...), db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return JSONResponse(status_code=401, content={'error': 'Unauthorized'})
    
    msg = db.query(models.PrivateMessage).filter(models.PrivateMessage.id == message_id, models.PrivateMessage.sender_id == user.id).first()
    if not msg:
        return JSONResponse(status_code=404, content={'error': 'Not found or unauthorized'})
        
    msg.message = new_message
    db.commit()
    return JSONResponse(content={'status': 'success'})



