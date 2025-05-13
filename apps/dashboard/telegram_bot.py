import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Messages multilingues pour les notifications
NOTIFICATION_TEMPLATES = {
    # Notification nouvel ambassadeur
    "new_ambassador": {
        "en": {
            "title": "🎉 Done! Congratulations! 🎊",
            "content": "🚀 A new ambassador has joined using your referral link!\n\n"
            "👤 Username: {username}\n"
            "📅 Joined: {date_joined}\n\n"
            "🔗 Your affiliate network is growing! Keep up the good work! 💪",
        },
        "fr": {
            "title": "🎉 Félicitations ! 🎊",
            "content": "🚀 Un nouvel ambassadeur s'est inscrit avec votre lien de parrainage !\n\n"
            "👤 Nom d'utilisateur : {username}\n"
            "📅 Inscription : {date_joined}\n\n"
            "🔗 Votre réseau d'affiliation grandit ! Continuez comme ça ! 💪",
        },
        "ru": {
            "title": "🎉 Поздравляем! 🎊",
            "content": "🚀 Новый амбассадор присоединился по вашей реферальной ссылке!\n\n"
            "👤 Имя пользователя: {username}\n"
            "📅 Дата регистрации: {date_joined}\n\n"
            "🔗 Ваша партнерская сеть растет! Так держать! 💪",
        },
        "de": {
            "title": "🎉 Gut gemacht! Herzlichen Glückwunsch! 🎊",
            "content": "🚀 Ein neuer Botschafter hat sich über Ihren Empfehlungslink angemeldet!\n\n"
            "👤 Benutzername: {username}\n"
            "📅 Beigetreten: {date_joined}\n\n"
            "🔗 Ihr Partnernetzwerk wächst! Weiter so! 💪",
        },
        "zh": {
            "title": "🎉 恭喜您！ 🎊",
            "content": "🚀 新大使已通过您的推荐链接加入！\n\n"
            "👤 用户名：{username}\n"
            "📅 加入时间：{date_joined}\n\n"
            "🔗 您的联盟网络正在增长！继续加油！ 💪",
        },
        "es": {
            "title": "🎉 ¡Felicidades! 🎊",
            "content": "🚀 ¡Un nuevo embajador se ha unido usando tu enlace de referido!\n\n"
            "👤 Usuario: {username}\n"
            "📅 Se unió: {date_joined}\n\n"
            "🔗 ¡Tu red de afiliados está creciendo! ¡Sigue así! 💪",
        },
    },
    # Notification nouvelle commission
    "new_commission": {
        "en": {
            "title": "🎉 New Commission! 💰",
            "content": "You've earned {amount}€ from {username}'s payment.\n\n"
            "Total earnings from this user: {total}€",
        },
        "fr": {
            "title": "🎉 Nouvelle Commission ! 💰",
            "content": "Vous avez gagné {amount}€ grâce au paiement de {username}.\n\n"
            "Gains totaux provenant de cet utilisateur : {total}€",
        },
        "ru": {
            "title": "🎉 Новая комиссия! 💰",
            "content": "Вы заработали {amount}€ с платежа {username}.\n\n"
            "Общий доход от этого пользователя: {total}€",
        },
        "de": {
            "title": "🎉 Neue Provision! 💰",
            "content": "Sie haben {amount}€ durch die Zahlung von {username} verdient.\n\n"
            "Gesamteinnahmen von diesem Benutzer: {total}€",
        },
        "zh": {
            "title": "🎉 新的佣金! 💰",
            "content": "您已从{username}的付款中赚取{amount}€。\n\n来自该用户的总收入：{total}€",
        },
        "es": {
            "title": "🎉 ¡Nueva comisión! 💰",
            "content": "Has ganado {amount}€ del pago de {username}.\n\n"
            "Ganancias totales de este usuario: {total}€",
        },
    },
}


