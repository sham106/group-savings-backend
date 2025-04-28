# from apscheduler.schedulers.background import BackgroundScheduler
# from datetime import datetime, timedelta
# from app.models.loan import Loan, LoanStatus
# from app.routes.notification_routes import create_loan_notification
# from app import db

# scheduler = BackgroundScheduler()

# def check_loan_due_dates():
#     """Check for loans due in 3 days or overdue loans"""
#     with scheduler.app.app_context():
#         try:
#             # Loans due in 3 days
#             due_soon_date = datetime.utcnow() + timedelta(days=3)
#             due_soon_loans = Loan.query.filter(
#                 Loan.status == LoanStatus.ACTIVE,
#                 Loan.due_date <= due_soon_date,
#                 Loan.due_date > datetime.utcnow()
#             ).all()
            
#             for loan in due_soon_loans:
#                 create_loan_notification(loan, 'LOAN_REMINDER', {
#                     'days_remaining': (loan.due_date - datetime.utcnow()).days
#                 })
            
#             # Overdue loans (1 day past due)
#             overdue_date = datetime.utcnow() - timedelta(days=1)
#             overdue_loans = Loan.query.filter(
#                 Loan.status == LoanStatus.ACTIVE,
#                 Loan.due_date <= overdue_date
#             ).all()
            
#             for loan in overdue_loans:
#                 loan.status = LoanStatus.DEFAULTED
#                 create_loan_notification(loan, 'LOAN_OVERDUE', {
#                     'days_overdue': (datetime.utcnow() - loan.due_date).days
#                 })
            
#             db.session.commit()
#         except Exception as e:
#             db.session.rollback()
#             scheduler.app.logger.error(f"Error in loan scheduler: {str(e)}")

# def init_loan_scheduler(app):
#     """Initialize the loan scheduler"""
#     scheduler.app = app
#     scheduler.add_job(
#         func=check_loan_due_dates,
#         trigger='interval',
#         hours=12,  # Run twice a day
#         id='loan_due_date_checker',
#         replace_existing=True
#     )
#     scheduler.start()