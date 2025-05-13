from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock
import json

from apps.dashboard.telegram_bot import TelegramNotifier
from apps.dashboard.models import Notification

User = get_user_model()


class TelegramNotifierTest(TestCase):
    def setUp(self):
        self.notifier = TelegramNotifier()
        
        # Créer un utilisateur avec un ID Telegram
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            telegram_chat_id="123456789",
            telegram_language="fr"
        )
        
        # Créer une notification
        self.notification = Notification.objects.create(
            user=self.user,
            title="Test Notification",
            message="This is a test notification message",
            notification_type="info"
        )

    @patch('apps.dashboard.telegram_bot.requests.post')
    def test_send_message(self, mock_post):
        """Test l'envoi d'un message Telegram"""
        # Configurer le mock pour simuler une réponse réussie
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 123}}
        mock_post.return_value = mock_response
        
        result = self.notifier.send_message(
            chat_id="123456789",
            message="Test message"
        )
        
        # Vérifier que la requête a été faite correctement
        self.assertTrue(mock_post.called)
        args, kwargs = mock_post.call_args
        
        # Vérifier l'URL utilisée
        self.assertIn('sendMessage', args[0])
        
        # Vérifier les données envoyées
        data = json.loads(kwargs['data'])
        self.assertEqual(data['chat_id'], "123456789")
        self.assertEqual(data['text'], "Test message")
        self.assertEqual(data['parse_mode'], "Markdown")
        
        # Vérifier le résultat
        self.assertTrue(result)

    @patch('apps.dashboard.telegram_bot.requests.post')
    def test_send_message_failure(self, mock_post):
        """Test l'échec d'envoi d'un message Telegram"""
        # Configurer le mock pour simuler une réponse échouée
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"ok": False, "description": "Bad Request"}
        mock_post.return_value = mock_response
        
        result = self.notifier.send_message(
            chat_id="123456789",
            message="Test message"
        )
        
        # Vérifier que la requête a été faite
        self.assertTrue(mock_post.called)
        
        # Vérifier le résultat (échec)
        self.assertFalse(result)

    @patch('apps.dashboard.telegram_bot.TelegramNotifier.send_message')
    def test_format_notification(self, mock_send_message):
        """Test le formatage d'une notification pour Telegram"""
        # Configurer le mock pour éviter l'envoi réel
        mock_send_message.return_value = True
        
        formatted_message = self.notifier.format_notification(self.notification, "fr")
        
        # Vérifier que le formatage inclut le titre et le message
        self.assertIn(self.notification.title, formatted_message)
        self.assertIn(self.notification.message, formatted_message)

    @patch('apps.dashboard.telegram_bot.TelegramNotifier.send_message')
    def test_send_notification(self, mock_send_message):
        """Test l'envoi d'une notification"""
        # Configurer le mock pour éviter l'envoi réel
        mock_send_message.return_value = True
        
        result = self.notifier.send_notification(self.notification)
        
        # Vérifier que send_message a été appelé
        self.assertTrue(mock_send_message.called)
        
        # Vérifier les arguments passés à send_message
        args, kwargs = mock_send_message.call_args
        self.assertEqual(kwargs['chat_id'], self.user.telegram_chat_id)
        
        # Vérifier le résultat
        self.assertTrue(result)

    @patch('apps.dashboard.telegram_bot.TelegramNotifier.send_message')
    def test_send_commission_notification(self, mock_send_message):
        """Test l'envoi d'une notification de commission"""
        # Configurer le mock pour éviter l'envoi réel
        mock_send_message.return_value = True
        
        # Créer un utilisateur référé
        referred_user = User.objects.create_user(
            username="referred",
            email="referred@example.com",
            password="password123"
        )
        
        result = self.notifier.send_commission_notification(
            referrer=self.user,
            referred_user=referred_user,
            amount=100.0,
            total_earnings=500.0
        )
        
        # Vérifier que send_message a été appelé
        self.assertTrue(mock_send_message.called)
        
        # Vérifier les arguments passés à send_message
        args, kwargs = mock_send_message.call_args
        self.assertEqual(kwargs['chat_id'], self.user.telegram_chat_id)
        
        # Vérifier que le message contient le montant
        self.assertIn('100', kwargs['message'])
        
        # Vérifier le résultat
        self.assertTrue(result)

    @patch('apps.dashboard.telegram_bot.TelegramNotifier.send_message')
    def test_send_new_ambassador_notification(self, mock_send_message):
        """Test l'envoi d'une notification de nouvel ambassadeur"""
        # Configurer le mock pour éviter l'envoi réel
        mock_send_message.return_value = True
        
        # Créer un nouvel ambassadeur
        new_ambassador = User.objects.create_user(
            username="new_ambassador",
            email="new_ambassador@example.com",
            password="password123",
            user_type="ambassador"
        )
        
        result = self.notifier.send_new_ambassador_notification(
            referrer=self.user,
            new_user=new_ambassador
        )
        
        # Vérifier que send_message a été appelé
        self.assertTrue(mock_send_message.called)
        
        # Vérifier les arguments passés à send_message
        args, kwargs = mock_send_message.call_args
        self.assertEqual(kwargs['chat_id'], self.user.telegram_chat_id)
        
        # Vérifier que le message contient le nom d'utilisateur
        self.assertIn(new_ambassador.username, kwargs['message'])
        
        # Vérifier le résultat
        self.assertTrue(result) 