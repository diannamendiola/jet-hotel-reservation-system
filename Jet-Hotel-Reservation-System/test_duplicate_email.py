from app import app
from models import db, User
from werkzeug.security import generate_password_hash

def test_duplicate_email_validation():
    with app.test_client() as client:
        with app.app_context():
            # First, create a test user
            test_user = User(
                full_name="Test User",
                email="duplicate@gmail.com",
                contact_info="1234567890",
                password=generate_password_hash("TestPass123!")
            )
            db.session.add(test_user)
            db.session.commit()

            # Now try to register with the same email
            response = client.post('/register', data={
                'full_name': 'Another User',
                'email': 'duplicate@gmail.com',
                'contact_info': '0987654321',
                'password': 'AnotherPass123!',
                'confirm_password': 'AnotherPass123!'
            })

            if 'This email is already registered' in response.get_data(as_text=True):
                print('✓ Duplicate email validation working correctly')
                return True
            else:
                print('✗ Duplicate email validation not working')
                print('Response status:', response.status_code)
                print('Response data:', response.get_data(as_text=True))
                return False

if __name__ == '__main__':
    test_duplicate_email_validation()
