from django.contrib import messages
from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.conf import settings
from .supabase_auth import SupabaseAuth

User = get_user_model()


class CustomAccountAdapter(DefaultAccountAdapter):
    def send_confirmation_mail(self, request, emailconfirmation, signup):
        activation_url = self.get_email_confirmation_url(request, emailconfirmation)

        # Stocker le lien d'activation dans la session
        request.session["activation_url"] = activation_url
        request.session["activation_email"] = emailconfirmation.email_address.email

        # Ajouter un message pour informer l'utilisateur
        messages.info(
            request,
            f"Lien d'activation pour {emailconfirmation.email_address.email}: {activation_url}",
        )

        return None  # Ne pas envoyer d'email réel


class SupabaseAuthBackend(ModelBackend):
    """
    Authentication backend to integrate Django with Supabase Auth
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a user against Supabase Auth
        
        This handles both username and email login attempts
        """
        # Use email if provided directly
        email = kwargs.get('email', username)
        
        # If no email/username or no password, return None
        if not email or not password:
            return None
            
        # Get or create the Supabase auth client
        supabase_auth = getattr(request, 'supabase_auth', None) or SupabaseAuth()
        
        # Authenticate with Supabase
        success, data = supabase_auth.sign_in(email, password)
        
        if not success:
            return None
            
        # Get the user details
        user_data = data.get('user', {})
        user_email = user_data.get('email')
        supabase_id = user_data.get('id')
        
        if not user_email:
            return None
            
        # Try to get the user by email
        try:
            user = User.objects.get(email=user_email)
            
            # Update any necessary data from Supabase
            if hasattr(user, 'supabase_id') and not user.supabase_id:
                user.supabase_id = supabase_id
                user.save(update_fields=['supabase_id'])
                
            # Store Supabase tokens in the session
            if request and hasattr(request, 'session'):
                request.session['supabase_access_token'] = data.get('access_token')
                request.session['supabase_refresh_token'] = data.get('refresh_token')
                
            return user
            
        except User.DoesNotExist:
            # User does not exist in Django, but exists in Supabase
            # Create a new user in Django database
            user = User.objects.create_user(
                username=user_email.split('@')[0],  # Use part of email as username
                email=user_email,
                password=None  # Don't set password as it's handled by Supabase
            )
            
            # Set additional fields if available
            if hasattr(user, 'supabase_id'):
                user.supabase_id = supabase_id
                
            # Set user metadata from Supabase if available
            user_metadata = user_data.get('user_metadata', {})
            if user_metadata:
                if 'full_name' in user_metadata and hasattr(user, 'first_name') and hasattr(user, 'last_name'):
                    names = user_metadata['full_name'].split(' ', 1)
                    user.first_name = names[0]
                    user.last_name = names[1] if len(names) > 1 else ''
                elif 'first_name' in user_metadata and hasattr(user, 'first_name'):
                    user.first_name = user_metadata['first_name']
                elif 'last_name' in user_metadata and hasattr(user, 'last_name'):
                    user.last_name = user_metadata['last_name']
                    
            user.save()
            
            # Store Supabase tokens in the session
            if request and hasattr(request, 'session'):
                request.session['supabase_access_token'] = data.get('access_token')
                request.session['supabase_refresh_token'] = data.get('refresh_token')
                
            return user
    
    def get_user(self, user_id):
        """
        Get a user by primary key
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
