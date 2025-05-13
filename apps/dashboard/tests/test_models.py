from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from apps.dashboard.models import Notification

User = get_user_model()


class NotificationTest(TestCase):
    """Tests pour le modèle Notification."""
    
    def setUp(self):
        """Préparer les données de test."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
            user_type="escort"
        )
        
        self.notification = Notification.objects.create(
            user=self.user,
            title="Test Notification",
            message="This is a test notification",
            notification_type="info",
            is_read=False
        )
    
    def test_notification_creation(self):
        """Tester la création d'une notification."""
        self.assertEqual(self.notification.user, self.user)
        self.assertEqual(self.notification.title, "Test Notification")
        self.assertEqual(self.notification.message, "This is a test notification")
        self.assertEqual(self.notification.notification_type, "info")
        self.assertFalse(self.notification.is_read)
        
        # Vérifier que la date de création est correcte
        self.assertIsNotNone(self.notification.created_at)
        self.assertTrue((timezone.now() - self.notification.created_at) < timedelta(minutes=1))
    
    def test_notification_str_method(self):
        """Tester la méthode __str__ du modèle Notification."""
        self.assertEqual(str(self.notification), "Test Notification")
    
    def test_notification_mark_as_read(self):
        """Tester le marquage d'une notification comme lue."""
        self.assertFalse(self.notification.is_read)
        
        # Marquer comme lue
        self.notification.is_read = True
        self.notification.save()
        
        # Récupérer la notification depuis la base de données
        refreshed_notification = Notification.objects.get(id=self.notification.id)
        self.assertTrue(refreshed_notification.is_read)
    
    def test_notification_get_notification_type_display(self):
        """Tester l'affichage du type de notification."""
        # Créer différents types de notifications
        info_notif = self.notification  # Déjà créée avec type 'info'
        
        success_notif = Notification.objects.create(
            user=self.user,
            title="Success Notification",
            message="This is a success notification",
            notification_type="success",
            is_read=False
        )
        
        warning_notif = Notification.objects.create(
            user=self.user,
            title="Warning Notification",
            message="This is a warning notification",
            notification_type="warning",
            is_read=False
        )
        
        error_notif = Notification.objects.create(
            user=self.user,
            title="Error Notification",
            message="This is an error notification",
            notification_type="error",
            is_read=False
        )
        
        # Vérifier les types
        self.assertEqual(info_notif.notification_type, "info")
        self.assertEqual(success_notif.notification_type, "success")
        self.assertEqual(warning_notif.notification_type, "warning")
        self.assertEqual(error_notif.notification_type, "error")
    
    def test_notification_types(self):
        """Test les différents types de notifications"""
        # Créer des notifications avec différents types
        info_notification = Notification.objects.create(
            user=self.user,
            title="Info Notification",
            message="This is an info notification",
            notification_type="info"
        )
        
        success_notification = Notification.objects.create(
            user=self.user,
            title="Success Notification",
            message="This is a success notification",
            notification_type="success"
        )
        
        warning_notification = Notification.objects.create(
            user=self.user,
            title="Warning Notification",
            message="This is a warning notification",
            notification_type="warning"
        )
        
        error_notification = Notification.objects.create(
            user=self.user,
            title="Error Notification",
            message="This is an error notification",
            notification_type="error"
        )
        
        system_notification = Notification.objects.create(
            user=self.user,
            title="System Notification",
            message="This is a system notification",
            notification_type="system"
        )
        
        # Vérifier que tous les types sont corrects
        self.assertEqual(info_notification.notification_type, "info")
        self.assertEqual(success_notification.notification_type, "success")
        self.assertEqual(warning_notification.notification_type, "warning")
        self.assertEqual(error_notification.notification_type, "error")
        self.assertEqual(system_notification.notification_type, "system")
    
    def test_filter_unread_notifications(self):
        """Test le filtrage des notifications non lues"""
        # Créer quelques notifications supplémentaires
        Notification.objects.create(
            user=self.user,
            title="Read Notification",
            message="This notification is already read",
            notification_type="info",
            is_read=True
        )
        
        Notification.objects.create(
            user=self.user,
            title="Unread Notification",
            message="This notification is not read",
            notification_type="info",
            is_read=False
        )
        
        # Récupérer les notifications non lues
        unread_notifications = Notification.objects.filter(user=self.user, is_read=False)
        
        # Vérifier qu'il y a exactement 2 notifications non lues
        self.assertEqual(unread_notifications.count(), 2)
        
        # Marquer toutes les notifications comme lues
        Notification.objects.filter(user=self.user).update(is_read=True)
        
        # Vérifier qu'il n'y a plus de notifications non lues
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0) 