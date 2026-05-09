# Ticketsathi Project Study Report

This document is a comprehensive technical breakdown of the **Ticketsathi** Django application. It is designed to provide you with all the necessary technical details and implementation specifics to confidently discuss the project with your supervisor.

---

## 1. User Features & Implementation

### A. Authentication & User Management

- **Feature:** Users can create accounts, log in, and securely manage their sessions.
- **Implementation:** Utilizes Django's built-in authentication system (`django.contrib.auth`). Views use standard forms (`SignUpForm`, `LoginForm`), and routes that require authorization are protected using the `@login_required` decorator.

### B. Browsing Movies & Showtimes

- **Feature:** Users can see "Now Showing" vs "Coming Soon" movies, filter by genre, and search. They can click a movie to see available showtimes across various cinemas.
- **Implementation:** The `home` and `movies_list` views query the `Movie` model. The `movie_detail` view aggregates `Showtime` instances linked to the selected movie and filters them dynamically based on the requested date and `Cinema`. YouTube trailer URLs use custom Regex logic in the `Movie` model to safely extract the embed ID.

### C. Seat Selection & Reservation

- **Feature:** Users see a grid of seats and can pick available ones (Regular, Premium, VIP).
- **Implementation:** Handled by the `select_seats` view. The system checks the `SeatBooking` intermediate model for a specific `Showtime` to see which seats have `is_booked=True`. When a user selects seats and proceeds, the view immediately sets `is_booked=True` for those seats to temporarily hold them and prevent race conditions (double bookings by another user at the exact same time).

### D. Multi-Gateway Payment Processing

- **Feature:** Users can pay via Card, eSewa, Khalti, or FonePay.
- **Implementation:** The `process_payment` view routes the request to a custom-built modular payment SDK (`booking.payments` folder). It initiates an API request to the chosen gateway, redirects the user, and waits for the gateway to ping back the `@csrf_exempt` decorated `payment_callback` view to cryptographically verify the transaction.

### E. E-Ticket Generation

- **Feature:** Upon confirmed payment, users receive a digital ticket with a scannable QR code.
- **Implementation:** Handled by the `booking_confirmation` view. It stitches together the booking reference, movie title, time, and seat numbers into a string, and uses the Python `qrcode` library to generate a base64 or static image representation of the ticket.

### F. Cancellation Requests

- **Feature:** Users can request to cancel their tickets by providing a reason (minimum 10 characters).
- **Implementation:** The `cancel_booking` view creates a `CancellationRequest` linked to the `Booking`. The system blocks multiple requests for the same booking using the `can_request_cancellation()` model method.

---

## 2. Administrator Features & Implementation

### A. System Dashboard

- **Feature:** Secure backend for staff to manage the entire database.
- **Implementation:** Heavily leverages the built-in `django.contrib.admin` interface. Models are registered in `admin.py` with custom `ModelAdmin` classes to provide search, filtering (e.g., `list_filter = ['is_now_showing', 'rating']`), and inline editing (like adding multiple `MovieImage` gallery photos directly from the `Movie` edit page).

### B. Cinema, Screen, and Showtime Scheduling

- **Feature:** Admins define the physical layout of the business (Cinemas -> Screens -> Seats) and link Movies to those Screens at specific times.
- **Implementation:** Strictly enforced relational integrity. `Showtime` is the junction model that ties together a `Movie`, a `Screen`, a start/end time, and a base `price`.

### C. Booking & Refund Management

- **Feature:** Admins process user cancellation requests, refunding money and freeing up seats.
- **Implementation:** In `admin.py`, a custom Django Admin Action called `approve_cancellation` is defined. When an admin selects a pending request and clicks approve:
  1. The booking logic sets `status = 'Cancelled'`.
  2. The payment record is updated to `Refunded`.
  3. _Crucially_, it runs `seat_bookings.update(is_booked=False, booking=None)` to instantly release the physical seats back into the pool for other customers to buy.

---

## 3. Technology Stack Breakdown

| Technology                    | Purpose                | Why it was chosen (For your Supervisor)                                                                                                                                                   |
| :---------------------------- | :--------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Django 5.2 (Python 3.10+)** | Core Backend Framework | Provides rapid development, built-in robust security measures against SQL Injection and XSS, and an out-of-the-box admin panel which saved weeks of custom development time.              |
| **MySQL**                     | Relational Database    | Highly scalable and reliable for transactional data (like booking ledgers and payment logs). Connected via `mysqlclient`.                                                                 |
| **HTML5 / CSS3 / Vanilla JS** | Frontend Interfaces    | Server-Side Rendering (SSR) via Django Templates ensures incredibly fast initial page loads and excellent SEO without the overhead of heavy SPA frameworks like React.                    |
| **python-dotenv**             | Environment Management | Essential security best practice. Ensures that sensitive production variables (like `SECRET_KEY`, Database Passwords, and Payment API Secrets) are never hardcoded in the Git repository. |
| **Pillow & qrcode**           | Media Processing       | `Pillow` handles automatic processing of uploaded movie posters and banners. `qrcode` dynamically generates secure, scannable E-Tickets strictly from backend verified data.              |

---

## 4. Crucial Talking Points for Your Supervisor

If your supervisor asks complex architectural questions, here are the exact answers based on your codebase:

**Q: "How do you prevent two users from booking the exact same seat at the exact same time?"**

> **A:** _"We handle race conditions defensively. The moment a user clicks 'Proceed to Payment' in the `select_seats` view, the system immediately fires an `update_or_create` query to the `SeatBooking` junction table, flipping `is_booked` to `True` for those specific seats. This temporarily locks the seats system-wide while they are interacting with the Payment Gateway, guaranteeing no one else can grab them."_

**Q: "How is the payment integration architected? Is it scalable?"**

> **A:** _"Yes, it follows the Open-Closed Principle. Instead of cramming all API logic into `views.py`, we built a modular payment SDK in the `booking/payments/` directory. It uses abstract interfaces (`PaymentRequest`, `VerifyRequest`). eSewa, Khalti, and FonePay all implement their own specific `Provider` classes. If we need to add 'Stripe' tomorrow, we just drop in a new `stripe.py` provider without touching the core checkout views."_

**Q: "Why is the payment callback view marked with `@csrf_exempt`?"**

> **A:** _"Because the payment verification callback is an external server-to-server POST request originating from the gateway (like eSewa's servers). They do not possess the browser's internal CSRF token. We bypass Django's CSRF exclusively for that one endpoint and instead rely on cryptographic signature verification of the payload inside our Provider module to ensure the request is authentically from the bank."_

**Q: "How is seat releasing handled during a refund?"**

> **A:** _"It's handled via a bulk atomic database operation. Attached to the Django Admin is a custom action model method for cancellations. When a staff member approves a cancellation, it runs a `.update(is_booked=False, booking=None)` query across all tied `SeatBooking` rows, which immediately synchronizes the public seat map without requiring server restarts or manual seat un-checking."_