class TelegramNotifier:
    """
    Classe pour envoyer des notifications via Telegram
    """

    def __init__(self):
        self.api_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
        self.api_url = f"https://api.telegram.org/bot{self.api_token}/sendMessage"

        # Traductions pour différentes langues
        self.translations = {
            "fr": {
                "new_referral": "🎉 Nouvel affilié!",
                "new_commission": "💰 Nouvelle commission!",
                "payout_processed": "💸 Versement traité!",
                "account_verified": "✅ Compte vérifié!",
                "welcome": "👋 Bienvenue!",
                "info": "ℹ️ Information",
                "warning": "⚠️ Avertissement",
                "error": "❌ Erreur",
                "test": "🔔 Test de notification",
            },
            "en": {
                "new_referral": "🎉 New referral!",
                "new_commission": "💰 New commission!",
                "payout_processed": "💸 Payout processed!",
                "account_verified": "✅ Account verified!",
                "welcome": "👋 Welcome!",
                "info": "ℹ️ Information",
                "warning": "⚠️ Warning",
                "error": "❌ Error",
                "test": "🔔 Notification test",
            },
            "es": {
                "new_referral": "🎉 ¡Nuevo afiliado!",
                "new_commission": "💰 ¡Nueva comisión!",
                "payout_processed": "💸 ¡Pago procesado!",
                "account_verified": "✅ ¡Cuenta verificada!",
                "welcome": "👋 ¡Bienvenido!",
                "info": "ℹ️ Información",
                "warning": "⚠️ Advertencia",
                "error": "❌ Error",
                "test": "🔔 Prueba de notificación",
            },
            "de": {
                "new_referral": "🎉 Neue Überweisung!",
                "new_commission": "💰 Neue Provision!",
                "payout_processed": "💸 Auszahlung bearbeitet!",
                "account_verified": "✅ Konto verifiziert!",
                "welcome": "👋 Willkommen!",
                "info": "ℹ️ Information",
                "warning": "⚠️ Warnung",
                "error": "❌ Fehler",
                "test": "🔔 Benachrichtigungstest",
            },
            "it": {
                "new_referral": "🎉 Nuovo referral!",
                "new_commission": "💰 Nuova commissione!",
                "payout_processed": "💸 Pagamento elaborato!",
                "account_verified": "✅ Account verificato!",
                "welcome": "👋 Benvenuto!",
                "info": "ℹ️ Informazione",
                "warning": "⚠️ Avvertimento",
                "error": "❌ Errore",
                "test": "🔔 Test di notifica",
            },
            "ru": {
                "new_referral": "🎉 Новый реферал!",
                "new_commission": "💰 Новая комиссия!",
                "payout_processed": "💸 Платеж обработан!",
                "account_verified": "✅ Аккаунт подтвержден!",
                "welcome": "👋 Добро пожаловать!",
                "info": "ℹ️ Информация",
                "warning": "⚠️ Предупреждение",
                "error": "❌ Ошибка",
                "test": "🔔 Тестовое уведомление",
            },
            "ar": {
                "new_referral": "🎉 إحالة جديدة!",
                "new_commission": "💰 عمولة جديدة!",
                "payout_processed": "💸 تمت معالجة الدفع!",
                "account_verified": "✅ تم التحقق من الحساب!",
                "welcome": "👋 مرحبًا!",
                "info": "ℹ️ معلومات",
                "warning": "⚠️ تحذير",
                "error": "❌ خطأ",
                "test": "🔔 اختبار الإشعار",
            },
            "zh": {
                "new_referral": "🎉 新推荐!",
                "new_commission": "💰 新佣金!",
                "payout_processed": "💸 付款已处理!",
                "account_verified": "✅ 账户已验证!",
                "welcome": "👋 欢迎!",
                "info": "ℹ️ 信息",
                "warning": "⚠️ 警告",
                "error": "❌ 错误",
                "test": "🔔 测试通知",
            },
        }

    def format_notification(self, notification, lang="en"):
        """
        Formate une notification pour Telegram selon la langue choisie
        """
        # Utiliser uniquement la langue spécifiée, sans fallback
        if lang not in self.translations:
            # Si la langue n'est pas disponible, utiliser l'anglais comme fallback
            lang = "en"

        translations = self.translations[lang]

        # Emoji et titre selon le type de notification
        if notification.notification_type == "new_referral":
            prefix = translations["new_referral"]
        elif notification.notification_type == "new_commission":
            prefix = translations["new_commission"]
        elif notification.notification_type == "payout":
            prefix = translations["payout_processed"]
        elif notification.notification_type == "verified":
            prefix = translations["account_verified"]
        elif notification.notification_type == "welcome":
            prefix = translations["welcome"]
        elif notification.notification_type == "info":
            prefix = translations["info"]
        elif notification.notification_type == "warning":
            prefix = translations["warning"]
        elif notification.notification_type == "error":
            prefix = translations["error"]
        else:
            prefix = translations["info"]

        # Pour les tests
        if "test" in notification.title.lower():
            prefix = translations["test"]

        return f"{prefix}\n\n*{notification.title}*\n\n{notification.message}"

    def send_message(self, chat_id, message):
        """
        Envoie un message par Telegram

        Args:
            chat_id: ID du chat Telegram
            message: Message à envoyer (peut contenir du formatage Markdown)

        Returns:
            bool: True si l'envoi a réussi, False sinon
        """
        if not chat_id:
            logger.error("Chat ID manquant, impossible d'envoyer la notification Telegram")
            return False

        if not self.api_token:
            logger.error("Token API Telegram manquant, impossible d'envoyer la notification")
            return False

        # Vérifier que le chat_id est dans un format valide
        chat_id = str(chat_id).strip()
        if not chat_id:
            logger.error("Chat ID invalide après nettoyage")
            return False

        # Préparation des données pour l'envoi
        url = f"https://api.telegram.org/bot{self.api_token}/sendMessage"
        data = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}

        # Envoi de la requête avec retry
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = requests.post(url, json=data, timeout=10)
                result = response.json()

                if result.get("ok"):
                    logger.info(f"✅ Message Telegram envoyé avec succès à {chat_id}")
                    return True
                else:
                    error_code = result.get("error_code", "inconnu")
                    error_desc = result.get("description", "Erreur inconnue")

                    # Gérer les différents types d'erreur
                    if error_code == 400 and "chat not found" in error_desc.lower():
                        logger.error(f"❌ Chat ID invalide ({chat_id}): {error_desc}")
                        return False  # Ne pas réessayer, l'ID est invalide
                    elif error_code == 403 and "blocked" in error_desc.lower():
                        logger.error(
                            f"❌ Le bot a été bloqué par l'utilisateur ({chat_id}): {error_desc}"
                        )
                        return False  # Ne pas réessayer, l'utilisateur a bloqué le bot
                    else:
                        logger.warning(
                            f"❌ Tentative {retry_count+1}/{max_retries}: Erreur Telegram {error_code}: {error_desc}"
                        )
                        retry_count += 1
                        import time

                        time.sleep(2)  # Attendre 2 secondes avant de réessayer

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"❌ Tentative {retry_count+1}/{max_retries}: Erreur de connexion: {str(e)}"
                )
                retry_count += 1
                import time

                time.sleep(2)  # Attendre 2 secondes avant de réessayer

            except Exception as e:
                logger.error(f"❌ Erreur inattendue: {str(e)}")
                return False

        logger.error(f"❌ Échec d'envoi du message Telegram après {max_retries} tentatives")
        return False

    def notify_user(self, user, notification):
        """
        Notifie un utilisateur en fonction de ses préférences
        """
        if not user.telegram_chat_id:
            logger.info(f"L'utilisateur {user.username} n'a pas configuré Telegram")
            return False

        # Utiliser la langue préférée de l'utilisateur
        message = self.format_notification(notification, user.telegram_language)

        return self.send_message(user.telegram_chat_id, message)

    def send_new_ambassador_notification(self, ambassador, new_user):
        """
        Envoyer une notification à un ambassadeur lorsqu'un nouvel utilisateur s'inscrit via son lien de parrainage
        """
        if not ambassador.telegram_chat_id:
            # L'ambassadeur n'a pas configuré Telegram
            return False

        # Récupérer la langue préférée
        try:
            language = ambassador.telegram_language or "fr"
        except Exception:
            language = "fr"  # Langue par défaut

        # Détecter si l'utilisateur est une escorte ou un ambassadeur
        is_escort = getattr(new_user, "user_type", "standard") == "standard"

        # Messages selon la langue
        messages = {
            "en": {
                "title_escort": "New Escort Registration",
                "title_ambassador": "New Ambassador Registration",
                "message_escort": f"A new escort {new_user.username} has signed up using your referral link! You'll receive commissions when they make payments.",
                "message_ambassador": f"A new ambassador {new_user.username} has signed up using your referral link! You'll receive commissions when they make payments.",
                "registration_date": "Registration date:",
            },
            "fr": {
                "title_escort": "Nouvelle Escorte Inscrite",
                "title_ambassador": "Nouvel Ambassadeur Inscrit",
                "message_escort": f"Une nouvelle escorte {new_user.username} s'est inscrite en utilisant votre lien de parrainage ! Vous recevrez des commissions lorsqu'elle effectuera des paiements.",
                "message_ambassador": f"Un nouvel ambassadeur {new_user.username} s'est inscrit en utilisant votre lien de parrainage ! Vous recevrez des commissions lorsqu'il effectuera des paiements.",
                "registration_date": "Date d'inscription :",
            },
            "es": {
                "title_escort": "Nueva Escort Registrada",
                "title_ambassador": "Nuevo Embajador Registrado",
                "message_escort": f"¡Una nueva escort {new_user.username} se ha registrado usando tu enlace de referencia! Recibirás comisiones cuando realice pagos.",
                "message_ambassador": f"¡Un nuevo embajador {new_user.username} se ha registrado usando tu enlace de referencia! Recibirás comisiones cuando realice pagos.",
                "registration_date": "Fecha de registro:",
            },
            "de": {
                "title_escort": "Neue Escort Angemeldet",
                "title_ambassador": "Neuer Botschafter Angemeldet",
                "message_escort": f"Eine neue Escort {new_user.username} hat sich über Ihren Empfehlungslink angemeldet! Sie erhalten Provisionen, wenn sie Zahlungen tätigt.",
                "message_ambassador": f"Ein neuer Botschafter {new_user.username} hat sich über Ihren Empfehlungslink angemeldet! Sie erhalten Provisionen, wenn er Zahlungen tätigt.",
                "registration_date": "Anmeldedatum:",
            },
            "ru": {
                "title_escort": "Новая Эскорт Зарегистрирована",
                "title_ambassador": "Новый Посол Зарегистрирован",
                "message_escort": f"Новая эскорт {new_user.username} зарегистрировалась по вашей реферальной ссылке! Вы будете получать комиссионные, когда она будет совершать платежи.",
                "message_ambassador": f"Новый посол {new_user.username} зарегистрировался по вашей реферальной ссылке! Вы будете получать комиссионные, когда он будет совершать платежи.",
                "registration_date": "Дата регистрации:",
            },
            "zh": {
                "title_escort": "新陪伴注册",
                "title_ambassador": "新大使注册",
                "message_escort": f"新陪伴 {new_user.username} 已使用您的推荐链接注册！当她进行付款时，您将获得佣金。",
                "message_ambassador": f"新大使 {new_user.username} 已使用您的推荐链接注册！当他进行付款时，您将获得佣金。",
                "registration_date": "注册日期：",
            },
            "it": {
                "title_escort": "Nuova Escort Registrata",
                "title_ambassador": "Nuovo Ambasciatore Registrato",
                "message_escort": f"Una nuova escort {new_user.username} si è registrata usando il tuo link di riferimento! Riceverai commissioni quando effettuerà pagamenti.",
                "message_ambassador": f"Un nuovo ambasciatore {new_user.username} si è registrato usando il tuo link di riferimento! Riceverai commissioni quando effettuerà pagamenti.",
                "registration_date": "Data di registrazione:",
            },
            "ar": {
                "title_escort": "تسجيل مرافقة جديدة",
                "title_ambassador": "تسجيل سفير جديد",
                "message_escort": f"مرافقة جديدة {new_user.username} قامت بالتسجيل باستخدام رابط الإحالة الخاص بك! ستتلقى عمولات عندما تقوم بإجراء مدفوعات.",
                "message_ambassador": f"سفير جديد {new_user.username} قام بالتسجيل باستخدام رابط الإحالة الخاص بك! ستتلقى عمولات عندما يقوم بإجراء مدفوعات.",
                "registration_date": "تاريخ التسجيل:",
            },
        }

        # Utiliser la langue sélectionnée ou par défaut
        msg = messages.get(language, messages["en"])

        # Sélectionner le titre et message appropriés selon le type d'utilisateur
        title_key = "title_escort" if is_escort else "title_ambassador"
        message_key = "message_escort" if is_escort else "message_ambassador"

        # Éviter les caractères spéciaux Markdown qui pourraient causer des problèmes de parsing
        username_safe = (
            new_user.username.replace("_", r"\_")
            .replace("*", r"\*")
            .replace("[", r"\[")
            .replace("`", r"\`")
        )

        # Construire le message en évitant les problèmes de formatage Markdown
        message = f"🌟 *{msg[title_key]}*\n\n"
        message += f"{msg[message_key].replace(new_user.username, username_safe)}\n\n"

        # Formater la date de manière sécurisée
        date_str = "N/A"
        if hasattr(new_user, "date_joined"):
            try:
                date_str = new_user.date_joined.strftime("%Y-%m-%d %H:%M")
            except Exception:
                date_str = "N/A"

        message += f"📅 *{msg['registration_date']}* {date_str}"

        # Envoyer le message
        return self.send_message(ambassador.telegram_chat_id, message)

    def send_commission_notification(self, referrer, referred_user, amount, total_earnings):
        """
        Envoie une notification pour une nouvelle commission

        Args:
            referrer: L'ambassadeur qui reçoit la commission
            referred_user: L'utilisateur dont le paiement génère la commission
            amount: Le montant de la commission
            total_earnings: Les gains totaux de cet utilisateur

        Returns:
            bool: True si l'envoi a réussi, False sinon
        """
        if not referrer or not referrer.telegram_chat_id:
            # Le référent n'existe pas ou n'a pas configuré Telegram
            return False

        # Récupérer la langue préférée de l'utilisateur
        language = self.get_user_language(referrer)

        # Messages selon la langue
        messages = {
            "en": {
                "title": "🎉 New Commission! 💰",
                "content": "You've earned {amount}€ from {username}'s payment.\n\nTotal earnings from this user: {total}€",
            },
            "fr": {
                "title": "🎉 Nouvelle Commission ! 💰",
                "content": "Vous avez gagné {amount}€ grâce au paiement de {username}.\n\nGains totaux provenant de cet utilisateur : {total}€",
            },
            "es": {
                "title": "🎉 ¡Nueva comisión! 💰",
                "content": "Has ganado {amount}€ del pago de {username}.\n\nGanancias totales de este usuario: {total}€",
            },
            "de": {
                "title": "🎉 Neue Provision! 💰",
                "content": "Sie haben {amount}€ durch die Zahlung von {username} verdient.\n\nGesamteinnahmen von diesem Benutzer: {total}€",
            },
            "ru": {
                "title": "🎉 Новая комиссия! 💰",
                "content": "Вы заработали {amount}€ с платежа {username}.\n\nОбщий доход от этого пользователя: {total}€",
            },
            "zh": {
                "title": "🎉 新的佣金! 💰",
                "content": "您已从{username}的付款中赚取{amount}€。\n\n来自该用户的总收入：{total}€",
            },
            "it": {
                "title": "🎉 Nuova Commissione! 💰",
                "content": "Hai guadagnato {amount}€ dal pagamento di {username}.\n\nGuadagni totali da questo utente: {total}€",
            },
            "ar": {
                "title": "🎉 عمولة جديدة! 💰",
                "content": "لقد كسبت {amount}€ من دفعة {username}.\n\nإجمالي الأرباح من هذا المستخدم: {total}€",
            },
        }

        # Utiliser le template dans la langue appropriée
        msg = messages.get(language, messages["en"])

        # Formater le message avec les données
        message = f"{msg['title']}\n\n" + msg["content"].format(
            username=referred_user.username,
            amount=f"{amount:.2f}",
            total=f"{total_earnings:.2f}",
        )

        # Envoyer la notification
        return self.send_message(chat_id=referrer.telegram_chat_id, message=message)

    def get_user_language(self, user):
        """
        Récupère la langue préférée de l'utilisateur pour les notifications

        Args:
            user: Instance du modèle User

        Returns:
            str: Code de langue (ex: 'en', 'fr')
        """
        if hasattr(user, "telegram_language") and user.telegram_language:
            language = user.telegram_language
            return language
        return "en"  # Langue par défaut
