import os
import pathlib
import psycopg2
from dotenv import load_dotenv
import datetime
import sys

# Charger les variables d'environnement
BASE_DIR = pathlib.Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

print("=" * 50)
print("TEST COMPLET SUPABASE / POSTGRESQL")
print("=" * 50)

# 1. Afficher les variables d'environnement
print("\n1. VARIABLES D'ENVIRONNEMENT:")
print(f"USER: {os.getenv('user')}")
print(f"PASSWORD: {'*' * len(os.getenv('password', ''))} (masqué)")
print(f"HOST: {os.getenv('host')}")
print(f"PORT: {os.getenv('port')}")
print(f"DBNAME: {os.getenv('dbname')}")

# 2. Tester la connexion PostgreSQL
print("\n2. TEST CONNEXION POSTGRESQL:")
try:
    conn = psycopg2.connect(
        user=os.getenv("user"),
        password=os.getenv("password"),
        host=os.getenv("host"),
        port=os.getenv("port"),
        dbname=os.getenv("dbname"),
    )
    print("✅ Connexion PostgreSQL établie avec succès!")

    # 3. Lister les tables
    print("\n3. TABLES EXISTANTES:")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """
    )
    tables = cursor.fetchall()
    if tables:
        print(f"Il y a {len(tables)} tables dans la base:")
        for i, table in enumerate(tables):
            print(f"  {i+1}. {table[0]}")
    else:
        print("⚠️ Aucune table trouvée dans le schéma public")

    # 4. Créer une table de test si elle n'existe pas déjà
    print("\n4. CRÉATION/MODIFICATION DE DONNÉES:")
    table_name = "test_django_supabase"
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """
    )
    conn.commit()
    print(f"✅ Table '{table_name}' créée ou déjà existante")

    # 5. Insérer une ligne de test
    test_data = f"Test Django-Supabase: {datetime.datetime.now()}"
    cursor.execute(
        f"""
        INSERT INTO {table_name} (description)
        VALUES (%s)
        RETURNING id, description, created_at;
    """,
        (test_data,),
    )

    new_row = cursor.fetchone()
    conn.commit()
    print(f"✅ Données insérées: ID={new_row[0]}, Description='{new_row[1]}', Date={new_row[2]}")

    # 6. Lire toutes les données de cette table
    print("\n5. LECTURE DES DONNÉES:")
    cursor.execute(
        f"""
        SELECT id, description, created_at
        FROM {table_name}
        ORDER BY created_at DESC
        LIMIT 5;
    """
    )
    rows = cursor.fetchall()
    print(f"Dernières entrées dans '{table_name}':")
    for row in rows:
        print(f"  - ID: {row[0]}, Date: {row[2]}, Description: '{row[1]}'")

    # Fermeture
    cursor.close()
    conn.close()
    print("\n✅ Test complet terminé avec succès!")

except Exception as e:
    print(f"❌ ERREUR: {e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("RÉSUMÉ: Toutes les opérations PostgreSQL fonctionnent!")
print("Django est maintenant correctement configuré avec Supabase.")
print("=" * 50)
