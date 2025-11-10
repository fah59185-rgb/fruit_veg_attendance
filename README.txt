
Fruit & Vegetable — Simple Attendance Web App
===========================================

What this is
- A small Flask app that allows employees to mark IN/OUT via unique links and an admin dashboard to view/export records.
- Prepopulated employees: Ch. Aswad, Muhammad Noor, Waheed Khan, Muhammad Amir, Rashid Khan, Saad, Zohaib Shah.

How to run locally
1. Unzip the package.
2. Create a Python virtualenv and install Flask:
   python -m venv venv
   source venv/bin/activate  # (or venv\Scripts\activate on Windows)
   pip install flask
3. (Optional) Change admin password:
   export FV_ADMIN_PASSWORD="yourpassword"
   export FV_SECRET_KEY="a-secure-secret"
4. Run:
   python app.py
5. Open:
   - Employee links (example): http://127.0.0.1:5000/link/token_aswad
   - Admin login: http://127.0.0.1:5000/admin  (default password: admin123)

Notes
- The map link you provided: https://maps.app.goo.gl/t4W8NYx4Y17dvGMd9 has been added to the homepage for reference.
- For production deployment consider using a proper WSGI server (gunicorn), HTTPS, and secure environment variables.
