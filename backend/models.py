"""
MODELS MODULE (models.py)
-------------------------
Purpose:
This file defines the SQLAlchemy Object-Relational Mapping (ORM) models.
Each class represents a table in the SQLite database (e.g., users, resources, messages).

Why it's here:
By defining our database schema here, FastAPI and SQLAlchemy know exactly what columns, 
data types, and relationships exist in our database. main.py will import these models 
to perform CRUD (Create, Read, Update, Delete) operations.
"""
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String)
    password = Column(String)
    role = Column(String, default="student") # "student" or "admin"
    created_at = Column(DateTime, default=datetime.utcnow)
    is_approved = Column(Boolean, default=True)
    approval_status = Column(String, default="pending") # Used for pending admins
    coins = Column(Integer, default=0)
    referral_code = Column(String, unique=True, index=True, nullable=True)
    referred_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    badges = Column(Integer, default=12)
    resources_shared = Column(Integer, default=18)
    resources_borrowed = Column(Integer, default=7)
    last_seen_resource_id = Column(Integer, default=0)
    last_login = Column(String, nullable=True)
    last_login = Column(String, nullable=True)

    resources = relationship("Resource", back_populates="owner")

class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    resource_type = Column(String) # 'donate', 'rent', 'exchange', 'digital'
    category = Column(String) # Book, Notes, Equipment
    price_per_day = Column(String, default="0") # Storing as string for simplicity e.g., "$5/day"
    exchange_for = Column(String) # What they want in exchange
    condition = Column(String)
    status = Column(String, default="Available")
    date_posted = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))
    image = Column(String)

    owner = relationship("User", back_populates="resources")

class Doubt(Base):
    __tablename__ = "doubts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    image_url = Column(String)
    author_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(String)
    
    author = relationship("User")
    replies = relationship("Reply", back_populates="doubt")

class Reply(Base):
    __tablename__ = "replies"
    id = Column(Integer, primary_key=True, index=True)
    doubt_id = Column(Integer, ForeignKey("doubts.id"))
    content = Column(String)
    author_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(String)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    
    doubt = relationship("Doubt", back_populates="replies")
    author = relationship("User")

class MentorshipRequest(Base):
    __tablename__ = "mentorship_requests"
    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String)
    description = Column(String)
    student_id = Column(Integer, ForeignKey("users.id"))
    mentor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="Open") # Open or Accepted
    created_at = Column(String)
    
    student = relationship("User", foreign_keys=[student_id])
    mentor = relationship("User", foreign_keys=[mentor_id])

class ExchangeOffer(Base):
    __tablename__ = "exchange_offers"
    id = Column(Integer, primary_key=True, index=True)
    target_resource_id = Column(Integer, ForeignKey("resources.id"))
    offered_resource_id = Column(Integer, ForeignKey("resources.id"))
    requester_id = Column(Integer, ForeignKey("users.id"))
    target_owner_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="pending") # pending, accepted, rejected

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("users.id"))
    sender_id = Column(Integer, ForeignKey("users.id"))
    type = Column(String) # 'rent_interest', 'donate_interest', 'exchange_interest', 'mentor_accept'
    message = Column(String)
    link = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(String, default=lambda: datetime.now().strftime("%b %d, %Y at %I:%M %p"))
    request_id = Column(Integer, ForeignKey("item_requests.id"), nullable=True)
    request = relationship("ItemRequest")
    
    recipient = relationship("User", foreign_keys=[recipient_id])
    sender = relationship("User", foreign_keys=[sender_id])

class Interest(Base):
    __tablename__ = "interests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    resource_id = Column(Integer, ForeignKey("resources.id"))
    
    user = relationship("User")
    resource = relationship("Resource")

class SupportMessage(Base):
    __tablename__ = "support_messages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String)
    created_at = Column(String, default=lambda: datetime.now().strftime("%b %d, %Y at %I:%M %p"))
    image_path = Column(String, nullable=True)
    image_path = Column(String, nullable=True)
    
    user = relationship("User")

class CoinTransaction(Base):
    __tablename__ = "coin_transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer)
    reason = Column(String)
    created_at = Column(String, default=lambda: datetime.now().strftime("%b %d, %Y at %I:%M %p"))
    
    user = relationship("User")

class LikedResource(Base):
    __tablename__ = "liked_resources"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    resource_id = Column(Integer, ForeignKey("resources.id"))
    
    user = relationship("User")
    resource = relationship("Resource")


class ItemRequest(Base):
    __tablename__ = "item_requests"
    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"))
    item_name = Column(String)
    category = Column(String)
    description = Column(String)
    date_required = Column(String)
    time_required = Column(String, nullable=True)
    is_fulfilled = Column(Boolean, default=False)
    expiry_date = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False)
    expiry_date = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(String, default=lambda: datetime.now().strftime("%b %d, %Y at %I:%M %p"))
    
    requester = relationship("User")

class SavedResource(Base):
    __tablename__ = "saved_resources"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    resource_id = Column(Integer, ForeignKey("resources.id"))
    
    user = relationship("User")
    resource = relationship("Resource")

class CommunityUpdate(Base):
    __tablename__ = "community_updates"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(String)
    audience = Column(String, default="all")
    event_date = Column(String)
    event_time = Column(String)
    image_url = Column(String, nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)



class RequestInterest(Base):
    __tablename__ = "request_interests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    request_id = Column(Integer, ForeignKey("item_requests.id"))

class HiddenRequest(Base):
    __tablename__ = "hidden_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    request_id = Column(Integer, ForeignKey("item_requests.id"))

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    message = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    created_at = Column(String, default=lambda: datetime.now().strftime('%Y-%m-%d %I:%M %p'))
    
    user = relationship('User')

class FriendRequest(Base):
    __tablename__ = 'friend_requests'
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey('users.id'))
    receiver_id = Column(Integer, ForeignKey('users.id'))
    status = Column(String, default='pending') # pending, accepted, rejected
    created_at = Column(String, default=lambda: datetime.now().strftime('%Y-%m-%d %I:%M %p'))

    sender = relationship('User', foreign_keys=[sender_id])
    receiver = relationship('User', foreign_keys=[receiver_id])

class PrivateMessage(Base):
    __tablename__ = 'private_messages'
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey('users.id'))
    receiver_id = Column(Integer, ForeignKey('users.id'))
    message = Column(String)
    image_url = Column(String, nullable=True)
    created_at = Column(String, default=lambda: datetime.now().strftime('%Y-%m-%d %I:%M %p'))
    
    sender = relationship('User', foreign_keys=[sender_id])
    receiver = relationship('User', foreign_keys=[receiver_id])




