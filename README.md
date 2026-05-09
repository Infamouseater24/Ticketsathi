# Ticketsathi - Cinema Booking System

Ticketsathi is a comprehensive web-based Cinema Booking System built with Django. It provides an intuitive interface for users to browse movies, check showtimes, select seats, and book tickets seamlessly. It also integrates multiple payment gateways to offer a variety of payment options.

## Features

### For Users

- **User Authentication**: Secure signup, login, and logout functionalities.
- **Movie Browsing**: View currently showing movies, upcoming releases, and detailed information about each movie including trailers and posters.
- **Showtimes & Cinemas**: Browse available showtimes across different cinemas and screens.
- **Interactive Seat Selection**: Visual seat map allowing users to select available seats categorized by type (Regular, Premium, VIP).
- **Booking & Payments**:
  - Book multiple seats for a showtime.
  - Integration with multiple payment gateways:
    - **eSewa**
    - **Khalti**
    - **FonePay**
    - **Credit/Debit Card**
- **Manage Bookings**: Users can view their past and upcoming bookings.
- **Cancellation Requests**: Users can request to cancel their bookings directly from the dashboard.

### For Administrators

- **Django Admin Panel**: Comprehensive admin interface to manage the entire system.
- **Cinema & Screen Management**: Add and configure cinemas, screens, and seating arrangements.
- **Movie Management**: Add movies, set durations, genres, upload posters/banners, and link trailers.
- **Showtime Scheduling**: Schedule showtimes for movies on specific screens with pricing.
- **Booking Overview**: Monitor all bookings and payment statuses.
- **Manage Cancellations**: Review and approve/reject user cancellation requests and process refunds.

## Technologies Used

- **Backend**: Django 5.2 (Python)
- **Database**: MySQL
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (Django Templates)
- **Environment Management**: `python-dotenv` for managing environment variables

## Setup and Installation

### Prerequisites

- Python 3.10+
- MySQL Server
- Git

### Local Development Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/Infamouseater24/Ticketsathi.git
   cd Ticketsathi
   ```

2. **Create a virtual environment and activate it**

   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the project directory (alongside `manage.py`) and add your configuration details. See `.env.example` (or configure these keys):

   ```env
   SECRET_KEY=your_django_secret_key
   DEBUG=True
   ALLOWED_HOSTS=127.0.0.1,localhost

   DB_NAME=cinema_booking_db
   DB_USER=root
   DB_PASSWORD=your_mysql_password
   DB_HOST=127.0.0.1
   DB_PORT=3306
   ```

5. **Database Setup**
   Ensure your MySQL server is running and create the database `cinema_booking_db`.

   ```sql
   CREATE DATABASE cinema_booking_db;
   ```

6. **Apply Migrations**

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

7. **Create a Superuser (Admin)**

   ```bash
   python manage.py createsuperuser
   ```

8. **Run the Development Server**
   ```bash
   python manage.py runserver
   ```
   Access the website at `http://127.0.0.1:8000/` and the admin panel at `http://127.0.0.1:8000/admin/`.

## Project Structure

- `cinema_booking/`: The core Django project directory containing settings, routing, and WSGI/ASGI configurations.
- `booking/`: The main application handling the core business logic (models, views, templates).
  - `payments/`: Modular integration for different payment gateways (eSewa, Khalti, FonePay).
  - `templates/booking/`: HTML templates for the frontend.
- `media/`: Directory for user-uploaded files like movie posters and banners.
- `static/`: Directory for static assets like CSS, JS, and global images.

## Payment Gateways config

Payment gateway keys and secrets (like Khalti Secret Key, eSewa Merchant ID, etc.) would need to be configured safely inside `.env` or Django settings for production environments.

## License

MIT License
