from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
from core.models import Category, CategoryService
import uuid
from datetime import datetime
from datetime import date

from django.utils import timezone
# user manager


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.SUPERADMIN)

        return self.create_user(email, password, **extra_fields)


# user model table

class User(AbstractUser):

    username = None

    class Role(models.TextChoices):
        SUPERADMIN = "superadmin", "Super Admin"
        ADMIN = "admin", "Admin"
        VENDOR = "vendor", "Vendor"
        CUSTOMER = "customer", "Customer"

    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    role = models.CharField(max_length=20,choices=Role.choices,default=Role.CUSTOMER)
    services = models.ManyToManyField(
        "core.CategoryService", blank=True, related_name="vendors")

    created_by = models.ForeignKey("self",on_delete=models.SET_NULL,null=True,
        blank=True,
        related_name="created_users"
    )
    user_created_at = models.DateTimeField(auto_now_add=True)
    user_updated_at = models.DateTimeField(auto_now=True)
    state = models.CharField(max_length=100,blank=True,null=True)
    district = models.CharField(max_length=100,blank=True,null=True)
    city = models.CharField(max_length=100,blank=True,null=True)
    area = models.CharField(max_length=150,blank=True,null=True)
    pincode = models.CharField(max_length=10,blank=True,null=True)
    address = models.TextField(blank=True,null=True)
    profile_image = models.ImageField(upload_to="profile_images/",null=True,blank=True)
    BEHAVIOUR = (
    ("good", "Good"),
    ("average", "Average"),
    ("bad", "Bad"),
    ("normal", "Normal"),)

    behaviour = models.CharField(max_length=20,choices=BEHAVIOUR,default="normal")
    behaviour_note = models.TextField(blank=True,null=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "phone"]

    objects = UserManager()

    def __str__(self):
        return f"{self.email} ({self.role})"



def generate_order_id():
    return "SDXETS" + uuid.uuid4().hex[:6].upper()

# bookings


# class AbstractModel(models.Model):
#     created_at = DT
#     updated_at = DT
#     created_by = User
#     updated_by = User
#     is_deleted  = bool
#     class Meta:
#         abstract = Tr

# class Booking(AbstractModel):



class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='cart')
    session_key = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(user__isnull=False) | models.Q(session_key__isnull=False),
                name='cart_user_or_session'
            )
        ]

    def __str__(self):
        return f"Cart - {self.user.email if self.user else self.session_key}"

    @property
    def total_items(self):
        return self.items.count()


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    service = models.ForeignKey(CategoryService, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'service')

    def __str__(self):
        return f"{self.service.s_title} in Cart {self.cart.id}"


class Booking(models.Model):
    STATUS = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    admin = models.ForeignKey(User,on_delete=models.SET_NULL,
    null=True,blank=True,related_name="admin_bookings",limit_choices_to={"role": "admin"})
    
    order_id = models.CharField(max_length=20,unique=True,editable=False,default=generate_order_id)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    problem = models.TextField(blank=True, null=True) # Optional now, since it might vary per service
    status = models.CharField(max_length=20,choices=STATUS,default='pending')
    city = models.CharField(max_length=100,blank=True,null=True)
    estimated_amount = models.IntegerField(default=0)
  
    # -------------------------------------------------------------
    # DEPRECATED FIELDS: Kept for backwards compatibility
    # since old views still reference them directly on Booking.
    # -------------------------------------------------------------
    category = models.ForeignKey(Category,on_delete=models.SET_NULL, null=True, blank=True)
    service = models.ForeignKey(CategoryService,on_delete=models.SET_NULL, null=True, blank=True)
    vendor = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="deprecated_vendor_bookings")
    scheduled_date = models.DateField(null=True,blank=True)
    scheduled_time = models.CharField(max_length=50,null=True,blank=True)
    start_date = models.DateField(null=True,blank=True)
    end_date = models.DateField(null=True,blank=True)
    renewal_requested = models.BooleanField(default=False)
    is_renewed = models.BooleanField(default=False)
    previous_total_days = models.IntegerField(null=True,blank=True)
    renewal_count = models.IntegerField(default=0)
    # -------------------------------------------------------------

    booking_created_at = models.DateTimeField(auto_now_add=True)
    booking_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order_id} - {self.name}"

    # properties kept for legacy code compatibility during transition
    @property
    def total_days(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0

    @property
    def show_renew_button(self):
        if self.end_date:
            from datetime import datetime
            end_date = self.end_date
            if isinstance(end_date, datetime):
                end_date = end_date.date()
            today = datetime.today().date()
            remaining_days = (end_date - today).days
            return 0 <= remaining_days <= 10
        return False


class BookingItem(models.Model):
    ITEM_STATUS = (
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='items')
    service = models.ForeignKey(CategoryService, on_delete=models.CASCADE, related_name='booking_items')
    vendor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_booking_items")
    
    status = models.CharField(max_length=20, choices=ITEM_STATUS, default='pending')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # single day 
    scheduled_date = models.DateField(null=True,blank=True)
    scheduled_time = models.CharField(max_length=50,null=True,blank=True)
    # multiple day service 
    start_date = models.DateField(null=True,blank=True)
    end_date = models.DateField(null=True,blank=True)
    renewal_requested = models.BooleanField(default=False)
    is_renewed = models.BooleanField(default=False)
    previous_total_days = models.IntegerField(null=True,blank=True)
    renewal_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.booking.order_id} - {self.service.s_title}"

    @property
    def total_days(self):
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0

    @property
    def show_renew_button(self):
        if self.end_date:
            end_date = self.end_date
            if isinstance(end_date, datetime):
                end_date = end_date.date()
            today = datetime.today().date()
            remaining_days = (end_date - today).days
            return 0 <= remaining_days <= 10
        return False
    
