from app import create_app

app = create_app()
# with app.app_context():
#     from app.models import User
#     u = User.query.filter_by(username='admin').first()
#     print('User:', u)
#     print('Roles:', u.roles if u else 'N/A')
#     print('is_admin:', u.is_admin if u else 'N/A')
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=app.config["DEBUG"])
