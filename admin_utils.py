"""
Admin utilities for UEM Placement Platform

This module provides utility functions for admin management:
- Promote users to admin status
- Create initial admin accounts
- Admin role management
"""

from models import User, db
from auth_service import AuthService
import logging

logger = logging.getLogger(__name__)

class AdminUtils:
    """Utility class for admin management"""
    
    @staticmethod
    def promote_user_to_admin(email: str) -> tuple:
        """
        Promote a user to admin status
        
        Args:
            email (str): Email of user to promote
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Find user by email
            user = User.query.filter_by(email=email.lower().strip()).first()
            if not user:
                return False, f"User with email {email} not found"
            
            # Check if already admin
            if user.is_admin:
                return False, f"User {email} is already an admin"
            
            # Promote to admin
            user.is_admin = True
            db.session.commit()
            
            logger.info(f"User promoted to admin: {email}")
            return True, f"User {email} has been promoted to admin"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error promoting user to admin: {e}")
            return False, f"Failed to promote user: {str(e)}"
    
    @staticmethod
    def demote_admin_to_user(email: str) -> tuple:
        """
        Demote an admin to regular user status
        
        Args:
            email (str): Email of admin to demote
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Find user by email
            user = User.query.filter_by(email=email.lower().strip()).first()
            if not user:
                return False, f"User with email {email} not found"
            
            # Check if is admin
            if not user.is_admin:
                return False, f"User {email} is not an admin"
            
            # Demote from admin
            user.is_admin = False
            db.session.commit()
            
            logger.info(f"Admin demoted to user: {email}")
            return True, f"Admin {email} has been demoted to regular user"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error demoting admin to user: {e}")
            return False, f"Failed to demote admin: {str(e)}"
    
    @staticmethod
    def create_admin_account(email: str, password: str, name: str) -> tuple:
        """
        Create a new admin account
        
        Args:
            email (str): Admin email (must be UEM domain)
            password (str): Admin password
            name (str): Admin name
            
        Returns:
            tuple: (success: bool, message: str, user: User or None)
        """
        try:
            # Register user first
            success, message, user = AuthService.register_user(email, password, name)
            
            if not success:
                return False, message, None
            
            # Promote to admin
            user.is_admin = True
            db.session.commit()
            
            logger.info(f"Admin account created: {email}")
            return True, f"Admin account created successfully for {email}", user
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating admin account: {e}")
            return False, f"Failed to create admin account: {str(e)}", None
    
    @staticmethod
    def list_admins() -> list:
        """
        Get list of all admin users
        
        Returns:
            list: List of admin users
        """
        try:
            admins = User.query.filter_by(is_admin=True).all()
            return [admin.to_dict() for admin in admins]
            
        except Exception as e:
            logger.error(f"Error listing admins: {e}")
            return []
    
    @staticmethod
    def check_admin_exists() -> bool:
        """
        Check if any admin accounts exist
        
        Returns:
            bool: True if at least one admin exists
        """
        try:
            admin_count = User.query.filter_by(is_admin=True).count()
            return admin_count > 0
            
        except Exception as e:
            logger.error(f"Error checking admin existence: {e}")
            return False
    
    @staticmethod
    def create_default_admin_if_none_exists():
        """
        Create a default admin account if no admins exist
        This should only be used for initial setup
        """
        try:
            if not AdminUtils.check_admin_exists():
                # Create default admin with environment variables or defaults
                import os
                default_email = os.environ.get('DEFAULT_ADMIN_EMAIL', 'admin@uem.edu.in')
                default_password = os.environ.get('DEFAULT_ADMIN_PASSWORD', 'admin123')
                default_name = os.environ.get('DEFAULT_ADMIN_NAME', 'System Administrator')
                
                success, message, user = AdminUtils.create_admin_account(
                    default_email, 
                    default_password, 
                    default_name
                )
                
                if success:
                    logger.info(f"Default admin account created: {default_email}")
                    print(f"Default admin account created: {default_email}")
                    print(f"Password: {default_password}")
                    print("Please change the password after first login!")
                else:
                    logger.error(f"Failed to create default admin: {message}")
                    
        except Exception as e:
            logger.error(f"Error creating default admin: {e}")


def promote_user_cli():
    """
    Command line interface for promoting users to admin
    This can be run as a standalone script
    """
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python admin_utils.py <email>")
        print("Example: python admin_utils.py professor@uem.edu.in")
        return
    
    email = sys.argv[1]
    
    # Initialize Flask app context
    from app import app
    with app.app_context():
        success, message = AdminUtils.promote_user_to_admin(email)
        print(message)
        
        if success:
            print(f"✓ {email} is now an admin")
        else:
            print(f"✗ Failed to promote {email}")


if __name__ == '__main__':
    promote_user_cli()