# booking history(track the order)
class BookingHistory(models.Model):

    booking = models.ForeignKey(Booking,on_delete=models.CASCADE,related_name="history")
    status = models.CharField(max_length=20)
    updated_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True)
    service_days = models.IntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.booking.order_id} - {self.status}"


# payments
class Payment(models.Model):
    
    booking = models.ForeignKey(Booking,on_delete=models.CASCADE,related_name="payments")
    vendor = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True)
    service = models.ForeignKey(CategoryService,on_delete=models.CASCADE,null=True,blank=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("partial_paid","Partial_Paid"),
            ("paid", "Paid"),
        ],
        default="pending"
    )
        
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    remaining_amount = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    screenshot = models.ImageField(upload_to="payments/",blank=True,null=True)
    PAYMENT_METHOD = (
    ('Cash', 'Cash'),
    ('Card', 'Card'),
    ('Online', 'Online'),
    ('UPI', 'UPI'),
)
    payment_request = models.TextField(blank=True,null=True)
    due_date = models.DateField(blank=True,null=True)
    reminder_sent = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=20,choices=PAYMENT_METHOD,default='Cash')
    payment_created_at = models.DateTimeField(auto_now_add=True)
    payment_updated_at = models.DateTimeField(auto_now=True)

    @property
    def due_amount(self):
        return self.amount - self.paid_amount

    def is_due_soon(self):
        return (timezone.now().date() - self.created_at.date()).days >= 25
    def __str__(self):
        return f"{self.booking.order_id} - {self.status}"



    def save(self, *args, **kwargs):

        self.remaining_amount = (
        self.total_amount - self.paid_amount
    )
        super().save(*args, **kwargs)
        
        

# vendor profile    
class VendorProfile(models.Model):
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="vendor_profile")
    experience = models.PositiveIntegerField(help_text="Years of experience")
    locality = models.CharField(max_length=200, db_index=True)
    street = models.CharField(max_length=200)
    city = models.CharField(max_length=100, db_index=True)
    postal_code = models.CharField(max_length=10, db_index=True)
    company_name = models.CharField(max_length=200, blank=True)
    company_address = models.TextField(blank=True)
    category = models.ForeignKey(Category,on_delete=models.SET_NULL,null=True,related_name="vendor_profiles")
    services = models.ManyToManyField(CategoryService,blank=True,related_name="vendor_profiles")
    is_verified = models.BooleanField(default=False)
    rating = models.FloatField(default=0)
    total_jobs = models.IntegerField(default=0)
    profile_created_at = models.DateTimeField(auto_now_add=True)
    profile_updated_at = models.DateTimeField(auto_now=True)
    pan_number = models.CharField(max_length=30,null=True,blank=True)
    pan_card = models.FileField(upload_to="vendor/pan/",null=True,blank=True)
    license_number = models.CharField(max_length=50,null=True,blank=True)
    license_file = models.FileField(upload_to="vendor/license/",null=True,blank=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True,blank=True)

    def __str__(self):
        return f"{self.user.email} - VendorProfile"


class CustomerRemark(models.Model):

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
    ]

    booking = models.ForeignKey("Booking",on_delete=models.CASCADE,related_name="remarks")
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="customer_remarks")
    vendor = models.ForeignKey(User,on_delete=models.CASCADE,related_name="vendor_remarks")
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_complaints"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.status}"
    
    


# notifications in all users  
class Notification(models.Model):

    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="notifications")
    booking = models.ForeignKey(Booking,on_delete=models.CASCADE,null=True,blank=True)
    payment = models.ForeignKey(Payment,on_delete=models.CASCADE,null=True,blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:

        ordering = ['-id']
        
        
        
        



# terms and conditions

class TermsAcceptance(models.Model):

    customer = models.ForeignKey(User,on_delete=models.CASCADE,related_name="terms_acceptances")
    booking = models.ForeignKey("Booking",on_delete=models.CASCADE,null=True,blank=True)
    signature = models.ImageField(upload_to="signatures/")
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):

        return self.customer.email
    


    class Meta:
        permissions = [
            ("manage_news",
             "Can Manage News"),
            
            ("manage_hero_section",
             "Can Manage Hero Section"),
            
            ("manage_categories",
             "Can Manage Categories"),
            
            ("manage_categories_service",
             "Can Manage Categories Service"),
            
            ("manage_service",
             "Can Manage Service"),
            
            ("manage_jobs",
             "Can Manage Jobs"),
            
            ("manage_job_application",
             "Can Manage Job Application"),
            
            ("manage_feedback",
             "Can Manage Feedback"),
            
            ("manage_inquery_contact",
             "Can Manage Inquery Contact"),
            
            ("manage_footer",
             "Can Manage Footer"),
            
            
        ]







class Visitor(models.Model):

    ip_address = models.GenericIPAddressField(unique=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    browser = models.CharField(max_length=100, blank=True, null=True)
    device = models.CharField(max_length=100, blank=True, null=True)
    operating_system = models.CharField(max_length=100, blank=True, null=True)
    page_url = models.TextField(blank=True)

    visited_at = models.DateTimeField(auto_now=True)

    def __str__(self):

        return f"{self.ip_address} - {self.city}"




class OTP(models.Model):

    phone = models.CharField(max_length=10)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.phone
  