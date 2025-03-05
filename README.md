# AssitProf
---
## 📌 **Description du projet**  
Le projet vise à développer un assistant virtuel pour les enseignants du supérieur, facilitant :  
✅ La gestion des tâches pédagogiques  
✅ La centralisation des ressources  
✅ L’analyse des performances étudiantes  

Le développement suit une approche rigoureuse basée sur le **génie logiciel**, comprenant l'analyse, la conception, le développement et le déploiement.  

---

## 🚀 **Fonctionnalités principales**  

### 📅 1. Gestion des plannings et rappels automatiques  
- 🕒 Saisie des cours et événements avec créneaux horaires  
- 🔔 Notifications et rappels automatiques  

### 📚 2. Centralisation des ressources pédagogiques  
- 📤 Téléversement et organisation des documents pédagogiques  
- 🏷️ Classification par dossiers ou tags pour une recherche rapide  

### 📊 3. Suivi des étudiants  
- 📂 Importation des résultats via un fichier CSV  
- 📈 Génération de graphiques (moyennes, taux de réussite, etc.)  

### 🤖 4. FAQ intelligente  
- 💡 Système de réponse automatique aux questions fréquentes  
- 📌 Base de données de questions-réponses évolutive  

### 💻 5. Interface utilisateur simple et ergonomique  
- 🎨 Interface web conviviale et responsive  
- 🖥️ Accessible sur PC et tablettes  

---

## 🛠️ **Technologies utilisées**  
- 🔙 **Backend** : Flask (Python)  
- 🗄️ **Base de données** : MySQL  
- 🎨 **Frontend** : HTML, CSS (Bootstrap), JavaScript  


## ⚙️ Installation et exécution

### Prérequis

- **Python 3.8+** installé
- **MySQL** installé et configuré
- **Git** installé

### Étapes d'installation

1. **Cloner le dépôt :**
   ```bash
   
   git clone [https://github.com/votre-utilisateur/mashru3](https://github.com/haki24gamer/Mashru3).git
   cd Mashru3

2. **Créer un environnement virtuel :**
   ```bash
   
      python -m venv venv
      source venv/bin/activate  # Pour Linux/MacOS
      venv\Scripts\activate     # Pour Windows

3. **Installer les dépendances :**
   ```bash
   
     pip install -r requirements.txt

4. **Configurer la base de données :**
   ```sql
   
     CREATE DATABASE mashru3 CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

5. **Appliquer les migrations de la base de données :**
   ```bash
   
     flask db upgrade

6. **Lancer l'application :**
   ```bash
   
     flask run
   
  L'application sera accessible sur http://127.0.0.1:5000.
